"""Collect CodeFarm observability metrics."""
from __future__ import annotations
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from codefarm_common import ROOT, load_state, write_json


def collect() -> dict:
    state = load_state()
    organisms = state.get("organisms", {}) if isinstance(state.get("organisms"), dict) else {}
    statuses = {}
    schedulable = []
    observed = []
    specializations = {}
    for organism_id, organism in organisms.items():
        organism = organism if isinstance(organism, dict) else {}
        key = organism.get("status", "unknown")
        statuses[key] = statuses.get(key, 0) + 1
        genome_path = ROOT / "organisms" / organism_id / "genome.json"
        if organism_id.startswith("org-") and genome_path.exists():
            schedulable.append(organism_id)
            import json
            try:
                genome = json.loads(genome_path.read_text(encoding="utf-8"))
            except Exception:
                genome = {}
            spec = genome.get("cognition", {}).get("specialization", organism.get("last_subsystem", "general"))
            specializations[spec] = specializations.get(spec, 0) + 1
        else:
            observed.append(organism_id)
    pool = state.get("nutrient_pool", {}) if isinstance(state.get("nutrient_pool"), dict) else {}
    improvements = state.get("infrastructure_improvements", []) if isinstance(state.get("infrastructure_improvements"), list) else []
    metrics = {
        "mode": "agent-organisms",
        "population": len(schedulable),
        "total_state_organisms": len(organisms),
        "schedulable_organisms": schedulable,
        "observed_artifacts": observed,
        "statuses": statuses,
        "specializations": specializations,
        "available_calories": pool.get("available", pool.get("available_calories", 0)),
        "consumed_calories": pool.get("consumed_calories", 0),
        "births_24h": state.get("metrics", {}).get("births_24h", 0),
        "deaths_24h": state.get("metrics", {}).get("deaths_24h", 0),
        "lifetime_nutrients": state.get("metrics", {}).get("lifetime_nutrients", 0),
        "quality_samples": len(state.get("metrics", {}).get("quality_history", [])),
        "improvements_verified": len([item for item in improvements if item.get("verified")]),
        "improvements_total": len(improvements),
        "recent_improvements": improvements[-10:],
        "tenant_id": state.get("tenant_id", "codefarm-internal"),
        "version": state.get("version", "simulation"),
    }
    write_json(ROOT / "observatory" / "metrics.json", metrics)
    return metrics


if __name__ == "__main__":
    print(collect())
