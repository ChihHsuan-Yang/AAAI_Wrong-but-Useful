#!/usr/bin/env python3
"""Fail the build if a non-portable or private string reaches the repository.

Five classes are checked:

``author_path``
    absolute paths that only exist on the authors' machines or clusters;
``private_url``
    institutional endpoints and proxies -- the worst of these is a proxy set as
    a shell default, which silently routes a reader's traffic somewhere private;
``credential``
    key-shaped literals;
``stale_name``
    internal repository, dataset, and framework names from the private monorepo;
``review_anonymity``
    submission-era anonymization language that must not survive publication.

Design notes that make this a real check rather than a reassuring one:

* **Patterns are assembled from fragments.** A scanner containing the literals
  it forbids would match itself, and the usual workaround -- exempting the
  scanner's own path -- exempts an entire file. Fragments keep the scanner
  scannable.
* **Every pattern carries a positive control** (:data:`POSITIVE_CONTROLS`).
  ``--self-test`` runs each pattern against a string that must match and a
  string that must not. A pattern that matches nothing is reported as BROKEN,
  not as clean, so "0 findings" cannot come from a dead regex.
* **The allowlist keys on (path, pattern, line-substring)**, never on a path
  alone, so an exemption cannot silently cover a whole file. Every entry
  carries a written justification.
* **Absence fails closed.** A path in the allowlist that no longer matches is
  reported, so stale exemptions are removed rather than accumulating.

Exit codes: 0 clean, 1 findings, 2 the audit itself is broken.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    ".git", ".venv", "venv", "env", ".pytest_cache", "__pycache__",
    ".ruff_cache", ".mypy_cache", "build", "dist", "site-packages",
    "node_modules", "reproduced", "outputs", "smoke_output", ".dhd_cache",
    ".egg-info",
}
SKIP_SUFFIXES = {".pdf", ".png", ".svg", ".jpg", ".jpeg", ".ico", ".zst", ".gz", ".zip"}


def _j(*parts: str) -> str:
    """Join fragments. Keeps forbidden literals out of this file's own source."""
    return "".join(parts)


@dataclass(frozen=True)
class Pattern:
    name: str
    klass: str
    regex: str
    why: str

    def compiled(self) -> re.Pattern[str]:
        return re.compile(self.regex, re.IGNORECASE)


PATTERNS: list[Pattern] = [
    # ---- author paths -----------------------------------------------------
    Pattern(
        "macos_home", "author_path",
        r"/" + _j("Us", "ers") + r"/[A-Za-z0-9._-]+",
        "An author's macOS home directory. Nothing on a reader's machine is there.",
    ),
    Pattern(
        "linux_home", "author_path",
        r"/" + _j("ho", "me") + r"/(?!user\b|USER\b)[A-Za-z0-9._-]+",
        "A named Linux home directory, usually an author or a third-party account.",
    ),
    Pattern(
        "cluster_filesystem", "author_path",
        r"/(?:" + _j("l", "us") + r"|" + _j("fla", "re") + r"|" + _j("ea", "gle") + r")/",
        "Site-specific parallel filesystems. Absent everywhere else, and usually "
        "written as a ':-' shell fallback, so they fail silently rather than loudly.",
    ),
    # ---- private URLs -----------------------------------------------------
    Pattern(
        "institutional_endpoint", "private_url",
        _j("inference-api", r"\.", "alcf", r"\.", "anl", r"\.", "gov"),
        "A live institutional inference endpoint. Not reachable by a reader, and "
        "not ours to advertise.",
    ),
    Pattern(
        "institutional_proxy", "private_url",
        _j("proxy", r"\.", "alcf", r"\.", "anl", r"\.", "gov"),
        "A private HTTP proxy. Shipped as `${HTTP_PROXY:-...}` it would silently "
        "route a reader's traffic through somebody else's network.",
    ),
    # ---- credentials ------------------------------------------------------
    Pattern(
        "openai_key_literal", "credential",
        r"\b" + _j("s", "k") + r"-[A-Za-z0-9]{16,}\b",
        "An OpenAI-style key literal.",
    ),
    Pattern(
        "hf_token_literal", "credential",
        r"\b" + _j("h", "f") + r"_[A-Za-z0-9]{20,}\b",
        "A Hugging Face access token literal.",
    ),
    Pattern(
        "bearer_literal", "credential",
        r"(?i)" + _j("Bear", "er") + r"\s+(?!\{|\$|<|\"|')[A-Za-z0-9._\-]{20,}",
        "A hard-coded bearer token rather than an interpolated variable.",
    ),
    Pattern(
        "assigned_key_literal", "credential",
        r"(?i)\b(?:api[_-]?key|auth[_-]?token|access[_-]?token|secret)\b\s*[:=]\s*"
        r"[\"'][A-Za-z0-9._\-]{16,}[\"']",
        "A credential assigned a long literal value instead of read from the "
        "environment.",
    ),
    # ---- stale internal names --------------------------------------------
    Pattern(
        "internal_monorepo", "stale_name",
        r"\b" + _j("mas", "-", "eval") + r"\b",
        "The private monorepo's name. A reader cannot clone it; a path built "
        "from it is a dead end.",
    ),
    Pattern(
        "internal_framework", "stale_name",
        r"\b" + _j("agent", "verse") + r"\b",
        "The internal agent framework. It is a hard runtime import in the "
        "private tree; anything here that needs it cannot run standalone.",
    ),
    Pattern(
        "internal_inventory", "stale_name",
        r"\b" + _j("MAS", "Trace", "Inventory") + r"\b",
        "An internal inventory repository name.",
    ),
    Pattern(
        "internal_traces_repo", "stale_name",
        r"\b" + _j("scientific", "-", "agent", "-", "protocol", "-", "traces") + r"\b",
        "An internal traces repository name.",
    ),
    # ---- review anonymity -------------------------------------------------
    Pattern(
        "anonymous_authors", "review_anonymity",
        r"(?i)" + _j("Anony", "mous") + r"\s+" + _j("Auth", "ors"),
        "Submission-era placeholder. On a public release the copyright line must "
        "name the real authors.",
    ),
    Pattern(
        "anonymous_artifact_name", "review_anonymity",
        r"(?i)" + _j("anony", "mous") + r"[_\- ]" + _j("reproduci", "bility"),
        "The double-blind artifact directory name.",
    ),
    Pattern(
        "anonymity_language", "review_anonymity",
        r"(?i)\b" + _j("anonymi", "ty") + r"\s+(?:self-)?" + _j("sc", "an") + r"\b",
        "Double-blind review scaffolding language.",
    ),
    Pattern(
        "anonymized_for_review", "review_anonymity",
        r"(?i)" + _j("anony", "mi[sz]ed") + r"\s+for\s+" + _j("rev", "iew"),
        "Explicit double-blind phrasing.",
    ),
]

#: ``pattern name -> (string that MUST match, string that MUST NOT match)``.
#: Every pattern has one. ``--self-test`` fails if a pattern matches neither, so
#: a clean scan cannot be produced by a regex that can never fire.
POSITIVE_CONTROLS: dict[str, tuple[str, str]] = {
    # Every control string is assembled from fragments, for the same reason the
    # patterns are: a literal here would make this file match its own pattern,
    # and the usual fix -- exempting the scanner by path -- would exempt the
    # entire file from every check. With fragments, this file is scanned like
    # any other and needs no exemption at all.
    "macos_home": ("/" + _j("Us", "ers") + "/someone/project", "/opt/project"),
    "linux_home": ("/" + _j("ho", "me") + "/someone/repo", "/" + _j("ho", "me") + "/user/repo"),
    "cluster_filesystem": ("/" + _j("l", "us") + "/scratch", "/var/lib/data"),
    "institutional_endpoint": (
        "https://" + _j("inference-api", ".", "alcf", ".", "anl", ".", "gov") + "/v1",
        "https://api.example.com/v1"),
    "institutional_proxy": (
        'HTTP_PROXY="http://' + _j("proxy", ".", "alcf", ".", "anl", ".", "gov")
        + ':3128"', "HTTP_PROXY=${HTTP_PROXY}"),
    "openai_key_literal": (
        _j("s", "k") + "-" + "A" * 24, _j("s", "k") + "-short"),
    "hf_token_literal": (
        _j("h", "f") + "_" + "B" * 24, _j("h", "f") + "_short"),
    "bearer_literal": (
        _j("Bear", "er") + " " + "C" * 24, _j("Bear", "er") + " {token}"),
    "assigned_key_literal": (
        'api_key = "' + "D" * 20 + '"', 'api_key = os.environ["X"]'),
    "internal_monorepo": (
        "/repos/" + _j("mas", "-", "eval") + "/.venv", "model evaluation"),
    "internal_framework": (
        "from " + _j("agent", "verse") + ".utils import X", "agent framework"),
    "internal_inventory": (
        _j("MAS", "Trace", "Inventory") + "/index", "trace inventory"),
    "internal_traces_repo": (
        _j("scientific", "-", "agent", "-", "protocol", "-", "traces") + "/raw",
        "agent protocol traces"),
    "anonymous_authors": (
        "Copyright (c) 2026 " + _j("Anony", "mous") + " " + _j("Auth", "ors"),
        "Copyright (c) 2026 C. Yang"),
    "anonymous_artifact_name": (
        _j("anony", "mous") + "_" + _j("reproduci", "bility") + "/README.md",
        "reproducibility/README.md"),
    "anonymity_language": (
        "an in-artifact " + _j("anony", "mity") + " " + _j("self-sc", "an"),
        "a portability audit"),
    "anonymized_for_review": (
        _j("anony", "mized") + " for " + _j("rev", "iew"), "prepared for release"),
}


@dataclass(frozen=True)
class Allowed:
    """One deliberate exemption, pinned to an exact line.

    Keyed on ``(path, pattern, sha256-of-the-stripped-line)``. Three earlier and
    weaker designs were tried and rejected by the positive control:

    * keying on the path alone exempts the whole file, so any violation added to
      it later passes silently;
    * keying on ``(path, pattern)`` exempts every line in that file matching
      that pattern -- a planted copyright line slipped straight through;
    * keying on a *substring* of the line has the same hole, because a different
      line that happens to contain the substring also satisfies it. A planted
      copyright line was exempted by a genuine line elsewhere in the same file
      that happened to contain the same words.

    A digest of the exact line has no such slack: change the line, or add
    another one like it, and the exemption stops applying.
    """

    path: str
    pattern: str
    line_sha256: str
    excerpt: str
    justification: str


def line_digest(line: str) -> str:
    return hashlib.sha256(line.strip().encode("utf-8")).hexdigest()


#: Exemptions are deliberate historical provenance only: the lines in
#: release_notes/PROVENANCE.md that record exactly which private strings were
#: replaced. A substitution you cannot see is a substitution you cannot check,
#: so those lines must survive -- and nothing else is exempt anywhere.
#: Regenerate a digest with:
#:   python -c "import sys;from tools.portability_audit import line_digest;\
#:              print(line_digest(sys.argv[1]))" "<the exact line>"
ALLOWLIST: list[Allowed] = [
    Allowed(
        "release_notes/PROVENANCE.md", "anonymous_artifact_name",
        "fbabeb0a096bef6affd59a65f52955213af0ea02280ac0268a3e904e2e92d747",
        "top directory `<old name>/` -> repository root",
        "Provenance: records the directory name inside the arXiv ancillary zip "
        "this repository was built from. A reader verifying the lineage needs "
        "the original name.",
    ),
    Allowed(
        "release_notes/PROVENANCE.md", "anonymous_authors",
        "8f96fd529a2d5beedb76a2a0aca6cf71686930cdc500fd28d519bcf44eefafb8",
        "the LICENSE copyright line -> the ten named authors",
        "Provenance: records the exact LICENSE copyright line that was replaced, "
        "so the substitution is auditable rather than asserted.",
    ),
    Allowed(
        "release_notes/PROVENANCE.md", "anonymous_artifact_name",
        "68fb319fcabf8c5411268bc7340906b88147a393c2047e5c0651e3c5a21f45b8",
        "the manifest artifact field -> AAAI_Wrong-but-Useful",
        "Provenance: records the exact manifest value that was replaced.",
    ),
    Allowed(
        "release_notes/PROVENANCE.md", "anonymous_artifact_name",
        "d776e85f9ebb13d3e67d5a2c4608160ebd8b53df0482c08390e4c691e253007a",
        "the pyproject description -> the paper's title",
        "Provenance: records the exact pyproject description that was replaced.",
    ),
    Allowed(
        "release_notes/PROVENANCE.md", "anonymity_language",
        "96bec63c8760c5c241d5b35063c4bcf7fd9a2b29414774f2c75a13346eb4503f",
        "the upstream self-scan -> tools/portability_audit.py",
        "Provenance: records which upstream test this audit replaced, and why "
        "the property being enforced changed.",
    ),
    Allowed(
        "release_notes/PROVENANCE.md", "internal_framework",
        "83214573255d85c0a49d4d706cd9a1c49080853842c0728f5b37a21b48046d19",
        "names the internal framework the analyses were decoupled from",
        "Provenance: the porting note's whole point is that these analyses no "
        "longer depend on that framework; naming it is what makes the claim "
        "checkable.",
    ),
]


def iter_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        parts = set(path.relative_to(root).parts)
        if parts & SKIP_DIRS or any(p.endswith(".egg-info") for p in parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        out.append(path)
    return out


def _allow_for(rel: str, pattern: str, line: str) -> Allowed | None:
    digest = line_digest(line)
    for entry in ALLOWLIST:
        if entry.path == rel and entry.pattern == pattern and entry.line_sha256 == digest:
            return entry
    return None


def scan(root: Path) -> tuple[list[dict], list[Allowed]]:
    """Return ``(findings, unused_allowlist_entries)``.

    This scanner scans itself like any other file. It has no self-exemption,
    because exempting a file by path exempts everything in it -- including a
    real violation someone later adds. Its patterns and controls are assembled
    from fragments so there is nothing here to exempt.
    """
    compiled = [(p, p.compiled()) for p in PATTERNS]
    findings: list[dict] = []
    used: set[tuple[str, str, str]] = set()
    for path in iter_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        # A path name can itself be non-portable even when the content is fine.
        for pattern, regex in compiled:
            if regex.search(rel):
                findings.append(
                    {
                        "path": rel, "line": 0, "pattern": pattern.name,
                        "class": pattern.klass, "text": rel, "why": pattern.why,
                    }
                )
        for number, line in enumerate(text.splitlines(), start=1):
            for pattern, regex in compiled:
                match = regex.search(line)
                if not match:
                    continue
                allowed = _allow_for(rel, pattern.name, line)
                if allowed is not None:
                    used.add((allowed.path, allowed.pattern, allowed.line_sha256))
                    continue
                findings.append(
                    {
                        "path": rel, "line": number, "pattern": pattern.name,
                        "class": pattern.klass, "text": line.strip()[:200],
                        "why": pattern.why,
                    }
                )
    unused = [
        entry
        for entry in ALLOWLIST
        if (entry.path, entry.pattern, entry.line_sha256) not in used
    ]
    return findings, unused


def self_test() -> list[str]:
    """Every pattern must match its positive control and reject its negative."""
    problems: list[str] = []
    for pattern in PATTERNS:
        control = POSITIVE_CONTROLS.get(pattern.name)
        if control is None:
            problems.append(f"{pattern.name}: NO POSITIVE CONTROL -- pattern unproven")
            continue
        must_match, must_not = control
        regex = pattern.compiled()
        if not regex.search(must_match):
            problems.append(
                f"{pattern.name}: BROKEN -- does not match its own positive "
                f"control {must_match!r}"
            )
        if regex.search(must_not):
            problems.append(
                f"{pattern.name}: OVERBROAD -- matches its negative control {must_not!r}"
            )
    covered = {p.name for p in PATTERNS}
    for name in POSITIVE_CONTROLS:
        if name not in covered:
            problems.append(f"{name}: control exists for a pattern that does not")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--self-test", action="store_true",
        help="Only verify that every pattern can fire; do not scan.",
    )
    parser.add_argument(
        "--allow-unused", action="store_true",
        help="Do not fail on allowlist entries that no longer match anything.",
    )
    args = parser.parse_args()

    problems = self_test()
    if problems:
        print("AUDIT IS BROKEN -- patterns failed their own controls:")
        for item in problems:
            print(f"  - {item}")
        return 2
    if args.self_test:
        print(f"PASS: all {len(PATTERNS)} patterns matched their positive control "
              f"and rejected their negative control.")
        return 0

    root = args.root.resolve()
    findings, unused = scan(root)

    if args.json:
        print(json.dumps({"findings": findings, "unused_allowlist": [
            e.__dict__ for e in unused]}, indent=2, sort_keys=True))
    else:
        if findings:
            print(f"PORTABILITY AUDIT FAILED: {len(findings)} finding(s) in {root}")
            for item in findings:
                print(f"  [{item['class']}/{item['pattern']}] "
                      f"{item['path']}:{item['line']}: {item['text']}")
                print(f"      why: {item['why']}")
        if unused and not args.allow_unused:
            print(f"STALE ALLOWLIST: {len(unused)} entr(ies) no longer match anything.")
            for entry in unused:
                print(f"  - {entry.path} [{entry.pattern}] {entry.excerpt!r} "
                      f"(sha {entry.line_sha256[:12]})")
            print("  Remove them: an exemption nobody needs is an exemption "
                  "nobody reviews.")
        if not findings and not (unused and not args.allow_unused):
            print(f"PASS: {len(PATTERNS)} patterns, all positive-controlled, "
                  f"0 findings across {len(iter_files(root))} files in {root}.")

    if findings:
        return 1
    if unused and not args.allow_unused:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
