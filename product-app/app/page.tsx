"use client";

import { useEffect, useMemo, useState } from "react";

type AgentState = {
  id: string;
  status: string;
  energy: number;
  specialization: string;
  last_task?: string;
  last_promotion?: string;
};

type CodeFarmState = {
  active_project_id?: string;
  active_project?: { name?: string; project_type?: string };
  app_url?: string | null;
  export_url?: string | null;
  build_percentage?: number;
  improvements_verified?: number;
  improvements_total?: number;
  scheduler?: { running?: boolean };
  organisms?: AgentState[];
  build_summary?: { recent?: Array<{ summary: string; calories: number; verified: boolean }> };
};

type ChatMessage = {
  role: "user" | "orchestrator";
  content: string;
  at?: string;
  sources?: Array<{ path: string; line: number; role?: string }>;
};

const defaultPrompt = "Build a local customer intake dashboard with a workboard, progress metrics, anomaly notes, and an export-ready README.";

async function jsonFetch(path: string, init?: RequestInit) {
  const res = await fetch(path, init);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

export default function Home() {
  const [name, setName] = useState("Customer Intake Dashboard");
  const [prompt, setPrompt] = useState(defaultPrompt);
  const [mode, setMode] = useState("autonomous");
  const [status, setStatus] = useState("Ready to start a sandboxed local build.");
  const [state, setState] = useState<CodeFarmState | null>(null);
  const [busy, setBusy] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("What is the current build status?");
  const [chatBusy, setChatBusy] = useState(false);

  const assigned = useMemo(() => ["org-001", "org-002", "org-003", "org-004"], []);

  async function refresh() {
    try {
      const data = await jsonFetch("/api/codefarm/state");
      setState(data);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Agent service is not ready.");
    }
  }

  async function refreshChat() {
    try {
      const data = await jsonFetch("/api/codefarm/chat");
      setChatMessages(data.messages || []);
    } catch {
      setChatMessages([]);
    }
  }

  useEffect(() => {
    refresh();
    refreshChat();
    const timer = setInterval(refresh, 3000);
    return () => clearInterval(timer);
  }, []);

  async function sendChat() {
    const message = chatInput.trim();
    if (!message) return;
    setChatBusy(true);
    setChatInput("");
    setChatMessages((items) => [...items, { role: "user", content: message }]);
    try {
      const data = await jsonFetch("/api/codefarm/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message })
      });
      setChatMessages(data.messages || []);
      await refresh();
    } catch (err) {
      setChatMessages((items) => [
        ...items,
        { role: "orchestrator", content: err instanceof Error ? err.message : "I could not reach the orchestrator service." }
      ]);
    } finally {
      setChatBusy(false);
    }
  }

  async function startProject(runMode: "once" | "auto") {
    setBusy(true);
    setStatus("Creating sandboxed app project...");
    try {
      await jsonFetch("/api/codefarm/project", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          app_prompt: prompt,
          assigned_orgs: assigned,
          build_rate_mode: mode,
          build_rate_seconds: mode === "autonomous" ? 0 : 60,
          target_improvements: 4
        })
      });
      setStatus(runMode === "auto" ? "Starting autonomous agents..." : "Running one build cycle...");
      await jsonFetch(runMode === "auto" ? "/api/codefarm/start" : "/api/codefarm/run-once", { method: "POST" });
      setStatus(runMode === "auto" ? "Autonomous agents are building in the background." : "Build cycle finished.");
      await refresh();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Unable to start build.");
    } finally {
      setBusy(false);
    }
  }

  async function stopAgents() {
    setBusy(true);
    try {
      await jsonFetch("/api/codefarm/stop", { method: "POST" });
      setStatus("Autonomous agents stopped.");
      await refresh();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Unable to stop agents.");
    } finally {
      setBusy(false);
    }
  }

  async function terminateAndStartOver() {
    setBusy(true);
    setStatus("Terminating current build and clearing the project sandbox...");
    try {
      await jsonFetch("/api/codefarm/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: state?.active_project_id,
          recreate: true,
          project: {
            name,
            app_prompt: prompt,
            assigned_orgs: assigned,
            build_rate_mode: mode,
            build_rate_seconds: mode === "autonomous" ? 0 : 60,
            target_improvements: 4
          }
        })
      });
      setStatus(mode === "autonomous" ? "Fresh project created. Restarting autonomous agents..." : "Fresh project created. Running a clean build cycle...");
      await jsonFetch(mode === "autonomous" ? "/api/codefarm/start" : "/api/codefarm/run-once", { method: "POST" });
      setStatus(mode === "autonomous" ? "Build restarted from a clean sandbox." : "Clean build cycle finished.");
      await refresh();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Unable to reset build.");
    } finally {
      setBusy(false);
    }
  }

  const appPreview = state?.app_url ? `http://127.0.0.1:8765${state.app_url}` : "#";
  const exportUrl = state?.export_url ? `/api/codefarm/export?project_id=${state.active_project_id}` : "#";

  return (
    <main className="shell">
      <section className="hero">
        <div className="heroCopy">
          <p className="eyebrow">Standalone local app factory</p>
          <h1>Deploy local autonomous agents that live to build</h1>
          <p className="lede">Describe the app. The local agent runtime builds a sandboxed project in the background, verifies generated files, and lets you preview or download the result.</p>
        </div>
        <form className="promptPanel" onSubmit={(event) => { event.preventDefault(); startProject("auto"); }}>
          <label>
            <span>Project name</span>
            <input value={name} onChange={(event) => setName(event.target.value)} />
          </label>
          <label>
            <span>Input prompt</span>
            <textarea rows={7} value={prompt} onChange={(event) => setPrompt(event.target.value)} />
          </label>
          <label>
            <span>Build rate</span>
            <select value={mode} onChange={(event) => setMode(event.target.value)}>
              <option value="autonomous">Autonomous - build again immediately</option>
              <option value="timed">Timed - one minute cadence</option>
            </select>
          </label>
          <div className="actions">
            <button disabled={busy} type="submit">Start Autonomous Build</button>
            <button disabled={busy} type="button" onClick={() => startProject("once")}>Run Once</button>
            <button disabled={busy} type="button" onClick={stopAgents}>Stop</button>
            <button className="danger" disabled={busy || !state?.active_project_id} type="button" onClick={terminateAndStartOver}>Terminate & Start Over</button>
          </div>
          <p className="status">{status}</p>
        </form>
      </section>

      <section className="dashboard">
        <article>
          <span>Build</span>
          <strong>{state?.build_percentage ?? 0}%</strong>
          <p>{state?.improvements_verified ?? 0} verified / {state?.improvements_total ?? 0} total</p>
        </article>
        <article>
          <span>Agents</span>
          <strong>{state?.organisms?.filter((org) => org.status !== "dead").length ?? 0}</strong>
          <p>{state?.scheduler?.running ? "Autonomous loop running" : "Loop stopped"}</p>
        </article>
        <article>
          <span>Output</span>
          <strong>{state?.active_project?.name || "No project"}</strong>
          <p>Sandbox: CodeFarm project app folder</p>
        </article>
      </section>

      <section className="projectActions">
        <a className={state?.app_url ? "" : "disabled"} href={appPreview} target="_blank">Preview generated app</a>
        <a className={state?.export_url ? "" : "disabled"} href={exportUrl}>Download app ZIP</a>
      </section>

      <section className="orchestratorChat" aria-label="Orchestrator chat">
        <div className="chatHeader">
          <div>
            <span>Orchestrator</span>
            <h2>Talk to the build brain</h2>
          </div>
          <button disabled={chatBusy} type="button" onClick={refreshChat}>Refresh</button>
        </div>
        <div className="chatLog">
          {chatMessages.length === 0 ? (
            <article className="chatBubble orchestrator">
              <strong>orchestrator</strong>
              <p>I am online. Ask me about status, agents, recent work, anomalies, or what to do next.</p>
            </article>
          ) : chatMessages.map((message, index) => (
            <article className={`chatBubble ${message.role}`} key={`${message.role}-${message.at || index}`}>
              <strong>{message.role === "user" ? "you" : "orchestrator"}</strong>
              <p>{message.content}</p>
              {message.sources?.length ? (
                <div className="chatSources">
                  {message.sources.slice(0, 5).map((source) => (
                    <span key={`${source.path}-${source.line}`}>{source.path}:{source.line}</span>
                  ))}
                </div>
              ) : null}
            </article>
          ))}
        </div>
        <form className="chatComposer" onSubmit={(event) => { event.preventDefault(); sendChat(); }}>
          <input
            aria-label="Message the orchestrator"
            value={chatInput}
            onChange={(event) => setChatInput(event.target.value)}
            placeholder="Ask about status, agents, risks, or next steps"
          />
          <button disabled={chatBusy || !chatInput.trim()} type="submit">Send</button>
        </form>
      </section>

      <section className="agents">
        {(state?.organisms || []).slice(0, 8).map((org) => (
          <article key={org.id}>
            <h2>{org.id}</h2>
            <p>{org.specialization} / {org.status}</p>
            <div className="bar"><span style={{ width: `${Math.min(100, Math.max(4, org.energy / 100))}%` }} /></div>
            <small>Last task: {org.last_task || "none"}</small>
          </article>
        ))}
      </section>

      <section className="summary">
        <h2>Recent agent work</h2>
        {(state?.build_summary?.recent || []).slice(0, 5).map((item, index) => (
          <p key={index}>{item.summary}</p>
        ))}
      </section>
    </main>
  );
}
