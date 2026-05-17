"""CodeFarm Commercial Orchestrator."""
from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE = Path("G:/codefarm")
LOG_PATH = BASE / "logs" / f"commercial-{datetime.now(timezone.utc).date().isoformat()}.log"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{utc_now()}] [ORCH] {message}"
    LOG_PATH.open("a", encoding="utf-8").write(line + "\n")
    print(line)


def read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def ensure_commercial_state() -> dict[str, Any]:
    state = read_json(BASE / "state.json", {})
    organisms = state.get("organisms", {}) if isinstance(state.get("organisms"), dict) else {}
    active = [oid for oid in ["org-001", "org-002", "org-003"] if oid in organisms]
    pool = state.setdefault("nutrient_pool", {})
    available = int(pool.get("available", pool.get("available_calories", 0)))
    state.update({
        "version": "2.0-commercial",
        "name": "CodeFarm",
        "status": "operational",
        "tenant_id": "demo",
    })
    state.setdefault("billing", {"tier": "pilot", "monthly_rate": 0, "automation_actions": 0, "incidents_prevented": 0, "uptime_percentage": 100.0})
    state.setdefault("infrastructure", {"vms_provisioned": 0, "services_deployed": 0, "last_deployment": None, "health_checks_passed": 0, "health_checks_failed": 0, "automation_actions": 0})
    state["population"] = {"active": len(active), "max": 10, "specializations": {"provisioner": 1, "platform": 1, "security": 1}}
    pool["available"] = available
    pool["available_calories"] = available
    pool.setdefault("spawn_cost", 150)
    pool.setdefault("revenue_per_action", 0.10)
    write_json(BASE / "state.json", state)
    return state


def commercial_organisms(tenant_id: str) -> list[str]:
    state = read_json(BASE / "state.json", {})
    organisms = state.get("organisms", {}) if isinstance(state.get("organisms"), dict) else {}
    selected = []
    for organism_id in sorted(organisms.keys()):
        manifest = read_json(BASE / "organisms" / organism_id / "task-manifest.json", {})
        if manifest.get("tenant") == tenant_id:
            selected.append(organism_id)
    return selected


def trigger_work(organism_id: str) -> dict[str, Any]:
    metabolism_path = BASE / "organisms" / organism_id / "metabolism.py"
    module = load_module(metabolism_path, f"{organism_id}_commercial_metabolism")
    return module.main()


def apply_task_result(result: dict[str, Any], digest: dict[str, Any]) -> None:
    state = read_json(BASE / "state.json", {})
    organisms = state.setdefault("organisms", {})
    org = organisms.setdefault(result["organism"], {})
    calories = int(digest.get("calories", 0))
    org["tenant"] = result.get("tenant", "demo")
    org["specialization"] = result.get("specialization", "unknown")
    org["status"] = "healthy" if result.get("verified") else "needs_attention"
    org["energy"] = int(org.get("energy", 0)) + calories
    org["lifetime_nutrients"] = int(org.get("lifetime_nutrients", 0)) + calories
    org["last_task"] = result.get("task")
    org["last_quality"] = 100 if result.get("verified") else 40
    org["last_customer_value"] = result.get("customer_value", "")
    org["updated_at"] = utc_now()

    infra = state.setdefault("infrastructure", {})
    infra["automation_actions"] = int(infra.get("automation_actions", 0)) + 1
    if result.get("verified"):
        infra["vms_provisioned"] = int(infra.get("vms_provisioned", 0)) + int(result.get("resources_created", 0))
        infra["services_deployed"] = int(infra.get("services_deployed", 0)) + int(result.get("services_deployed", 0))
    infra["last_deployment"] = utc_now()

    indexes = state.setdefault("tenant_task_indexes", {})
    indexes[f"{result.get('tenant', 'demo')}:{result['organism']}"] = int(result.get("task_index", 0))
    state["cycle"] = int(state.get("cycle", 0)) + 1
    write_json(BASE / "state.json", state)


def generate_customer_report(tenant_id: str) -> Path:
    state = read_json(BASE / "state.json", {})
    report = {
        "tenant_id": tenant_id,
        "generated_at": utc_now(),
        "billing": state.get("billing", {}),
        "infrastructure": state.get("infrastructure", {}),
        "population": state.get("population", {}),
    }
    path = BASE / "reports" / tenant_id / "latest-report.json"
    write_json(path, report)
    return path


def run_customer_cycle(tenant_id: str = "demo") -> None:
    ensure_commercial_state()
    digest_module = load_module(BASE / "digestive-engine" / "commercial_digest.py", "commercial_digest")
    log("============================================")
    log("COMMERCIAL CYCLE STARTED")
    log("============================================")
    for organism_id in commercial_organisms(tenant_id):
        log(f"WORK Triggering {organism_id}")
        result = trigger_work(organism_id)
        if result.get("error"):
            log(f"WORK {organism_id} error={result['error']}")
            continue
        digest = digest_module.digest_task_result(result)
        apply_task_result(result, digest)
        dry_run = " dry_run=True" if result.get("dry_run") else ""
        log(f"WORK {organism_id} task={result['task']} verified={result['verified']} calories={digest['calories']}{dry_run}")
        log(f"VALUE {result.get('customer_value', '')}")
    report_path = generate_customer_report(tenant_id)
    state = read_json(BASE / "state.json", {})
    log(f"BILLING Revenue this month: ${state.get('billing', {}).get('monthly_rate', 0):.2f}")
    log("CYCLE COMPLETE")
    log(f"VMs: {state.get('infrastructure', {}).get('vms_provisioned', 0)}")
    log(f"Services: {state.get('infrastructure', {}).get('services_deployed', 0)}")
    log(f"Revenue: ${state.get('billing', {}).get('monthly_rate', 0):.2f}")
    log(f"Report: {report_path}")


if __name__ == "__main__":
    run_customer_cycle("demo")

