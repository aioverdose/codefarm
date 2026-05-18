"""CodeFarm Build Control server.

Local-only stdlib HTTP server for configuring projects, project directions,
assigned organisms, build cadence, and automatic agent Genesis cycles.
"""
from __future__ import annotations

import os

import io
import json
import re
import shutil
import subprocess
import sys
import threading
import zipfile
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE = Path(os.environ.get("CODEFARM_HOME", Path(__file__).resolve().parent))
STATE_PATH = BASE / "state.json"
CONTROL_DIR = BASE / "observatory" / "control"
CHAT_PATH = BASE / "development-ledger" / "orchestrator-chat.json"
HOST = "127.0.0.1"
PORT = 8765
CODE_SEARCH_EXCLUDED_DIRS = {
    ".git",
    ".next",
    ".terraform",
    "__pycache__",
    "dist",
    "logs",
    "node_modules",
    "python-venv",
    "proposals",
    "snapshots",
    "site-packages",
    "terraform",
    "tmp",
    "venv",
}
CODE_SEARCH_SUFFIXES = {".bat", ".cmd", ".css", ".html", ".js", ".json", ".md", ".mjs", ".ps1", ".py", ".tf", ".ts", ".tsx", ".yml", ".yaml"}
CODE_SEARCH_NAMES = {"LICENSE", "README.md", "product.json"}
CODE_SEARCH_EXCLUDED_FILES = {"data.js", "metrics.json", "package-lock.json", "self_building_panel.json", "state.json"}
CODE_SEARCH_MAX_FILE_BYTES = 220_000

scheduler = {
    "running": False,
    "thread": None,
    "stop": threading.Event(),
    "last_cycle_at": None,
    "last_error": None,
    "cycles_started": 0,
}
state_lock = threading.Lock()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or f"project-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def read_json(path: Path, default):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def default_control() -> dict:
    return {
        "directions": "Improve CodeFarm infrastructure through verified Terraform, Ansible, digestive-engine, observatory, and genome-bank proposals.",
        "assigned_orgs": [],
        "build_rate_seconds": 60,
        "build_rate_mode": "timed",
        "target_improvements": 50,
        "auto_enabled": False,
        "app_prompt": "",
        "project_type": "codefarm",
        "updated_at": utc_now(),
    }


def default_project(project_id: str = "codefarm-core", name: str = "CodeFarm Core") -> dict:
    control = default_control()
    control.update({"project_id": project_id, "project_name": name})
    return {
        "id": project_id,
        "name": name,
        "status": "active",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        **control,
    }


def ensure_projects(state: dict) -> tuple[dict, dict]:
    projects = state.setdefault("projects", {})
    if not isinstance(projects, dict):
        projects = {}
        state["projects"] = projects
    active_id = state.get("active_project_id") or state.get("build_control", {}).get("project_id") or "codefarm-core"
    if active_id not in projects:
        project = default_project(active_id, "CodeFarm Core" if active_id == "codefarm-core" else active_id.replace("-", " ").title())
        legacy = state.get("build_control", {}) if isinstance(state.get("build_control"), dict) else {}
        for key in ["directions", "assigned_orgs", "build_rate_seconds", "build_rate_mode", "target_improvements", "auto_enabled"]:
            if key in legacy:
                project[key] = legacy[key]
        projects[active_id] = project
    state["active_project_id"] = active_id
    return projects, projects[active_id]


def sync_control_from_project(state: dict, project: dict) -> dict:
    control = default_control()
    for key in ["directions", "assigned_orgs", "build_rate_seconds", "build_rate_mode", "target_improvements", "auto_enabled", "updated_at"]:
        if key in project:
            control[key] = project[key]
    control["project_id"] = project["id"]
    control["project_name"] = project.get("name", project["id"])
    control["app_prompt"] = project.get("app_prompt", "")
    control["project_type"] = project.get("project_type", "codefarm")
    state["build_control"] = control
    return control


def save_control(payload: dict) -> dict:
    with state_lock:
        state = read_json(STATE_PATH, {})
        projects, project = ensure_projects(state)
        project_id = payload.get("project_id") or state.get("active_project_id") or project["id"]
        if project_id not in projects:
            project_id = project["id"]
        project = projects[project_id]
        state["active_project_id"] = project_id
        if "name" in payload:
            project["name"] = str(payload.get("name", project.get("name", project_id))).strip()[:120] or project_id
        if "directions" in payload:
            project["directions"] = str(payload.get("directions", ""))[:4000]
        if "app_prompt" in payload:
            project["app_prompt"] = str(payload.get("app_prompt", ""))[:8000]
        if "project_type" in payload:
            project["project_type"] = str(payload.get("project_type") or project.get("project_type", "codefarm"))[:40]
        if "assigned_orgs" in payload and isinstance(payload["assigned_orgs"], list):
            project["assigned_orgs"] = [str(item) for item in payload["assigned_orgs"] if str(item).startswith("org-")]
        if "build_rate_mode" in payload:
            mode = str(payload.get("build_rate_mode") or "timed")
            project["build_rate_mode"] = "autonomous" if mode == "autonomous" else "timed"
        if "build_rate_seconds" in payload:
            project["build_rate_seconds"] = max(0, min(86400, int(payload.get("build_rate_seconds", 60))))
        if "target_improvements" in payload:
            project["target_improvements"] = max(1, int(payload.get("target_improvements") or 50))
        if "auto_enabled" in payload:
            project["auto_enabled"] = bool(payload.get("auto_enabled"))
        project["updated_at"] = utc_now()
        control = sync_control_from_project(state, project)
        write_json(STATE_PATH, state)
        return control


def scaffold_app_project(project: dict) -> None:
    app_root = BASE / "projects" / project["id"] / "app"
    app_root.mkdir(parents=True, exist_ok=True)
    spec = {
        "project_id": project["id"],
        "name": project.get("name", project["id"]),
        "prompt": project.get("app_prompt", ""),
        "created_at": project.get("created_at", utc_now()),
        "files": ["index.html", "styles.css", "app.js", "README.md"],
    }
    write_json(app_root.parent / "project-spec.json", spec)
    readme = app_root / "README.md"
    if not readme.exists():
        readme.write_text(f"# {spec['name']}\n\nPrompt:\n{spec['prompt']}\n", encoding="utf-8")


def project_root(project_id: str) -> Path:
    projects_root = (BASE / "projects").resolve()
    root = (projects_root / slugify(project_id)).resolve()
    if root != projects_root and projects_root in root.parents:
        return root
    raise ValueError("Project path escapes the CodeFarm sandbox")


def create_project(payload: dict) -> dict:
    with state_lock:
        state = read_json(STATE_PATH, {})
        projects, _ = ensure_projects(state)
        name = str(payload.get("name") or "New Project").strip()[:120] or "New Project"
        project_id = slugify(str(payload.get("id") or name))
        base_id = project_id
        suffix = 2
        while project_id in projects:
            project_id = f"{base_id}-{suffix}"
            suffix += 1
        project = default_project(project_id, name)
        app_prompt = str(payload.get("app_prompt") or "").strip()
        if app_prompt:
            project["project_type"] = "app"
            project["app_prompt"] = app_prompt[:8000]
            project["app_root"] = f"projects/{project_id}/app"
            project["directions"] = f"Build this app from the project prompt: {app_prompt[:3500]}"
            project["target_improvements"] = int(payload.get("target_improvements") or 4)
            scaffold_app_project(project)
        for key in ["directions", "assigned_orgs", "build_rate_seconds", "build_rate_mode", "target_improvements"]:
            if key in payload:
                project[key] = payload[key]
        if app_prompt and not str(project.get("directions", "")).strip():
            project["directions"] = f"Build this app from the project prompt: {app_prompt[:3500]}"
        project["auto_enabled"] = False
        projects[project_id] = project
        state["active_project_id"] = project_id
        control = sync_control_from_project(state, project)
        write_json(STATE_PATH, state)
        return {"project": project, "control": control}


def reset_project(payload: dict) -> dict:
    stop_scheduler()
    recreate_payload = payload.get("project") if isinstance(payload.get("project"), dict) else None
    with state_lock:
        state = read_json(STATE_PATH, {})
        projects, active_project = ensure_projects(state)
        project_id = slugify(str(payload.get("project_id") or active_project.get("id") or state.get("active_project_id") or ""))
        if not project_id:
            raise ValueError("No project selected to reset")
        if project_id == "codefarm-core":
            raise ValueError("The CodeFarm core project cannot be deleted by reset")

        removed_paths = []
        root = project_root(project_id)
        if root.exists():
            shutil.rmtree(root)
            removed_paths.append(str(root))

        improvements = state.get("infrastructure_improvements", [])
        if isinstance(improvements, list):
            state["infrastructure_improvements"] = [item for item in improvements if item.get("project_id") != project_id]

        if project_id in projects:
            del projects[project_id]

        fallback = projects.get("codefarm-core")
        if not fallback:
            fallback = default_project("codefarm-core", "CodeFarm Core")
            projects["codefarm-core"] = fallback
        state["active_project_id"] = fallback["id"]
        control = sync_control_from_project(state, fallback)
        write_json(STATE_PATH, state)

    if recreate_payload or payload.get("recreate"):
        project_payload = recreate_payload or payload
        created = create_project(project_payload)
        return {"ok": True, "reset_project_id": project_id, "removed_paths": removed_paths, "created": created, "snapshot": snapshot()}

    return {"ok": True, "reset_project_id": project_id, "removed_paths": removed_paths, "control": control, "snapshot": snapshot()}


def select_project(project_id: str) -> dict:
    with state_lock:
        state = read_json(STATE_PATH, {})
        projects, _ = ensure_projects(state)
        if project_id not in projects:
            raise ValueError(f"Unknown project: {project_id}")
        state["active_project_id"] = project_id
        control = sync_control_from_project(state, projects[project_id])
        write_json(STATE_PATH, state)
        return control


def run_cycle() -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, str(BASE / "agent_orchestrator.py")],
        cwd=str(BASE),
        capture_output=True,
        text=True,
        timeout=300,
    )
    subprocess.run([sys.executable, str(BASE / "observatory" / "metrics-collector.py")], cwd=str(BASE), capture_output=True, text=True, timeout=60)
    subprocess.run([sys.executable, str(BASE / "observatory" / "ui-generator.py")], cwd=str(BASE), capture_output=True, text=True, timeout=60)
    return result.returncode, result.stdout + result.stderr


def scheduler_loop() -> None:
    scheduler["running"] = True
    scheduler["last_error"] = None
    try:
        while not scheduler["stop"].is_set():
            state = read_json(STATE_PATH, {})
            _, project = ensure_projects(state)
            sync_control_from_project(state, project)
            write_json(STATE_PATH, state)
            if not project.get("auto_enabled"):
                break
            scheduler["cycles_started"] += 1
            code, output = run_cycle()
            scheduler["last_cycle_at"] = utc_now()
            if code != 0:
                scheduler["last_error"] = output[-2000:]
                save_control({"auto_enabled": False})
                break
            latest_control = read_json(STATE_PATH, {}).get("build_control", {})
            mode = latest_control.get("build_rate_mode", "timed")
            delay = 0 if mode == "autonomous" else int(latest_control.get("build_rate_seconds", 60))
            if delay <= 0:
                if scheduler["stop"].is_set():
                    break
                continue
            if scheduler["stop"].wait(delay):
                break
    finally:
        scheduler["running"] = False


def start_scheduler() -> None:
    if scheduler["running"]:
        return
    scheduler["stop"] = threading.Event()
    save_control({"auto_enabled": True})
    thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler["thread"] = thread
    thread.start()


def stop_scheduler() -> None:
    save_control({"auto_enabled": False})
    scheduler["stop"].set()


def proposal_counts() -> dict:
    root = BASE / "proposals"
    return {name: len([p for p in (root / name).glob("*") if p.is_dir()]) for name in ["pending", "promoted", "quarantine"]}


def organism_rows(state: dict) -> list[dict]:
    organisms = state.get("organisms", {}) if isinstance(state.get("organisms"), dict) else {}
    control = state.get("build_control", {}) if isinstance(state.get("build_control"), dict) else {}
    assigned = set(control.get("assigned_orgs", []))
    rows = []
    for oid, org in sorted(organisms.items()):
        if not oid.startswith("org-"):
            continue
        genome = read_json(BASE / "organisms" / oid / "genome.json", {})
        cognition = genome.get("cognition", {}) if isinstance(genome, dict) else {}
        rows.append({
            "id": oid,
            "assigned": not assigned or oid in assigned,
            "status": org.get("status", "unknown"),
            "energy": int(org.get("energy", 0)),
            "specialization": cognition.get("specialization", org.get("specialization", "general")),
            "expertise": cognition.get("expertise_level", 1),
            "last_task": org.get("last_task"),
            "last_promotion": org.get("last_promotion"),
            "last_quality": org.get("last_quality", 0),
            "last_decay": org.get("last_decay", 0),
            "last_penalty": org.get("last_penalty", 0),
            "lifetime_nutrients": org.get("lifetime_nutrients", 0),
            "last_output": org.get("last_output"),
            "last_proposal": org.get("last_proposal"),
        })
    return rows


def active_project_improvements(state: dict, project_id: str) -> list[dict]:
    improvements = state.get("infrastructure_improvements", []) if isinstance(state.get("infrastructure_improvements"), list) else []
    tagged = [item for item in improvements if item.get("project_id") == project_id]
    if tagged:
        return tagged
    return improvements if project_id == "codefarm-core" else []


def anomalies(state: dict, orgs: list[dict], counts: dict, build_pct: float) -> list[dict]:
    items = []
    for org in orgs:
        if org["status"] == "dead":
            items.append({"severity": "critical", "title": f"{org['id']} dead", "detail": "Energy reached zero."})
        elif org["energy"] < 250:
            items.append({"severity": "warning", "title": f"{org['id']} low energy", "detail": f"Energy is {org['energy']}."})
        if org.get("last_promotion") == "quarantined":
            items.append({"severity": "warning", "title": f"{org['id']} proposal quarantined", "detail": "Last improvement failed verification."})
    if counts.get("pending", 0):
        items.append({"severity": "warning", "title": "Pending proposals", "detail": f"{counts['pending']} proposal(s) have not been resolved."})
    improvements = state.get("infrastructure_improvements", []) if isinstance(state.get("infrastructure_improvements"), list) else []
    if improvements:
        verified = len([item for item in improvements if item.get("verified")])
        rate = verified / len(improvements)
        if rate < 0.8:
            items.append({"severity": "warning", "title": "Verification rate below 80%", "detail": f"Current rate is {rate * 100:.1f}%."})
    if build_pct >= 100:
        items.append({"severity": "info", "title": "Build target reached", "detail": "Create the next project or increase target improvements."})
    if not items:
        items.append({"severity": "ok", "title": "No anomalies", "detail": "Agents are building within current thresholds."})
    return items


def safe_relative(path_value: str) -> Path | None:
    if not path_value:
        return None
    path = Path(path_value)
    if path.is_absolute():
        resolved = path.resolve()
    else:
        resolved = (BASE / path).resolve()
    root = BASE.resolve()
    if resolved == root or root in resolved.parents:
        return resolved
    return None


def proposal_manifest_for(item: dict) -> dict:
    candidates = []
    promotion = item.get("promotion", {}) if isinstance(item.get("promotion"), dict) else {}
    for value in [promotion.get("path"), item.get("proposal_path")]:
        path = safe_relative(str(value or ""))
        if path:
            candidates.append(path / "proposal.json")
    for candidate in candidates:
        manifest = read_json(candidate, {})
        if manifest:
            return manifest
    return {}


def explain_build(item: dict, manifest: dict | None = None) -> str:
    manifest = manifest or {}
    organism = item.get("organism") or manifest.get("organism_id") or "An organism"
    task = item.get("task") or manifest.get("task") or "build work"
    subsystem = item.get("subsystem") or manifest.get("subsystem") or "CodeFarm"
    target = manifest.get("target_path") or item.get("target_path")
    verified = item.get("verified")
    action_by_subsystem = {
        "terraform": "is expanding the infrastructure blueprint with VM provisioning capacity",
        "ansible": "is adding configuration and hardening automation",
        "digestive-engine": "is improving the verification and nutrient scoring machinery",
        "observatory": "is adding monitoring data for the dashboard",
        "genome-bank": "is evolving reusable organism genome traits",
        "app": "is building source code for the prompted application",
    }
    action = action_by_subsystem.get(str(subsystem), "is improving a CodeFarm subsystem")
    status = "verified and promoted" if verified else "quarantined or still unverified"
    target_text = f" targeting {target}" if target else ""
    return f"{organism} {action} for task {task}{target_text}. The output is {status}."


def project_build_summary(improvements: list[dict]) -> dict:
    by_subsystem = {}
    by_organism = {}
    recent = []
    verified_count = 0
    calories = 0
    for item in improvements:
        subsystem = item.get("subsystem") or "unknown"
        organism = item.get("organism") or "unknown"
        verified = bool(item.get("verified"))
        by_subsystem.setdefault(subsystem, {"total": 0, "verified": 0, "calories": 0})
        by_organism.setdefault(organism, {"total": 0, "verified": 0, "calories": 0})
        by_subsystem[subsystem]["total"] += 1
        by_organism[organism]["total"] += 1
        calories += int(item.get("calories", 0) or 0)
        by_subsystem[subsystem]["calories"] += int(item.get("calories", 0) or 0)
        by_organism[organism]["calories"] += int(item.get("calories", 0) or 0)
        if verified:
            verified_count += 1
            by_subsystem[subsystem]["verified"] += 1
            by_organism[organism]["verified"] += 1
    for item in list(reversed(improvements))[:8]:
        manifest = proposal_manifest_for(item)
        recent.append({
            "at": item.get("at"),
            "organism": item.get("organism"),
            "task": item.get("task"),
            "subsystem": item.get("subsystem"),
            "verified": bool(item.get("verified")),
            "calories": item.get("calories", 0),
            "target_path": manifest.get("target_path"),
            "summary": explain_build(item, manifest),
        })
    return {
        "total": len(improvements),
        "verified": verified_count,
        "calories": calories,
        "by_subsystem": by_subsystem,
        "by_organism": by_organism,
        "recent": recent,
    }
def recent_artifacts(state: dict, project_id: str, limit: int = 24) -> list[dict]:
    items = []
    improvements = state.get("infrastructure_improvements", []) if isinstance(state.get("infrastructure_improvements"), list) else []
    for item in reversed(improvements):
        if item.get("project_id") and item.get("project_id") != project_id:
            continue
        for key in ["output_file", "proposal_path"]:
            path = safe_relative(str(item.get(key) or ""))
            if path and path.exists():
                manifest = proposal_manifest_for(item)
                items.append({
                    "kind": "proposal" if key == "proposal_path" else "organism-output",
                    "organism": item.get("organism"),
                    "task": item.get("task"),
                    "subsystem": item.get("subsystem"),
                    "verified": bool(item.get("verified")),
                    "calories": item.get("calories", 0),
                    "at": item.get("at"),
                    "target_path": manifest.get("target_path"),
                    "summary": explain_build(item, manifest),
                    "path": str(path),
                    "relative_path": str(path.relative_to(BASE)),
                    "url": f"/api/file?path={path.relative_to(BASE).as_posix()}",
                })
                break
        if len(items) >= limit:
            break
    if len(items) < limit:
        for output in sorted((BASE / "organisms").glob("org-*/output/*"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True):
            if output.is_file():
                items.append({
                    "kind": "organism-output",
                    "organism": output.parts[-3],
                    "task": "direct-output",
                    "subsystem": output.suffix.lstrip(".") or "artifact",
                    "verified": None,
                    "calories": None,
                    "at": datetime.fromtimestamp(output.stat().st_mtime, timezone.utc).isoformat(),
                    "target_path": None,
                    "summary": f"{output.parts[-3]} produced a direct artifact named {output.name} in its output folder.",
                    "path": str(output),
                    "relative_path": str(output.relative_to(BASE)),
                    "url": f"/api/file?path={output.relative_to(BASE).as_posix()}",
                })
            if len(items) >= limit:
                break
    return items


def export_project_zip(project_id: str) -> tuple[str, bytes]:
    state = read_json(STATE_PATH, {})
    projects, _ = ensure_projects(state)
    if project_id not in projects:
        raise ValueError(f"Unknown project: {project_id}")
    project = projects[project_id]
    app_root = BASE / "projects" / project_id / "app"
    if not app_root.exists() or not app_root.is_dir():
        raise ValueError("Project does not have an app folder to export")
    improvements = active_project_improvements(state, project_id)
    export_manifest = {
        "project": project,
        "exported_at": utc_now(),
        "build_summary": project_build_summary(improvements),
        "app_root": str(app_root.relative_to(BASE)),
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(app_root.rglob("*")):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(app_root).as_posix())
        spec_path = BASE / "projects" / project_id / "project-spec.json"
        if spec_path.exists():
            archive.write(spec_path, "project-spec.json")
        archive.writestr("codefarm-export.json", json.dumps(export_manifest, indent=2, sort_keys=True))
        archive.writestr("BUILD_SUMMARY.md", export_summary_markdown(project, export_manifest["build_summary"]))
    safe_name = slugify(project.get("name", project_id))
    return f"{safe_name}.zip", buffer.getvalue()


def export_summary_markdown(project: dict, summary: dict) -> str:
    lines = [
        f"# {project.get('name', project.get('id', 'Generated App'))}",
        "",
        "## Prompt",
        "",
        project.get("app_prompt", "No prompt recorded."),
        "",
        "## Build Summary",
        "",
        f"- Total improvements: {summary.get('total', 0)}",
        f"- Verified improvements: {summary.get('verified', 0)}",
        f"- Calories earned: {summary.get('calories', 0)}",
        "",
        "## Recent Agent Work",
        "",
    ]
    for item in summary.get("recent", []):
        lines.append(f"- {item.get('summary', 'No summary available')}")
    lines.append("")
    return "\n".join(lines)


def chat_history() -> list[dict]:
    history = read_json(CHAT_PATH, [])
    if not isinstance(history, list):
        return []
    return [item for item in history if isinstance(item, dict)][-80:]


def save_chat_history(history: list[dict]) -> None:
    write_json(CHAT_PATH, history[-80:])


def chat_status_line(snap: dict) -> str:
    project = snap.get("active_project", {}) if isinstance(snap.get("active_project"), dict) else {}
    scheduler_state = "running" if snap.get("scheduler", {}).get("running") else "stopped"
    return (
        f"I am watching {project.get('name', snap.get('active_project_id', 'the active project'))}. "
        f"The autonomous loop is {scheduler_state}, build progress is {snap.get('build_percentage', 0)}%, "
        f"and {snap.get('improvements_verified', 0)} of {snap.get('improvements_total', 0)} improvements are verified."
    )


def chat_agent_line(snap: dict) -> str:
    organisms = snap.get("organisms", []) if isinstance(snap.get("organisms"), list) else []
    active = [org for org in organisms if org.get("status") != "dead"]
    low_energy = [org for org in active if int(org.get("energy", 0)) < 250]
    leaders = sorted(active, key=lambda org: int(org.get("lifetime_nutrients", 0) or 0), reverse=True)[:3]
    leader_text = ", ".join(
        f"{org.get('id')} ({org.get('specialization', 'general')}, energy {org.get('energy', 0)})"
        for org in leaders
    ) or "no active organisms yet"
    warning = f" I am concerned about low energy in {', '.join(org.get('id', 'unknown') for org in low_energy[:4])}." if low_energy else ""
    return f"I have {len(active)} active organisms. Current strongest workers: {leader_text}.{warning}"


def chat_recent_line(snap: dict) -> str:
    recent = snap.get("build_summary", {}).get("recent", []) if isinstance(snap.get("build_summary"), dict) else []
    if not recent:
        return "No recent agent work is recorded for this project yet. Run a cycle and I will have something fresh to inspect."
    lines = [item.get("summary", "An agent produced work.") for item in recent[:3]]
    return "Recent work: " + " ".join(lines)


def chat_anomaly_line(snap: dict) -> str:
    items = snap.get("anomalies", []) if isinstance(snap.get("anomalies"), list) else []
    if not items:
        return "I do not see any anomalies in the current snapshot."
    return "Current signals: " + " ".join(f"{item.get('title')}: {item.get('detail')}" for item in items[:4])


def chat_next_line(snap: dict) -> str:
    if snap.get("build_percentage", 0) >= 100:
        return "Next move: preview the generated app, export it, or raise the target improvements if you want another pass."
    if not snap.get("scheduler", {}).get("running"):
        return "Next move: run one cycle for a controlled check, or start autonomous mode if you want me to keep pushing."
    return "Next move: let the loop continue, then inspect recent work once the next cycle lands."


def code_query_terms(message: str) -> list[str]:
    stopwords = {
        "about", "agent", "answer", "code", "codefarm", "could", "does", "from", "have", "how", "into", "like",
        "that", "the", "this", "what", "when", "where", "which", "with", "would", "your",
    }
    words = re.findall(r"[a-zA-Z0-9_\-/\.]{3,}", message.lower())
    terms = [word.strip("./") for word in words if word not in stopwords]
    aliases = {
        "orchestrator": ["agent_orchestrator.py", "control_server.py", "run_cycle", "promote_or_quarantine"],
        "organism": ["organisms", "agent_metabolism.py", "genome.json", "vitals.json"],
        "metabolism": ["agent_metabolism.py", "choose_task", "execute_task"],
        "proposal": ["proposal", "promote_or_quarantine", "infrastructure_digest.py"],
        "promote": ["promote_or_quarantine", "proposal_paths", "snapshot_target", "move_proposal"],
        "promotion": ["promote_or_quarantine", "proposal_paths", "snapshot_target", "move_proposal"],
        "digest": ["digestive-engine", "infrastructure_digest.py", "digest_infrastructure_output"],
        "verify": ["digest_infrastructure_output", "verified", "quarantine"],
        "chat": ["orchestrator_reply", "append_chat_message", "api/chat", "orchestratorChat"],
        "api": ["control_server.py", "route.ts", "codefarmJson"],
        "ui": ["page.tsx", "globals.css", "observatory"],
        "next": ["product-app", "page.tsx", "route.ts", "codefarm.ts"],
        "state": ["state.json", "snapshot", "build_control", "organisms"],
        "package": ["package-windows.ps1", "package.json", "dist"],
        "terraform": ["core/terraform", "main.tf", "modules/organism"],
        "ansible": ["core/ansible", "site.yml"],
    }
    for key, values in aliases.items():
        if key in message.lower():
            terms.extend(values)
    return list(dict.fromkeys(term for term in terms if term))


def wants_code_context(message: str) -> bool:
    text = message.lower()
    markers = [
        "api", "code", "endpoint", "file", "function", "how does", "how do", "implementation", "orchestrator",
        "route", "source", "where", "why can", "why does",
    ]
    return any(marker in text for marker in markers)


def code_search_candidate(path: Path) -> bool:
    try:
        rel = path.relative_to(BASE)
    except ValueError:
        return False
    if any(part in CODE_SEARCH_EXCLUDED_DIRS for part in rel.parts):
        return False
    if not path.is_file():
        return False
    if path.name in CODE_SEARCH_EXCLUDED_FILES:
        return False
    if path.name not in CODE_SEARCH_NAMES and path.suffix.lower() not in CODE_SEARCH_SUFFIXES:
        return False
    try:
        return path.stat().st_size <= CODE_SEARCH_MAX_FILE_BYTES
    except OSError:
        return False


def read_source_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def iter_code_paths() -> list[Path]:
    explicit = [
        "README.md",
        "product.json",
        "agent_orchestrator.py",
        "control_server.py",
        "codefarm_common.py",
        "orchestrator.py",
        "overmind.py",
        "organisms/agent_metabolism.py",
        "organisms/commercial_metabolism.py",
        "organisms/metabolism_template.py",
        "genome-bank/base-genome.json",
        "tasks/task-types.json",
    ]
    roots = [
        "core",
        "data-center/ansible",
        "data-center/terraform",
        "digestive-engine",
        "immune-system",
        "observatory",
        "product-app/app",
        "product-app/lib",
        "product-app/scripts",
        "product-app/package.json",
        "website",
    ]
    paths = []
    for rel in explicit:
        path = BASE / rel
        if path.exists():
            paths.append(path)
    for rel in roots:
        root = BASE / rel
        if root.is_file():
            paths.append(root)
            continue
        if not root.exists():
            continue
        for current_root, dirs, files in os.walk(root):
            dirs[:] = [name for name in dirs if name not in CODE_SEARCH_EXCLUDED_DIRS]
            for filename in files:
                paths.append(Path(current_root) / filename)
    return list(dict.fromkeys(paths))


def line_snippet(text: str, terms: list[str], radius: int = 2) -> tuple[int, str]:
    lines = text.splitlines()
    lowered_terms = [term.lower() for term in terms if len(term) > 2]
    match_index = 0
    best_score = 0
    for index, line in enumerate(lines):
        lower = line.lower()
        score = sum(4 if "_" in term and term in lower else 1 for term in lowered_terms if term in lower)
        if score > best_score:
            best_score = score
            match_index = index
    start = max(0, match_index - radius)
    end = min(len(lines), match_index + radius + 1)
    snippet = "\n".join(f"{number + 1}: {lines[number][:180]}" for number in range(start, end))
    return start + 1, snippet


def source_role(path: str) -> str:
    roles = {
        "agent_orchestrator.py": "Runs organism cycles, verifies proposals, promotes or quarantines changes, updates energy/state, and breeds successful organisms.",
        "control_server.py": "Exposes the local HTTP API, project controls, scheduler, snapshots, exports, and orchestrator chat.",
        "organisms/agent_metabolism.py": "Defines how an organism chooses tasks and writes proposal payloads for infrastructure or app files.",
        "digestive-engine/infrastructure_digest.py": "Validates proposal artifacts and computes verification status, calories, and bonuses.",
        "product-app/app/page.tsx": "Renders the Next.js product UI, including project controls, status cards, agent list, and chat panel.",
        "product-app/lib/codefarm.ts": "Starts or contacts the local CodeFarm service and proxies browser-safe API calls.",
    }
    normalized = path.replace("\\", "/")
    for suffix, role in roles.items():
        if normalized.endswith(suffix):
            return role
    if normalized.endswith("route.ts"):
        return "Next.js API route that proxies a browser request to the local CodeFarm control server."
    if normalized.endswith("globals.css"):
        return "Global styling for the product UI."
    if normalized.endswith(".json"):
        return "Structured configuration or runtime metadata."
    return "Relevant source artifact."


def search_codebase(message: str, limit: int = 5) -> list[dict]:
    terms = code_query_terms(message)
    if not terms:
        return []
    results = []
    for path in iter_code_paths():
        if not code_search_candidate(path):
            continue
        rel = path.relative_to(BASE).as_posix()
        rel_lower = rel.lower()
        try:
            text = read_source_text(path)
        except OSError:
            continue
        lower = text.lower()
        score = 0
        for term in terms:
            term_lower = term.lower()
            if term_lower in rel_lower:
                score += 12
            score += min(lower.count(term_lower), 8)
        if score <= 0:
            continue
        line, snippet = line_snippet(text, terms)
        results.append({
            "path": rel,
            "line": line,
            "score": score,
            "role": source_role(rel),
            "snippet": snippet,
        })
    results.sort(key=lambda item: (-item["score"], item["path"]))
    return results[:limit]


def chat_code_line(message: str) -> tuple[str, list[dict]]:
    sources = search_codebase(message)
    if not sources:
        return (
            "I checked the source index, but I did not find a tight code match. Ask me with a file, function, or subsystem name and I can narrow the search.",
            [],
        )
    lead = "I can answer from the CodeFarm source now. The strongest matches are:"
    bullets = []
    for source in sources:
        bullets.append(f"- {source['path']}:{source['line']} - {source['role']}")
    snippets = ["Relevant snippets:"]
    for source in sources[:3]:
        snippets.append(f"{source['path']}:{source['line']}\n{source['snippet']}")
    return "\n".join([lead, *bullets, "", *snippets]), sources


def orchestrator_reply(message: str) -> dict:
    snap = snapshot()
    text = message.lower()
    parts = []
    sources = []
    if wants_code_context(message):
        code_line, sources = chat_code_line(message)
        parts.append(code_line)
    if any(word in text for word in ["agent", "organism", "worker", "energy"]):
        parts.append(chat_agent_line(snap))
    if any(word in text for word in ["recent", "done", "built", "work", "change", "proposal"]):
        parts.append(chat_recent_line(snap))
    if any(word in text for word in ["problem", "anomaly", "risk", "stuck", "wrong", "fail", "quarantine"]):
        parts.append(chat_anomaly_line(snap))
    if any(word in text for word in ["next", "should", "recommend", "plan", "do"]):
        parts.append(chat_next_line(snap))
    if any(word in text for word in ["status", "progress", "how", "hello", "hi"]) or not parts:
        parts.insert(0, chat_status_line(snap))
    if len(parts) == 1 and "?" not in message:
        parts.append(chat_next_line(snap))
    return {
        "role": "orchestrator",
        "content": "\n\n".join(dict.fromkeys(parts)),
        "at": utc_now(),
        "snapshot": {
            "active_project_id": snap.get("active_project_id"),
            "build_percentage": snap.get("build_percentage", 0),
            "improvements_verified": snap.get("improvements_verified", 0),
            "improvements_total": snap.get("improvements_total", 0),
            "scheduler_running": snap.get("scheduler", {}).get("running", False),
        },
        "sources": sources,
    }


def chat_snapshot() -> dict:
    return {"messages": chat_history(), "snapshot": snapshot()}


def append_chat_message(payload: dict) -> dict:
    content = str(payload.get("message") or payload.get("content") or "").strip()
    if not content:
        raise ValueError("Message is required")
    content = content[:2000]
    history = chat_history()
    user_message = {"role": "user", "content": content, "at": utc_now()}
    assistant_message = orchestrator_reply(content)
    history.extend([user_message, assistant_message])
    save_chat_history(history)
    return {"ok": True, "messages": history[-80:], "reply": assistant_message}


def snapshot() -> dict:
    state = read_json(STATE_PATH, {})
    projects, project = ensure_projects(state)
    control = sync_control_from_project(state, project)
    orgs = organism_rows(state)
    counts = proposal_counts()
    improvements = active_project_improvements(state, project["id"])
    verified = len([item for item in improvements if item.get("verified")])
    target = max(1, int(control.get("target_improvements", 50)))
    build_pct = min(100.0, verified / target * 100)
    project_list = sorted(projects.values(), key=lambda item: item.get("created_at", ""))
    return {
        "state_version": state.get("version"),
        "cycle": state.get("cycle", 0),
        "active_project_id": project["id"],
        "active_project": project,
        "app_url": f"/apps/{project['id']}/index.html" if project.get("project_type") == "app" else None,
        "export_url": f"/api/export?project_id={project['id']}" if project.get("project_type") == "app" else None,
        "projects": project_list,
        "control": control,
        "scheduler": {k: v for k, v in scheduler.items() if k not in {"thread", "stop"}},
        "reset_supported": True,
        "organisms": orgs,
        "proposal_counts": counts,
        "pool": state.get("nutrient_pool", {}),
        "improvements_total": len(improvements),
        "improvements_verified": verified,
        "build_percentage": round(build_pct, 2),
        "build_summary": project_build_summary(improvements),
        "anomalies": anomalies(state, orgs, counts, build_pct),
        "artifacts": recent_artifacts(state, project["id"]),
    }


class Handler(BaseHTTPRequestHandler):
    def send_json(self, payload, status=200):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/state":
            self.send_json(snapshot())
            return
        if path == "/api/chat":
            self.send_json(chat_snapshot())
            return
        if path.startswith("/apps/"):
            parts = path.strip("/").split("/", 2)
            if len(parts) < 3:
                self.send_error(404)
                return
            project_id = slugify(parts[1])
            rel = parts[2] or "index.html"
            file_path = safe_relative(f"projects/{project_id}/app/{rel}")
            if not file_path or not file_path.exists() or file_path.is_dir():
                self.send_error(404)
                return
            content = file_path.read_bytes()
            suffix = file_path.suffix.lower()
            content_type = "text/html" if suffix == ".html" else "text/css" if suffix == ".css" else "application/javascript" if suffix == ".js" else "text/plain"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return
        if path == "/api/export":
            params = parse_qs(parsed.query)
            project_id = params.get("project_id", [read_json(STATE_PATH, {}).get("active_project_id", "")])[0]
            try:
                filename, content = export_project_zip(slugify(project_id))
            except Exception as exc:
                self.send_json({"ok": False, "error": str(exc)}, 400)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", f"attachment; filename=\"{filename}\"")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return
        if path == "/api/file":
            params = parse_qs(parsed.query)
            file_path = safe_relative(params.get("path", [""])[0])
            if not file_path or not file_path.exists() or file_path.is_dir():
                self.send_error(404)
                return
            content = file_path.read_text(encoding="utf-8", errors="replace")
            body = content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/":
            path = "/index.html"
        file_path = (CONTROL_DIR / path.lstrip("/")).resolve()
        if CONTROL_DIR.resolve() not in file_path.parents and file_path != CONTROL_DIR.resolve():
            self.send_error(403)
            return
        if not file_path.exists() or file_path.is_dir():
            self.send_error(404)
            return
        content = file_path.read_bytes()
        content_type = "text/html" if file_path.suffix == ".html" else "text/css" if file_path.suffix == ".css" else "application/javascript"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            if path == "/api/config":
                self.send_json({"control": save_control(self.read_body())})
            elif path == "/api/project":
                self.send_json(create_project(self.read_body()))
            elif path in {"/api/reset-project", "/api/reset"}:
                self.send_json(reset_project(self.read_body()))
            elif path == "/api/select-project":
                body = self.read_body()
                self.send_json({"control": select_project(str(body.get("project_id", "")))})
            elif path == "/api/start":
                start_scheduler()
                self.send_json({"ok": True, "scheduler": snapshot()["scheduler"]})
            elif path == "/api/stop":
                stop_scheduler()
                self.send_json({"ok": True, "scheduler": snapshot()["scheduler"]})
            elif path == "/api/run-once":
                code, output = run_cycle()
                self.send_json({"ok": code == 0, "output": output[-5000:], "snapshot": snapshot()}, 200 if code == 0 else 500)
            elif path == "/api/chat":
                self.send_json(append_chat_message(self.read_body()))
            else:
                self.send_error(404)
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, 500)

    def log_message(self, format, *args):
        return


def main() -> int:
    save_control({})
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"CodeFarm Build Control: http://{HOST}:{PORT}/")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
