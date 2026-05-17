"""Digest infrastructure improvement proposals produced by CodeFarm agents."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

BASE = Path("G:/codefarm")


def read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def inside_root(path: Path) -> bool:
    try:
        resolved = path.resolve()
        root = BASE.resolve()
        return resolved == root or root in resolved.parents
    except OSError:
        return False


def proposal_parts(result: dict[str, Any]) -> tuple[Path, dict[str, Any], Path]:
    proposal_dir = Path(result.get("proposal_path", ""))
    manifest = read_json(proposal_dir / "proposal.json", {})
    payload = proposal_dir / manifest.get("payload_file", "")
    return proposal_dir, manifest, payload


def digest_infrastructure_output(result: dict[str, Any]) -> dict[str, Any]:
    proposal_dir, manifest, payload = proposal_parts(result)
    verified = bool(result.get("success"))
    bonus = 0
    reason = "verified"
    target = BASE / manifest.get("target_path", "")
    if not proposal_dir.exists() or not payload.exists() or not inside_root(proposal_dir) or not inside_root(target):
        return {"verified": False, "calories": 0, "bonus": 0, "reason": "invalid proposal path", "proposal_path": str(proposal_dir)}
    improvement_type = manifest.get("improvement_type")
    text = payload.read_text(encoding="utf-8", errors="ignore")
    if improvement_type == "terraform":
        verified = verified and "module" in text and "./modules/organism" in text
        bonus = 100 if verified else 0
        reason = "terraform proposal validated"
    elif improvement_type == "ansible":
        verified = verified and "ansible.builtin" in text and "PermitRootLogin no" in text
        bonus = 150 if verified else 0
        reason = "ansible hardening proposal validated"
    elif improvement_type == "digestive-engine":
        compile_result = subprocess.run(["python", "-m", "py_compile", str(payload)], cwd=str(BASE), capture_output=True, text=True)
        verified = compile_result.returncode == 0 and "estimate_improvement_score" in text
        bonus = 75 if verified else 0
        reason = "digest helper compiled"
    elif improvement_type == "observatory":
        try:
            parsed = json.loads(text)
            verified = parsed.get("panel") == "self_building_improvements"
        except json.JSONDecodeError:
            verified = False
        bonus = 50 if verified else 0
        reason = "observatory panel proposal validated"
    elif improvement_type == "genome-bank":
        try:
            parsed = json.loads(text)
            verified = "cognition" in parsed
        except json.JSONDecodeError:
            verified = False
        bonus = 125 if verified else 0
        reason = "genome proposal validated"
    else:
        verified = False
        reason = "unknown improvement type"
    base_calories = int(result.get("calories", 0))
    if not verified:
        base_calories = max(0, base_calories - 200)
    if result.get("dry_run"):
        bonus = max(0, bonus - 50)
    return {
        "verified": verified,
        "calories": base_calories + bonus,
        "bonus": bonus,
        "reason": reason,
        "improvement_type": improvement_type,
        "proposal_path": str(proposal_dir),
        "output_file": str(payload),
    }


def main() -> int:
    import sys
    if len(sys.argv) < 2:
        raise SystemExit("Usage: infrastructure_digest.py '<result_json>'")
    print(json.dumps(digest_infrastructure_output(json.loads(sys.argv[1])), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
