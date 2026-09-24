"""Make the runtime package and analysis modules importable in tests."""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _sub in ("src", "analysis", "analysis/replay", "figures"):
    _path = str(_ROOT / _sub)
    if _path not in sys.path:
        sys.path.insert(0, _path)
