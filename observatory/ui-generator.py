"""Generate a browser-friendly UI data snapshot for CodeFarm."""
from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from codefarm_common import ROOT, read_json


def main() -> int:
    state = read_json(ROOT / "state.json", {})
    metrics = read_json(ROOT / "observatory" / "metrics.json", {})
    logs_dir = ROOT / "logs"
    logs = sorted(logs_dir.glob("codefarm-*.log")) if logs_dir.exists() else []
    recent_log = []
    if logs:
        recent_log = logs[-1].read_text(encoding="utf-8", errors="replace").splitlines()[-25:]
    payload = {
        "state": state if isinstance(state, dict) else {},
        "metrics": metrics if isinstance(metrics, dict) else {},
        "recent_log": recent_log,
    }
    out = ROOT / "observatory" / "ui" / "data.js"
    out.write_text("window.CODEFARM_DATA = " + json.dumps(payload, indent=2) + ";\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
