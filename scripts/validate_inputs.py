#!/usr/bin/env python3
"""Validate the included data inputs against the artifact manifest.

Checks, for every entry in ``ARTIFACT_MANIFEST.json``:

- the referenced file exists;
- its SHA-256 matches the recorded value;
- CSV row counts match the recorded ``row_count``.

Exit code is non-zero on any mismatch. This does not call any model.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "ARTIFACT_MANIFEST.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def csv_rows(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def main() -> int:
    if not MANIFEST.exists():
        print(f"missing manifest: {MANIFEST}")
        return 1
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    problems: list[str] = []
    checked = 0
    for entry in manifest.get("data_objects", []):
        rel = entry["artifact_path"]
        path = REPO_ROOT / rel
        if not path.exists():
            problems.append(f"missing: {rel}")
            continue
        actual = sha256(path)
        if entry.get("sha256") and actual != entry["sha256"]:
            problems.append(f"sha256 mismatch: {rel}")
        if rel.endswith(".csv") and entry.get("row_count") is not None:
            actual_rows = csv_rows(path)
            if actual_rows != entry["row_count"]:
                problems.append(
                    f"row_count mismatch: {rel} expected={entry['row_count']} "
                    f"actual={actual_rows}"
                )
        checked += 1

    if problems:
        print("VALIDATION FAILED:")
        for item in problems:
            print(f"  - {item}")
        return 1
    print(f"PASS: validated {checked} data objects against the manifest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
