import { useCallback, useEffect, useState } from "react";
import { api, hasToken, setToken, setUnauthorizedHandler } from "./api.js";
import Login from "./components/Login.jsx";
import Ask from "./views/Ask.jsx";
import Documents from "./views/Documents.jsx";
import History from "./views/History.jsx";
import System from "./views/System.jsx";

const NAV = [
  { id: "ask", label: "Ask" },
  { id: "documents", label: "Documents" },
  { id: "history", label: "History" },
  { id: "system", label: "System" },
];

function useBackendStatus(active) {
  const [state, setState] = useState("checking");
  useEffect(() => {
    if (!active) return undefined;
    let stopped = false;
    const check = () =>
      api.health()
        .then((h) => !stopped && setState(h.ollama === "up" ? "online" : "ollama-down"))
        .catch(() => !stopped && setState("offline"));
    check();
    const t = setInterval(check, 20000);
    return () => { stopped = true; clearInterval(t); };
  }, [active]);
  return state;
}

const STATUS_TEXT = {
  checking: ["off", "Checking…"],
  online: ["ok", "Ollama running"],
  "ollama-down": ["warn", "Ollama not running"],
  offline: ["bad", "Backend offline"],
};

export default function App() {
  const [authed, setAuthed] = useState(hasToken());
  const [user, setUser] = useState("");
  const [view, setView] = useState("ask");
  const [notice, setNotice] = useState("");
  const status = useBackendStatus(authed);

  const signOut = useCallback((message = "") => {
    setToken(null);
    sessionStorage.removeItem("enclave_thread");
    setAuthed(false);
    setUser("");
    setView("ask");
    setNotice(message);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => signOut("Your session ended. Please sign in again."));
  }, [signOut]);

  useEffect(() => {
    if (authed) api.me().then((u) => setUser(u.username)).catch(() => {});
  }, [authed]);

  if (!authed) {
    return <Login notice={notice} onLogin={() => { setNotice(""); setAuthed(true); }} />;
  }

  const [dot, statusText] = STATUS_TEXT[status];
  return (
    <div className="app">
      <nav className="rail" aria-label="Main">
        <p className="wordmark">Enclave AI</p>
        <ul className="nav-list">
          {NAV.map((n) => (
            <li key={n.id}>
              <button type="button" className="nav-button" aria-current={view === n.id ? "page" : undefined} onClick={() => setView(n.id)}>
                {n.label}
              </button>
            </li>
          ))}
        </ul>
        <div className="rail-foot">
          <p className="rail-status" role="status">
            <span className={`dot dot-${dot}`} aria-hidden="true" />
            {statusText}
          </p>
          <p className="rail-user">{user ? `Signed in as ${user}` : ""}</p>
          <button type="button" className="rail-signout" onClick={() => signOut("")}>Sign out</button>
        </div>
      </nav>
      <main className="main">
        <Ask visible={view === "ask"} onGoDocuments={() => setView("documents")} />
        <Documents visible={view === "documents"} />
        <History visible={view === "history"} />
        <System visible={view === "system"} />
      </main>
    </div>
  );
}
