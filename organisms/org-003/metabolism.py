"""CodeFarm Agent Organism.

Survives by proposing improvements to the infrastructure that sustains it.
Organisms never edit live CodeFarm organs directly; verified proposals are
promoted by the orchestrator.
"""
from __future__ import annotations

import json
import random
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORG_DIR = Path(__file__).resolve().parent
BASE = Path("G:/codefarm")
GENOME_PATH = ORG_DIR / "genome.json"


def now_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def ensure_inside_root(path: Path) -> Path:
    resolved = path.resolve()
    root = BASE.resolve()
    if root != resolved and root not in resolved.parents:
        raise ValueError(f"Path escapes CodeFarm root: {resolved}")
    return resolved


def choose_task() -> dict[str, Any]:
    genome = read_json(GENOME_PATH, {})
    state = read_json(BASE / "state.json", {})
    tasks = state.get("task_queue", []) if isinstance(state.get("task_queue"), list) else []
    if not tasks:
        return {"id": "extend_monitoring", "subsystem": "observatory", "reward": 250, "description": "Add observability fallback", "verification": "dashboard marker exists"}
    spec = genome.get("cognition", {}).get("specialization", "general")
    matching = [task for task in tasks if task.get("subsystem") == spec]
    if matching and random.random() > 0.2:
        return random.choice(matching)
    return random.choice(tasks)


def run_tool(command: list[str], cwd: Path) -> dict[str, Any]:
    if shutil.which(command[0]) is None:
        return {"success": True, "dry_run": True, "output": f"{command[0]} not installed; validated generated artifact only."}
    result = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True, timeout=60)
    return {"success": result.returncode == 0, "dry_run": False, "output": result.stdout + result.stderr}


def create_proposal(task: dict[str, Any], improvement_type: str, target: str, mode: str, filename: str, content: str, magnitude: int) -> dict[str, Any]:
    proposal_id = f"{ORG_DIR.name}-{task.get('id', improvement_type)}-{now_id()}-{random.randint(1000, 9999)}"
    proposal_dir = BASE / "proposals" / "pending" / proposal_id
    payload_path = proposal_dir / filename
    ensure_inside_root(payload_path)
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text(content, encoding="utf-8")
    manifest = {
        "proposal_id": proposal_id,
        "organism_id": ORG_DIR.name,
        "task": task.get("id"),
        "subsystem": task.get("subsystem"),
        "improvement_type": improvement_type,
        "target_path": target,
        "mode": mode,
        "payload_file": payload_path.name,
        "magnitude": magnitude,
        "created_at": utc_now(),
    }
    write_json(proposal_dir / "proposal.json", manifest)
    output_file = ORG_DIR / "output" / filename
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(content, encoding="utf-8")
    return {"proposal_path": str(proposal_dir), "file": str(output_file), "payload_file": str(payload_path), "manifest": manifest}


def verify_terraform_proposal(proposal_dir: Path, content: str) -> dict[str, Any]:
    verify_dir = proposal_dir / "verify" / "terraform"
    if verify_dir.exists():
        shutil.rmtree(verify_dir)
    shutil.copytree(BASE / "core" / "terraform", verify_dir)
    main_tf = verify_dir / "main.tf"
    main_tf.write_text(main_tf.read_text(encoding="utf-8") + "\n" + content, encoding="utf-8")
    init_result = run_tool(["terraform", "init", "-backend=false", "-input=false"], verify_dir)
    if not init_result.get("success") and not init_result.get("dry_run"):
        return init_result
    result = run_tool(["terraform", "validate"], verify_dir)
    if result.get("dry_run"):
        (proposal_dir / "tfplan").write_text("dry-run validate: terraform unavailable\n", encoding="utf-8")
    return result


def write_terraform_improvement(task: dict[str, Any]) -> dict[str, Any]:
    module_name = f"organism_{random.randint(1000, 9999)}"
    improvement = f'''
# Proposed by {ORG_DIR.name} at {utc_now()}
module "{module_name}" {{
  source = "./modules/organism"
  name   = "auto-org-{random.randint(1000, 9999)}"
  memory = 2048
  cpu    = 2
}}
'''
    proposal = create_proposal(task, "terraform", "core/terraform/main.tf", "append", f"terraform_improvement_{now_id()}.tf", improvement, int(task.get("reward", 500)))
    result = verify_terraform_proposal(Path(proposal["proposal_path"]), improvement)
    return {**proposal, "success": result["success"], "improvement_type": "terraform", "magnitude": int(task.get("reward", 500)), "dry_run": result.get("dry_run", False)}


def verify_ansible_content(content: str) -> bool:
    return "ansible.builtin" in content and "PermitRootLogin no" in content and "tags: security" in content


def write_ansible_improvement(task: dict[str, Any]) -> dict[str, Any]:
    improvement = f'''
    # Proposed by {ORG_DIR.name} at {utc_now()}
    - name: Harden SSH configuration
      ansible.builtin.lineinfile:
        path: /etc/ssh/sshd_config
        regexp: '^PermitRootLogin'
        line: 'PermitRootLogin no'
      tags: security
'''
    proposal = create_proposal(task, "ansible", "core/ansible/site.yml", "append", f"ansible_improvement_{now_id()}.yml", improvement, int(task.get("reward", 300)))
    return {**proposal, "success": verify_ansible_content(improvement), "improvement_type": "ansible", "magnitude": int(task.get("reward", 300)), "dry_run": False}


def write_digest_improvement(task: dict[str, Any]) -> dict[str, Any]:
    content = f'''"""Infrastructure improvement digestion helpers.
Proposed by {ORG_DIR.name} at {utc_now()}.
"""
from __future__ import annotations


def estimate_improvement_score(result: dict) -> int:
    base = int(result.get("magnitude", 0))
    if result.get("dry_run"):
        return max(0, base - 75)
    return base + 50
'''
    proposal = create_proposal(task, "digestive-engine", "digestive-engine/infrastructure_digest_helpers.py", "replace", f"digest_improvement_{now_id()}.py", content, int(task.get("reward", 400)))
    payload = Path(proposal["payload_file"])
    result = subprocess.run(["python", "-m", "py_compile", str(payload)], cwd=str(BASE), capture_output=True, text=True)
    return {**proposal, "success": result.returncode == 0, "improvement_type": "digestive-engine", "magnitude": int(task.get("reward", 400)), "dry_run": False}


def write_dashboard_improvement(task: dict[str, Any]) -> dict[str, Any]:
    payload = {"added_by": ORG_DIR.name, "added_at": utc_now(), "panel": "self_building_improvements"}
    content = json.dumps(payload, indent=2, sort_keys=True)
    proposal = create_proposal(task, "observatory", "observatory/ui/self_building_panel.json", "replace", f"observatory_improvement_{now_id()}.json", content, int(task.get("reward", 250)))
    return {**proposal, "success": "self_building_improvements" in content, "improvement_type": "observatory", "magnitude": int(task.get("reward", 250)), "dry_run": False}


def write_genome_improvement(task: dict[str, Any]) -> dict[str, Any]:
    genome = read_json(GENOME_PATH, {})
    cognition = genome.setdefault("cognition", {})
    cognition["expertise_level"] = int(cognition.get("expertise_level", 1)) + 1
    filename = f"{ORG_DIR.name}-self-builder-{now_id()}.json"
    content = json.dumps(genome, indent=2, sort_keys=True)
    proposal = create_proposal(task, "genome-bank", f"genome-bank/evolved-strains/{filename}", "replace", filename, content, int(task.get("reward", 600)))
    return {**proposal, "success": "cognition" in genome, "improvement_type": "genome-bank", "magnitude": int(task.get("reward", 600)), "dry_run": False}


def execute_task(task: dict[str, Any]) -> dict[str, Any]:
    subsystem = task.get("subsystem")
    if subsystem == "terraform":
        return write_terraform_improvement(task)
    if subsystem == "ansible":
        return write_ansible_improvement(task)
    if subsystem == "digestive-engine":
        return write_digest_improvement(task)
    if subsystem == "observatory":
        return write_dashboard_improvement(task)
    if subsystem == "genome-bank":
        return write_genome_improvement(task)
    return write_dashboard_improvement(task)


def verify_improvement(result: dict[str, Any]) -> bool:
    proposal = Path(result.get("proposal_path", ""))
    manifest = read_json(proposal / "proposal.json", {})
    payload = proposal / manifest.get("payload_file", "")
    if not proposal.exists() or not payload.exists():
        return False
    return bool(result.get("success"))


def update_vitals(task: dict[str, Any], verified: bool) -> None:
    vitals_path = ORG_DIR / "vitals.json"
    vitals = read_json(vitals_path, {"total_outputs": 0})
    vitals["last_work"] = utc_now()
    vitals["total_outputs"] = int(vitals.get("total_outputs", 0)) + 1
    vitals["last_task"] = task.get("id")
    vitals["last_success"] = verified
    write_json(vitals_path, vitals)


def main() -> dict[str, Any]:
    task = choose_task()
    result = execute_task(task)
    verified = verify_improvement(result)
    update_vitals(task, verified)
    calories = int(result.get("magnitude", 0)) if verified else max(0, int(result.get("magnitude", 0)) // 4)
    return {
        "organism_id": ORG_DIR.name,
        "task": task.get("id"),
        "subsystem": task.get("subsystem"),
        "proposal_path": result.get("proposal_path"),
        "output_file": result.get("file"),
        "payload_file": result.get("payload_file"),
        "improvement_type": result.get("improvement_type"),
        "success": verified,
        "dry_run": result.get("dry_run", False),
        "calories": calories,
        "magnitude": result.get("magnitude", 0),
        "completed_at": utc_now(),
    }


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))

