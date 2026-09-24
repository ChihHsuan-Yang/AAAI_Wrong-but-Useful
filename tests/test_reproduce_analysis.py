"""End-to-end check that analysis reproduction matches the expected manifest."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_reproduce_module():
    spec = importlib.util.spec_from_file_location(
        "reproduce_analysis", ROOT / "scripts" / "reproduce_analysis.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_headline_summary_matches_expected_manifest():
    import json

    module = _load_reproduce_module()
    computed = module.compute_headline_summary()
    expected = json.loads(
        (ROOT / "data" / "manifests" / "expected_summaries.json").read_text()
    )
    assert module._almost_equal(computed, expected)


def test_taxonomy_has_off_diagonal_cells():
    module = _load_reproduce_module()
    summary = module.compute_headline_summary()
    tax = summary["loo_taxonomy"]
    # The paper's central claim: wrong-helpful and correct-harmful cells exist.
    assert tax["OSS|wrong"]["helpful"] > 0
    assert tax["OSS|correct"]["harmful"] > 0
    assert tax["Gemma|wrong"]["helpful"] > 0
    assert tax["Gemma|correct"]["harmful"] > 0
