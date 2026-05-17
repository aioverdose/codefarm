"""CodeFarm Agent Genesis Orchestrator.

Runs self-building organisms through proposal, verification, promotion, and
reproduction. Organisms propose changes; only the orchestrator promotes verified
proposals into live CodeFarm subsystems.
"""
from __future__ import annotations

import importlib.util
import json
import random
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE = Path("G:/codefarm")
LOG_PATH = BASE / "logs" / f"agent-genesis-{datetime.now(timezone.utc).date().isoformat()}.log"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{utc_now()}] [AGENT] {message}"
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


def inside_root(path: Path) -> bool:
    resolved = path.resolve()
    root = BASE.resolve()
    return resolved == root or root in resolved.parents


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def active_agent_ids() -> list[str]:
    state = read_json(BASE / "state.json", {})
    organisms = state.get("organisms", {}) if isinstance(state.get("organisms"), dict) else {}
    max_population = int(state.get("population", {}).get("max", 10)) if isinstance(state.get("population"), dict) else 10
    ids = []
    for organism_id in sorted(organisms.keys()):
        genome = read_json(BASE / "organisms" / organism_id / "genome.json", {})
        if organism_id.startswith("org-") and genome.get("cognition"):
            ids.append(organism_id)
    return ids[:max_population]


def proposal_paths(proposal_path: str) -> tuple[Path, dict[str, Any], Path, Path]:
    proposal_dir = Path(proposal_path)
    manifest = read_json(proposal_dir / "proposal.json", {})
    payload = proposal_dir / manifest.get("payload_file", "")
    target = BASE / manifest.get("target_path", "")
    if not inside_root(proposal_dir) or not inside_root(payload) or not inside_root(target):
        raise ValueError("proposal path escapes CodeFarm root")
    return proposal_dir, manifest, payload, target


def snapshot_target(target: Path, proposal_id: str) -> Path | None:
    if not target.exists():
        return None
    relative = target.relative_to(BASE)
    snapshot = BASE / "snapshots" / proposal_id / relative
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(target, snapshot)
    return snapshot


def move_proposal(proposal_dir: Path, destination_root: Path) -> Path:
    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / proposal_dir.name
    if destination.exists():
        destination = destination_root / f"{proposal_dir.name}-{stamp()}"
    shutil.move(str(proposal_dir), str(destination))
    return destination


def promote_or_quarantine(result: dict[str, Any], digestion: dict[str, Any]) -> dict[str, Any]:
    proposal_path = result.get("proposal_path")
    if not proposal_path:
        return {"status": "none", "path": None}
    proposal_dir, manifest, payload, target = proposal_paths(proposal_path)
    if not digestion.get("verified"):
        quarantined = move_proposal(proposal_dir, BASE / "proposals" / "quarantine")
        log(f"QUARANTINE {quarantined} reason={digestion.get('reason')}")
        return {"status": "quarantined", "path": str(quarantined)}
    proposal_id = manifest.get("proposal_id", proposal_dir.name)
    snapshot = snapshot_target(target, proposal_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    mode = manifest.get("mode", "replace")
    content = payload.read_text(encoding="utf-8")
    if mode == "append" and target.exists():
        existing = target.read_text(encoding="utf-8")
        target.write_text(existing.rstrip() + "\n" + content, encoding="utf-8")
    else:
        target.write_text(content, encoding="utf-8")
    promoted = move_proposal(proposal_dir, BASE / "proposals" / "promoted")
    log(f"PROMOTE {proposal_id} target={target.relative_to(BASE)} snapshot={snapshot.relative_to(BASE) if snapshot else 'none'}")
    return {"status": "promoted", "path": str(promoted), "target": str(target), "snapshot": str(snapshot) if snapshot else None}


def next_organism_id(state: dict[str, Any]) -> str:
    organisms = state.get("organisms", {}) if isinstance(state.get("organisms"), dict) else {}
    n = 1
    while f"org-{n:03d}" in organisms:
        n += 1
    return f"org-{n:03d}"


def mutate_genome(parent_genome: dict[str, Any]) -> dict[str, Any]:
    genome = json.loads(json.dumps(parent_genome))
    cognition = genome.setdefault("cognition", {})
    rules = genome.get("reproduction", {}).get("mutation_rules", {})
    options = rules.get("specialization", ["terraform", "ansible", "digestive-engine", "observatory", "genome-bank"])
    if random.random() < 0.35 and options:
        cognition["specialization"] = random.choice(options)
    else:
        cognition["expertise_level"] = int(cognition.get("expertise_level", 1)) + 1
    cognition["successful_improvements"] = []
    genome["genome_id"] = f"agent-{cognition.get('specialization', 'general')}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    genome["strain"] = f"{genome.get('strain', 'self-builder')}-offspring"
    return genome


def maybe_breed() -> None:
    state = read_json(BASE / "state.json", {})
    organisms = state.get("organisms", {}) if isinstance(state.get("organisms"), dict) else {}
    population = state.setdefault("population", {})
    max_population = int(population.get("max", 10))
    agent_ids = active_agent_ids()
    if len(agent_ids) >= max_population:
        return
    pool = state.setdefault("nutrient_pool", {})
    available = int(pool.get("available", pool.get("available_calories", 0)))
    spawn_cost = int(pool.get("spawn_cost", 150))
    candidates = []
    for organism_id in agent_ids:
        organism = organisms.get(organism_id, {})
        genome = read_json(BASE / "organisms" / organism_id / "genome.json", {})
        threshold = int(genome.get("reproduction_threshold", organism.get("reproduction_threshold", 1200)))
        if int(organism.get("energy", 0)) >= threshold:
            candidates.append((organism_id, int(organism.get("lifetime_nutrients", 0))))
    if not candidates or available < spawn_cost:
        return
    parent_id = max(candidates, key=lambda item: item[1])[0]
    child_id = next_organism_id(state)
    parent_genome = read_json(BASE / "organisms" / parent_id / "genome.json", {})
    child_genome = mutate_genome(parent_genome)
    child_root = BASE / "organisms" / child_id
    for rel in ["output", "output/archive", "stomach"]:
        (child_root / rel).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(BASE / "organisms" / "agent_metabolism.py", child_root / "metabolism.py")
    write_json(child_root / "genome.json", child_genome)
    write_json(child_root / "vitals.json", {"birth_at": utc_now(), "parent": parent_id, "total_outputs": 0})
    organisms[child_id] = {"id": child_id, "status": "born_agent", "energy": 100, "birth_at": utc_now(), "updated_at": utc_now(), "parent": parent_id, "specialization": child_genome.get("cognition", {}).get("specialization", "general"), "lifetime_nutrients": 0, "consecutive_low_quality_outputs": 0}
    pool["available"] = available - spawn_cost
    pool["available_calories"] = pool["available"]
    population["active"] = len(active_agent_ids()) + 1
    metrics = state.setdefault("metrics", {})
    metrics["lifetime_births"] = int(metrics.get("lifetime_births", 0)) + 1
    metrics["births_24h"] = int(metrics.get("births_24h", 0)) + 1
    state.setdefault("events", []).append({"at": utc_now(), "event": "agent_birth", "parent": parent_id, "child": child_id, "spawn_cost": spawn_cost})
    write_json(BASE / "state.json", state)
    log(f"BIRTH {child_id} parent={parent_id} specialization={child_genome.get('cognition', {}).get('specialization', 'general')} cost={spawn_cost}")


def update_state(result: dict[str, Any], digestion: dict[str, Any], promotion: dict[str, Any]) -> None:
    state = read_json(BASE / "state.json", {})
    organisms = state.setdefault("organisms", {})
    organism = organisms.setdefault(result["organism_id"], {"id": result["organism_id"]})
    calories = int(digestion.get("calories", 0))
    organism["status"] = "self_building" if digestion.get("verified") else "needs_attention"
    organism["energy"] = int(organism.get("energy", 0)) - 12 + calories
    organism["lifetime_nutrients"] = int(organism.get("lifetime_nutrients", 0)) + calories
    organism["last_task"] = result.get("task")
    organism["last_subsystem"] = result.get("subsystem")
    organism["last_output"] = result.get("output_file")
    organism["last_proposal"] = result.get("proposal_path")
    organism["last_promotion"] = promotion.get("status")
    organism["last_quality"] = 100 if digestion.get("verified") else 25
    organism["updated_at"] = utc_now()
    genome = read_json(BASE / "organisms" / result["organism_id"] / "genome.json", {})
    if digestion.get("verified"):
        successes = genome.setdefault("cognition", {}).setdefault("successful_improvements", [])
        if result.get("task") not in successes:
            successes.append(result.get("task"))
        write_json(BASE / "organisms" / result["organism_id"] / "genome.json", genome)
    pool = state.setdefault("nutrient_pool", {})
    available = int(pool.get("available", pool.get("available_calories", 0))) + calories
    pool["available"] = available
    pool["available_calories"] = available
    metrics = state.setdefault("metrics", {})
    metrics["lifetime_nutrients"] = int(metrics.get("lifetime_nutrients", 0)) + calories
    metrics.setdefault("quality_history", []).append({"at": utc_now(), "organism": result["organism_id"], "quality": organism["last_quality"], "subsystem": result.get("subsystem")})
    improvements = state.setdefault("infrastructure_improvements", [])
    improvements.append({"at": utc_now(), "organism": result["organism_id"], "task": result.get("task"), "subsystem": result.get("subsystem"), "verified": digestion.get("verified"), "calories": calories, "output_file": result.get("output_file"), "proposal_path": result.get("proposal_path"), "promotion": promotion})
    state["cycle"] = int(state.get("cycle", 0)) + 1
    state["version"] = "3.1-proposal-promotion"
    state["status"] = "self_building"
    write_json(BASE / "state.json", state)


def run_cycle() -> None:
    digest = load_module(BASE / "digestive-engine" / "infrastructure_digest.py", "infrastructure_digest")
    log("============================================")
    log("AGENT GENESIS CYCLE STARTED")
    log("============================================")
    for organism_id in active_agent_ids():
        metabolism = load_module(BASE / "organisms" / organism_id / "metabolism.py", f"{organism_id}_agent_metabolism")
        log(f"WORK Triggering {organism_id}")
        result = metabolism.main()
        digestion = digest.digest_infrastructure_output(result)
        promotion = promote_or_quarantine(result, digestion)
        update_state(result, digestion, promotion)
        dry = " dry_run=True" if result.get("dry_run") else ""
        log(f"WORK {organism_id} task={result.get('task')} subsystem={result.get('subsystem')} verified={digestion.get('verified')} promotion={promotion.get('status')} calories={digestion.get('calories')}{dry}")
        log(f"PROPOSAL {result.get('proposal_path')}")
    maybe_breed()
    log("AGENT GENESIS CYCLE COMPLETE")
    state = read_json(BASE / "state.json", {})
    log(f"Pool: {state.get('nutrient_pool', {}).get('available', 0)}")
    log(f"Improvements: {len(state.get('infrastructure_improvements', []))}")


if __name__ == "__main__":
    run_cycle()
