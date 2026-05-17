"""Shared filesystem and JSON helpers for CodeFarm."""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("CODEFARM_ROOT", r"G:\codefarm"))
STATE_PATH = ROOT / "state.json"

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def ensure_inside_root(path: Path) -> Path:
    resolved = path.resolve()
    root = ROOT.resolve()
    if root != resolved and root not in resolved.parents:
        raise ValueError(f"Path escapes CodeFarm root: {resolved}")
    return resolved

def ensure_dirs() -> None:
    for rel in ["core/terraform", "core/ansible", "core/k8s-manifests", "organisms", "digestive-engine", "nutrient-pool/available", "nutrient-pool/consumed", "genome-bank/evolved-strains", "genome-bank/failures", "immune-system", "observatory/grafana-dashboards", "logs", "tasks/pending", "tasks/completed", "tasks/failed", "tools", "secrets/ssh"]:
        ensure_inside_root(ROOT / rel).mkdir(parents=True, exist_ok=True)

def read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default

def write_json(path: Path, payload: Any) -> None:
    ensure_inside_root(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)

def load_state() -> dict[str, Any]:
    state = read_json(STATE_PATH, {})
    if not isinstance(state, dict):
        state = {}
    state.setdefault("codefarm_root", str(ROOT))
    state.setdefault("autonomy_level", 2)
    state.setdefault("cycle", 0)
    state.setdefault("organisms", {})
    state.setdefault("nutrient_pool", {})
    state["nutrient_pool"].setdefault("available_calories", 0)
    state["nutrient_pool"].setdefault("consumed_calories", 0)
    state["nutrient_pool"].setdefault("spawn_cost", 500)
    state.setdefault("metrics", {})
    state["metrics"].setdefault("births_24h", 0)
    state["metrics"].setdefault("deaths_24h", 0)
    state["metrics"].setdefault("lifetime_births", 0)
    state["metrics"].setdefault("lifetime_deaths", 0)
    state["metrics"].setdefault("lifetime_nutrients", 0)
    state["metrics"].setdefault("quality_history", [])
    state.setdefault("events", [])
    return state

def save_state(state: dict[str, Any]) -> None:
    now = utc_now()
    if state.get("created_at") is None:
        state["created_at"] = now
    state["updated_at"] = now
    write_json(STATE_PATH, state)

def log_event(message: str) -> Path:
    ensure_dirs()
    log_path = ROOT / "logs" / f"codefarm-{datetime.now(timezone.utc).date().isoformat()}.log"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{utc_now()} {message}\n")
    return log_path
