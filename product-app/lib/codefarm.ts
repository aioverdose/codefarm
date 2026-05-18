import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";

const DEFAULT_ROOT = "G:\\codefarm";
const DEFAULT_API = "http://127.0.0.1:8765";
let startAttempted = false;

export const codefarmRoot = process.env.CODEFARM_HOME || DEFAULT_ROOT;
export const codefarmApi = process.env.CODEFARM_API_URL || DEFAULT_API;

function assertLocalCodeFarmRoot() {
  const resolved = path.resolve(codefarmRoot);
  if (!existsSync(path.join(resolved, "control_server.py"))) {
    throw new Error(`CodeFarm root is not valid: ${resolved}`);
  }
  return resolved;
}

export async function ensureCodeFarm() {
  try {
    const res = await fetch(`${codefarmApi}/api/state`, { cache: "no-store" });
    if (res.ok) return;
  } catch {}

  if (!startAttempted) {
    startAttempted = true;
    const root = assertLocalCodeFarmRoot();
    const child = spawn("python", [path.join(root, "control_server.py")], {
      cwd: root,
      detached: true,
      stdio: "ignore",
      windowsHide: true,
      env: { ...process.env, CODEFARM_HOME: root }
    });
    child.unref();
  }

  const startedAt = Date.now();
  while (Date.now() - startedAt < 7000) {
    await new Promise((resolve) => setTimeout(resolve, 250));
    try {
      const res = await fetch(`${codefarmApi}/api/state`, { cache: "no-store" });
      if (res.ok) return;
    } catch {}
  }
  throw new Error("Local autonomous agent service did not become ready.");
}

export async function codefarmJson(pathname: string, init?: RequestInit) {
  await ensureCodeFarm();
  const res = await fetch(`${codefarmApi}${pathname}`, {
    ...init,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) }
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : {};
  if (!res.ok) throw new Error(data.error || `Agent service request failed: ${res.status}`);
  return data;
}

export async function codefarmBinary(pathname: string) {
  await ensureCodeFarm();
  const res = await fetch(`${codefarmApi}${pathname}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Export request failed: ${res.status}`);
  return res;
}

export function projectPayload(input: unknown) {
  const body = (input && typeof input === "object" ? input : {}) as Record<string, unknown>;
  const name = String(body.name || "New Local App").slice(0, 120);
  const prompt = String(body.app_prompt || "").slice(0, 8000);
  const mode = body.build_rate_mode === "autonomous" ? "autonomous" : "timed";
  const seconds = mode === "autonomous" ? 0 : Math.max(5, Math.min(86400, Number(body.build_rate_seconds || 60)));
  const assigned = Array.isArray(body.assigned_orgs)
    ? body.assigned_orgs.map(String).filter((id) => /^org-\d{3}$/.test(id)).slice(0, 12)
    : ["org-001", "org-002", "org-003", "org-004"];

  return {
    name,
    app_prompt: prompt,
    project_type: "app",
    directions: `Build this app from the project prompt: ${prompt}`.slice(0, 4000),
    assigned_orgs: assigned,
    build_rate_mode: mode,
    build_rate_seconds: seconds,
    target_improvements: Math.max(1, Math.min(200, Number(body.target_improvements || 4)))
  };
}

export const exposedFunctionCatalog = [
  { name: "createProject", path: "/api/codefarm/project", visibility: "hidden-api", note: "Creates a sandboxed local app project." },
  { name: "runOnce", path: "/api/codefarm/run-once", visibility: "hidden-api", note: "Runs one build cycle." },
  { name: "startAutonomous", path: "/api/codefarm/start", visibility: "hidden-api", note: "Starts background build cycles." },
  { name: "stopAutonomous", path: "/api/codefarm/stop", visibility: "hidden-api", note: "Stops background build cycles." },
  { name: "resetProject", path: "/api/codefarm/reset", visibility: "hidden-api", note: "Terminates the active build, clears its sandbox, and recreates it from the prompt." },
  { name: "chatWithOrchestrator", path: "/api/codefarm/chat", visibility: "visible-ui", note: "Talks to the local orchestrator using current build state and chat history." },
  { name: "exportZip", path: "/api/codefarm/export", visibility: "hidden-api", note: "Downloads the generated app ZIP." }
];
