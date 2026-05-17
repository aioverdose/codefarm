"""Detect unhealthy organisms."""
from __future__ import annotations
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from codefarm_common import load_state

def detect_pathogens() -> list[dict]:
    state = load_state()
    findings = []
    for organism_id, organism in state.get("organisms", {}).items():
        if int(organism.get("energy", 0)) < 20:
            findings.append({"organism": organism_id, "reason": "energy_below_20"})
        if int(organism.get("consecutive_low_quality_outputs", 0)) > 3:
            findings.append({"organism": organism_id, "reason": "consecutive_low_quality_outputs"})
    return findings

if __name__ == "__main__":
    print(detect_pathogens())
