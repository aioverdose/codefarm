"""Archive failed simulated organisms."""
from __future__ import annotations
import shutil
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from codefarm_common import ROOT, load_state, log_event, save_state, utc_now, write_json

def terminate(organism_id: str, reason: str) -> None:
    state = load_state()
    organism = state.get("organisms", {}).pop(organism_id, None)
    if organism is None:
        return
    archive = ROOT / "genome-bank" / "failures" / f"{organism_id}-{utc_now().replace(':', '')}.json"
    write_json(archive, {"organism": organism, "reason": reason, "autopsy_at": utc_now()})
    org_root = ROOT / "organisms" / organism_id
    if org_root.exists():
        target = ROOT / "genome-bank" / "failures" / organism_id
        if not target.exists():
            shutil.move(str(org_root), str(target))
    metrics = state.setdefault("metrics", {})
    metrics["lifetime_deaths"] = int(metrics.get("lifetime_deaths", 0)) + 1
    metrics["deaths_24h"] = int(metrics.get("deaths_24h", 0)) + 1
    save_state(state)
    log_event(f"SURGERY organism={organism_id} reason={reason}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("organism_id")
    parser.add_argument("reason")
    args = parser.parse_args()
    terminate(args.organism_id, args.reason)
