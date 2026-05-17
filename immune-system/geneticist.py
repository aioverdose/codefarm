"""Review strains and promote high performers."""
from __future__ import annotations
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from codefarm_common import ROOT, load_state, log_event, write_json

def review() -> dict:
    state = load_state()
    organisms = state.get("organisms", {})
    if not organisms:
        return {"status": "no_population"}
    best_id, best = max(organisms.items(), key=lambda item: int(item[1].get("lifetime_nutrients", 0)))
    report = {"best_organism": best_id, "lifetime_nutrients": best.get("lifetime_nutrients", 0), "genome": best.get("genome", {})}
    if int(best.get("lifetime_nutrients", 0)) > 1000:
        write_json(ROOT / "genome-bank" / "evolved-strains" / f"{best_id}-strain.json", report)
        log_event(f"GENETICIST promoted={best_id}")
    return report

if __name__ == "__main__":
    print(review())
