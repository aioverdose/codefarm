"""CODEFARM-OVERMIND entry point."""
from __future__ import annotations
import argparse
import importlib.util
from pathlib import Path
from codefarm_common import ROOT, ensure_dirs, load_state, log_event, save_state, utc_now, write_json


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def bootstrap() -> None:
    ensure_dirs()
    state = load_state()
    state.setdefault("created_at", utc_now())
    save_state(state)
    for rel in ["core/terraform/README.md", "core/ansible/README.md", "core/k8s-manifests/README.md"]:
        path = ROOT / rel
        if not path.exists():
            path.write_text("CodeFarm placeholder. Real infrastructure hooks stay rooted under G:\\codefarm.\n", encoding="utf-8")
    log_event("BOOTSTRAP complete")


def genesis() -> str:
    state = load_state()
    if state.get("organisms"):
        return sorted(state["organisms"].keys())[0]
    breeder = load_module(ROOT / "immune-system" / "breeder.py", "breeder")
    return breeder.spawn()


def seed_task(label: str) -> Path:
    pending = sorted((ROOT / "tasks" / "pending").glob("*.json"))
    if pending:
        return pending[0]
    state = load_state()
    task_id = f"task-cycle-{int(state.get('cycle', 0)) + 1}-{label}"
    task_path = ROOT / "tasks" / "pending" / f"{task_id}.json"
    write_json(task_path, {
        "id": task_id,
        "type": "algo_implementation",
        "difficulty": "easy",
        "nutrient_multiplier": 1.0,
        "prompt": "Write a Python function safe_json_loads(text, default=None) that parses JSON and returns default on invalid JSON.",
        "expected_function": "safe_json_loads"
    })
    log_event(f"TASK seeded={task_id}")
    return task_path


def run_immune_sweep() -> None:
    detector = load_module(ROOT / "immune-system" / "pathogen-detector.py", "pathogen_detector")
    findings = detector.detect_pathogens()
    if findings:
        surgeon = load_module(ROOT / "immune-system" / "surgeon.py", "surgeon")
        for finding in findings:
            surgeon.terminate(finding["organism"], finding["reason"])


def maybe_breed() -> None:
    state = load_state()
    pool = state.get("nutrient_pool", {})
    organisms = state.get("organisms", {})
    if int(pool.get("available_calories", 0)) > int(pool.get("spawn_cost", 500)) and len(organisms) < 3:
        breeder = load_module(ROOT / "immune-system" / "breeder.py", "breeder")
        parent = max(organisms.items(), key=lambda item: int(item[1].get("lifetime_nutrients", 0)))[0]
        breeder.spawn(parent)


def sustain_once() -> dict:
    genesis()
    state = load_state()
    worked = []
    for organism_id in sorted(state.get("organisms", {}).keys()):
        metabolism_path = ROOT / "organisms" / organism_id / "metabolism.py"
        if not metabolism_path.exists():
            log_event(f"SKIP organism={organism_id} reason=no_metabolism_engine")
            continue
        seed_task(organism_id)
        metabolism = load_module(metabolism_path, f"{organism_id}_metabolism")
        worked.append(metabolism.run_cycle(organism_id))
        run_immune_sweep()
        maybe_breed()
        state = load_state()
    collector = load_module(ROOT / "observatory" / "metrics-collector.py", "metrics_collector")
    metrics = collector.collect()
    log_event(f"SUSTAIN population={metrics['population']} pool={metrics['available_calories']}")
    return {"worked": worked, "metrics": metrics}


def main() -> int:
    parser = argparse.ArgumentParser(description="CODEFARM-OVERMIND")
    parser.add_argument("command", choices=["bootstrap", "genesis", "cycle", "status"], nargs="?", default="cycle")
    args = parser.parse_args()
    if args.command == "bootstrap":
        bootstrap()
    elif args.command == "genesis":
        bootstrap(); genesis()
    elif args.command == "cycle":
        bootstrap(); sustain_once()
    state = load_state()
    population = len(state.get("organisms", {}))
    pool = state.get("nutrient_pool", {}).get("available_calories", 0)
    status = "alive" if population else "empty"
    log_path = ROOT / "logs" / f"codefarm-{utc_now()[:10]}.log"
    print(f"G CODEFARM | Status: {status} | Population: {population} | Pool: {pool}")
    print(f"Log: {log_path}")
    print(f"State: {ROOT / 'state.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

