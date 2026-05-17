"""Compatibility digestion command for CodeFarm organism output."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from codefarm_common import ROOT, load_state, log_event, save_state, write_json
from analyzer import digest


def main() -> int:
    parser = argparse.ArgumentParser(description="Digest one organism output file.")
    parser.add_argument("organism_id")
    parser.add_argument("output_file")
    parser.add_argument("--task")
    args = parser.parse_args()

    output_file = Path(args.output_file)
    if not output_file.exists():
        raise FileNotFoundError(output_file)

    payload = digest(output_file, Path(args.task) if args.task else None)
    calories = int(payload.get("nutrients", {}).get("nutrient_value", 0))

    state = load_state()
    organisms = state.setdefault("organisms", {})
    organism = organisms.setdefault(args.organism_id, {
        "id": args.organism_id,
        "status": "observed",
        "energy": 0,
        "lifetime_nutrients": 0,
        "consecutive_low_quality_outputs": 0,
    })
    organism["last_output"] = str(output_file)
    organism["last_quality"] = payload.get("nutrients", {}).get("weighted_quality", 0)
    organism["lifetime_nutrients"] = int(organism.get("lifetime_nutrients", 0)) + calories
    organism["energy"] = int(organism.get("energy", 0)) + calories
    organism["status"] = "thriving" if calories >= 120 else "weak"

    pool = state.setdefault("nutrient_pool", {})
    pool["available_calories"] = int(pool.get("available_calories", 0)) + calories
    metrics = state.setdefault("metrics", {})
    metrics["lifetime_nutrients"] = int(metrics.get("lifetime_nutrients", 0)) + calories
    metrics.setdefault("quality_history", []).append({
        "organism": args.organism_id,
        "quality": payload.get("nutrients", {}).get("weighted_quality", 0),
    })
    save_state(state)

    report_path = ROOT / "organisms" / args.organism_id / "stomach" / f"{output_file.stem}-digestion.json"
    write_json(report_path, payload)
    log_event(f"DIGEST_COMMAND organism={args.organism_id} source={output_file} calories={calories}")

    print(json.dumps({
        "organism": args.organism_id,
        "source": str(output_file),
        "nutrient_value": calories,
        "weighted_quality": payload.get("nutrients", {}).get("weighted_quality", 0),
        "report": str(report_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
