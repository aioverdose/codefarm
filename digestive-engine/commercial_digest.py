"""CodeFarm Commercial Digestion.

Verifies customer value was delivered and converts the result into revenue-facing
metrics. This module keeps legacy digest compatibility in analyzer.py separate.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BASE = Path("G:/codefarm")


def read_state() -> dict[str, Any]:
    try:
        return json.loads((BASE / "state.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_state(state: dict[str, Any]) -> None:
    (BASE / "state.json").write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def verify_customer_value(task_result: dict[str, Any]) -> int:
    calories = 50
    customer_value = str(task_result.get("customer_value", "")).lower()
    if task_result.get("verified"):
        calories += int(task_result.get("reward", 0))
        if "web server" in customer_value:
            calories += 100
        if "compliance" in customer_value or "soc2" in customer_value:
            calories += 400
        if "orchestration" in customer_value or "container" in customer_value:
            calories += 150
        if "backup" in customer_value:
            calories += 250
    else:
        calories = max(0, calories - 150)
    return calories


def calculate_monthly_revenue(state: dict[str, Any]) -> float:
    billing = state.get("billing", {}) if isinstance(state.get("billing"), dict) else {}
    actions = int(billing.get("automation_actions", 0))
    prevented = int(billing.get("incidents_prevented", 0))
    uptime = float(billing.get("uptime_percentage", 100.0))
    action_value = actions * float(state.get("nutrient_pool", {}).get("revenue_per_action", 0.10))
    incident_value = prevented * 50
    uptime_bonus = 200 if uptime > 99.9 else 0
    return round(action_value + incident_value + uptime_bonus, 2)


def update_billing_metrics(task_result: dict[str, Any], calories: int) -> dict[str, Any]:
    state = read_state()
    billing = state.setdefault("billing", {})
    infra = state.setdefault("infrastructure", {})
    pool = state.setdefault("nutrient_pool", {})

    billing["automation_actions"] = int(billing.get("automation_actions", 0)) + 1
    if task_result.get("verified"):
        billing["incidents_prevented"] = int(billing.get("incidents_prevented", 0)) + 1
        infra["health_checks_passed"] = int(infra.get("health_checks_passed", 0)) + 1
    else:
        infra["health_checks_failed"] = int(infra.get("health_checks_failed", 0)) + 1

    total_checks = int(infra.get("health_checks_passed", 0)) + int(infra.get("health_checks_failed", 0))
    billing["uptime_percentage"] = round((int(infra.get("health_checks_passed", 0)) / total_checks) * 100, 2) if total_checks else 100.0
    billing["monthly_rate"] = calculate_monthly_revenue(state)
    pool["available"] = int(pool.get("available", pool.get("available_calories", 0))) + calories
    pool["available_calories"] = pool["available"]
    write_state(state)
    return {"billing": billing, "infrastructure": infra, "nutrient_pool": pool}


def digest_task_result(task_result: dict[str, Any]) -> dict[str, Any]:
    calories = verify_customer_value(task_result)
    updated = update_billing_metrics(task_result, calories)
    return {
        "calories": calories,
        "customer": task_result.get("tenant", "unknown"),
        "verified": bool(task_result.get("verified")),
        "billing_action": True,
        "monthly_revenue": updated["billing"].get("monthly_rate", 0),
    }


def main() -> int:
    import sys
    if len(sys.argv) < 2:
        raise SystemExit("Usage: commercial_digest.py '<task_result_json>'")
    print(json.dumps(digest_task_result(json.loads(sys.argv[1])), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
