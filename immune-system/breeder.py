"""Spawn simulated organisms from genomes."""
from __future__ import annotations
import random
import shutil
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from codefarm_common import ROOT, load_state, log_event, read_json, save_state, utc_now, write_json

def next_organism_id(state: dict) -> str:
    existing = state.get("organisms", {})
    n = 1
    while f"org-{n:03d}" in existing:
        n += 1
    return f"org-{n:03d}"

def spawn(parent_id: str | None = None) -> str:
    state = load_state()
    genome = read_json(ROOT / "genome-bank" / "base-genome.json", {})
    if parent_id and parent_id in state.get("organisms", {}):
        genome.update(state["organisms"][parent_id].get("genome", {}))
        genome["temperature"] = round(max(0.0, min(1.0, float(genome.get("temperature", 0.2)) + random.uniform(-0.05, 0.05))), 3)
        genome["strain"] = f"{genome.get('strain', 'base')}-mutant"
    organism_id = next_organism_id(state)
    org_root = ROOT / "organisms" / organism_id
    for rel in ["stomach", "output", "output/archive"]:
        (org_root / rel).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "organisms" / "metabolism_template.py", org_root / "metabolism.py")
    write_json(org_root / "genome.json", genome)
    organism = {"id": organism_id, "status": "born", "energy": 100, "birth_at": utc_now(), "updated_at": utc_now(), "genome": genome, "energy_decay_per_cycle": int(genome.get("energy_decay_per_cycle", 8)), "starvation_threshold": int(genome.get("starvation_threshold", 120)), "reproduction_threshold": int(genome.get("reproduction_threshold", 900)), "consecutive_low_quality_outputs": 0, "lifetime_nutrients": 0}
    state.setdefault("organisms", {})[organism_id] = organism
    metrics = state.setdefault("metrics", {})
    metrics["lifetime_births"] = int(metrics.get("lifetime_births", 0)) + 1
    metrics["births_24h"] = int(metrics.get("births_24h", 0)) + 1
    save_state(state)
    log_event(f"BIRTH organism={organism_id} parent={parent_id or 'none'}")
    return organism_id

if __name__ == "__main__":
    print(spawn())
