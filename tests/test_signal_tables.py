"""Below-cell recomputation of robustness tables from per-signal/per-fold records."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "recompute_signal_tables", ROOT / "scripts" / "recompute_signal_tables.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_signal_tables_match_expected_manifest():
    module = _load()
    computed = module.compute_all()
    expected = json.loads(
        (ROOT / "data" / "manifests" / "expected_signal_tables.json").read_text()
    )
    assert module._almost_equal(computed, expected)


def test_matched_sensitivity_signal_counts():
    module = _load()
    ms = module.matched_sensitivity_table()
    # Each matched change covers 20 frozen problems x 5 benchmarks x 5 signals.
    for row in ms.values():
        assert row["signals"] == 500


def test_cross_fitted_gain_is_positive_for_both_models():
    module = _load()
    xf = module.cross_fitted_table()["overall"]
    assert xf["oss"]["gain_pp"] > 0
    assert xf["gemma"]["gain_pp"] > 0


def test_signal_records_carry_no_raw_identifiers():
    # Problem keys must be anonymized hashes, not benchmark-native numbering.
    import csv

    path = ROOT / "data" / "derived" / "signal_labels" / "matched_sensitivity_order_oss.csv"
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            pid = row["problem_id"]
            assert pid.startswith("p_") and " " not in pid
