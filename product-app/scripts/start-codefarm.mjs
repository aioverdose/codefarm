import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
const root = process.env.CODEFARM_HOME || path.resolve("..", "runtime", "codefarm");
const api = process.env.CODEFARM_API_URL || "http://127.0.0.1:8765";
async function isLive() { try { const res = await fetch(`${api}/api/state`); return res.ok; } catch { return false; } }
if (await isLive()) { console.log(`Agent service already running at ${api}`); process.exit(0); }
if (!existsSync(path.join(root, "control_server.py"))) { console.error(`Invalid agent runtime root: ${root}`); process.exit(1); }
const child = spawn("python", [path.join(root, "control_server.py")], { cwd: root, detached: true, stdio: "ignore", windowsHide: true, env: { ...process.env, CODEFARM_HOME: root } });
child.unref();
console.log(`Started local agent service at ${api}`);