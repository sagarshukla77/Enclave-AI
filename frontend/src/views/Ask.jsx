import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { formatSeconds, normalizeSources, normalizeTools } from "../format.js";
import RichAnswer from "../components/RichAnswer.jsx";
import Verdict from "../components/Verdict.jsx";
import EvidenceList from "../components/EvidenceList.jsx";
import HowAnswered from "../components/HowAnswered.jsx";
import ReportButtons from "../components/ReportButtons.jsx";

const STORE_KEY = "enclave_thread";
const EXAMPLES = [
  "The measured impeller wear is 4.2 mm. Does it pass or fail the SOP limit, and what action is required?",
  "What is the maximum permitted shaft vibration?",
  "At what bearing temperature must the bearings be replaced?",
];

function loadSaved() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(STORE_KEY) || "[]");
    return Array.isArray(saved) ? saved : [];
  } catch {
    return [];
  }
}

function Thinking({ startedAt }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const seconds = Math.floor((now - startedAt) / 1000);
  return (
    <div className="thinking" role="status" aria-live="polite">
      <span className="thinking-dot" aria-hidden="true" />
      <span>
        Reading your documents… {seconds} s
        {seconds >= 20 && <span className="thinking-hint"> The first answer can take a minute while the model loads.</span>}
      </span>
    </div>
  );
}

export default function Ask({ visible, onGoDocuments }) {
  const [messages, setMessages] = useState(loadSaved);
  const [activeId, setActiveId] = useState(() => {
    const saved = loadSaved();
    return saved.length ? saved[saved.length - 1].id : null;
  });
  const [activeCite, setActiveCite] = useState(null);
  const [input, setInput] = useState("");
  const [models, setModels] = useState(null);
  const [model, setModel] = useState("");
  const [docCount, setDocCount] = useState(null);
  const endRef = useRef(null);
  const inputRef = useRef(null);

  const busy = messages.some((m) => m.status === "pending");
  const active = messages.find((m) => m.id === activeId);
  const activeSources = active && active.result ? normalizeSources(active.result.sources) : [];

  useEffect(() => {
    api.models().then((m) => { setModels(m.models); setModel(m.default); }).catch(() => {});
  }, []);

  useEffect(() => {
    if (visible) api.documents().then((d) => setDocCount(d.documents.length)).catch(() => {});
  }, [visible]);

  useEffect(() => {
    const keep = messages.filter((m) => m.status !== "pending");
    try { sessionStorage.setItem(STORE_KEY, JSON.stringify(keep.slice(-30))); } catch { /* storage full */ }
  }, [messages]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length]);

  async function send(question) {
    const q = question.trim();
    if (!q || busy) return;
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    setMessages((prev) => [...prev, { id, question: q, status: "pending", startedAt: Date.now() }]);
    setActiveId(id);
    setActiveCite(null);
    setInput("");
    try {
      const result = await api.chat(q, model);
      setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, status: "done", result } : m)));
    } catch (e) {
      setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, status: "error", error: e.message } : m)));
    }
  }

  function selectCite(messageId, label) {
    setActiveId(messageId);
    setActiveCite(label);
    requestAnimationFrame(() => {
      document.getElementById(`slip-${label}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  }

  function clearThread() {
    setMessages([]);
    setActiveId(null);
    setActiveCite(null);
    sessionStorage.removeItem(STORE_KEY);
  }

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  }

  return (
    <section className="view ask" hidden={!visible} aria-labelledby="ask-title">
      <div className="ask-thread">
        <header className="page-head">
          <div>
            <h1 id="ask-title">Ask your documents</h1>
            <p className="lede">Answers come only from files you have added, with the file and page cited. Nothing leaves this computer.</p>
          </div>
          <div className="head-tools">
            {models && models.length > 0 && (
              <label className="inline-field">
                <span>Model</span>
                <select value={model} onChange={(e) => setModel(e.target.value)} disabled={busy}>
                  {models.map((m) => (
                    <option key={m.name} value={m.name} disabled={!m.installed}>
                      {m.name}{m.installed ? "" : " (not installed)"}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {messages.length > 0 && (
              <button type="button" className="btn quiet" onClick={clearThread} disabled={busy}>Clear thread</button>
            )}
          </div>
        </header>

        {docCount === 0 && (
          <div className="notice" role="note">
            You have not added any documents yet, so there is nothing to search.{" "}
            <button type="button" className="link-button" onClick={onGoDocuments}>Add documents</button>
          </div>
        )}

        {messages.length === 0 && (
          <div className="sheet empty-ask">
            <h2>What would you like to check?</h2>
            <p>Try a question like one of these, or write your own below.</p>
            <ul className="examples">
              {EXAMPLES.map((ex) => (
                <li key={ex}>
                  <button type="button" onClick={() => { setInput(ex); inputRef.current?.focus(); }}>{ex}</button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {messages.map((m) => {
          const sources = m.result ? normalizeSources(m.result.sources) : [];
          const isActive = m.id === activeId;
          return (
            <article key={m.id} className={"sheet turn" + (isActive ? " is-active" : "")}>
              <h2 className="question">{m.question}</h2>

              {m.status === "pending" && <Thinking startedAt={m.startedAt} />}

              {m.status === "error" && (
                <p className="error-note" role="alert">{m.error}</p>
              )}

              {m.status === "done" && (
                <>
                  <RichAnswer
                    text={m.result.answer}
                    sources={sources}
                    activeLabel={isActive ? activeCite : null}
                    onCite={(label) => selectCite(m.id, label)}
                  />
                  <Verdict answer={m.result.answer} validation={m.result.validation} />
                  {m.result.model_warning && <p className="soft-note">{m.result.model_warning}</p>}
                  <p className="turn-meta">
                    {m.result.model}
                    {m.result.duration_seconds !== undefined ? `, answered in ${formatSeconds(m.result.duration_seconds)}` : ""}
                  </p>
                  <HowAnswered tools={normalizeTools(m.result.tools_used)} trace={m.result.trace} />
                  <div className="turn-actions">
                    {m.result.audit_id && <ReportButtons auditId={m.result.audit_id} />}
                    {!isActive && sources.length > 0 && (
                      <button type="button" className="btn quiet" onClick={() => { setActiveId(m.id); setActiveCite(null); }}>
                        Show its sources
                      </button>
                    )}
                  </div>
                </>
              )}
            </article>
          );
        })}
        <div ref={endRef} />

        <div className="composer sheet">
          <label htmlFor="question-input" className="visually-hidden">Your question</label>
          <textarea
            id="question-input"
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask a question about your documents"
            rows={2}
            maxLength={2000}
          />
          <div className="composer-row">
            <span className="hint">Enter to send, Shift+Enter for a new line</span>
            <button type="button" className="btn primary" onClick={() => send(input)} disabled={busy || input.trim().length < 3}>
              {busy ? "Working…" : "Ask"}
            </button>
          </div>
        </div>
      </div>

      <aside className="ask-evidence" aria-label="Sources for the selected answer">
        <h2>Sources</h2>
        {!active && <p className="soft-note">The passages behind an answer appear here. Select a number in an answer to jump to its source.</p>}
        {active && active.status === "pending" && <p className="soft-note">Waiting for the answer…</p>}
        {active && active.status === "error" && <p className="soft-note">This question did not get an answer.</p>}
        {active && active.status === "done" && activeSources.length === 0 && (
          <p className="soft-note">No sources were used. When the answer is not in your documents, the workbench says so instead of guessing.</p>
        )}
        {activeSources.length > 0 && (
          <EvidenceList sources={activeSources} activeLabel={activeCite} onSelect={(label) => selectCite(active.id, label)} idPrefix="slip" />
        )}
      </aside>
    </section>
  );
}
