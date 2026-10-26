import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";

function Row({ name, state, label, detail, fix }) {
  return (
    <li className="status-row">
      <div className="status-name">
        <strong>{name}</strong>
        {detail && <span>{detail}</span>}
      </div>
      <div className="status-state">
        <span className={`dot dot-${state}`} aria-hidden="true" />
        <span>{label}</span>
      </div>
      {fix && <p className="status-fix">{fix}</p>}
    </li>
  );
}

export default function System({ visible }) {
  const [status, setStatus] = useState(null);
  const [models, setModels] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    Promise.all([api.modelStatus(), api.models()])
      .then(([s, m]) => { setStatus(s); setModels(m); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { if (visible) load(); }, [visible, load]);

  const s = status;
  return (
    <section className="view" hidden={!visible} aria-labelledby="system-title">
      <header className="page-head">
        <div>
          <h1 id="system-title">System</h1>
          <p className="lede">Everything the workbench needs to answer questions, and what to do if something is missing.</p>
        </div>
        <div className="head-tools">
          <button type="button" className="btn quiet" onClick={load} disabled={loading}>{loading ? "Checking…" : "Check again"}</button>
        </div>
      </header>

      {error && <p className="error-note" role="alert">{error}</p>}
      {!s && !error && <p className="soft-note">Checking…</p>}

      {s && (
        <ul className="status-list sheet">
          <Row name="Ollama" state={s.ollama_up ? "ok" : "bad"} label={s.ollama_up ? "Running" : "Not running"}
               detail="Runs the language models on this computer"
               fix={s.ollama_up ? null : "Open the Ollama app, or run: ollama serve"} />
          <Row name="Answer model" detail={s.llm.name} state={s.llm.installed ? "ok" : "bad"}
               label={s.llm.installed ? "Ready" : "Not installed"}
               fix={s.llm.installed ? null : `Run: ollama pull ${s.llm.name}`} />
          <Row name="Search model" detail={s.embedding.name} state={s.embedding.installed ? "ok" : "bad"}
               label={s.embedding.installed ? "Ready" : "Not installed"}
               fix={s.embedding.installed ? null : `Run: ollama pull ${s.embedding.name}`} />
          <Row name="Text recognition (Tesseract)" detail="Reads scanned pages and photos" state={s.tesseract ? "ok" : "bad"}
               label={s.tesseract ? "Found" : "Not found"}
               fix={s.tesseract ? null : "Install Tesseract OCR, then set TESSERACT_CMD in backend/.env if it is not on PATH."} />
          <Row name="Vision model" detail={s.vision.name || "Not set"}
               state={!s.vision.enabled ? "off" : s.vision.installed ? "ok" : "warn"}
               label={!s.vision.enabled ? "Off (optional)" : s.vision.installed ? "Set up" : "Set but not installed"}
               fix={!s.vision.enabled
                 ? "Optional. Without it, scans are read with Tesseract only."
                 : s.vision.installed
                   ? "Used when Tesseract cannot read a scan, or when you ask for it on upload."
                   : `Run: ollama pull ${s.vision.name}`} />
        </ul>
      )}

      {models && (
        <>
          <h2 className="section-title">Models you can choose</h2>
          <ul className="model-list">
            {models.models.map((m) => (
              <li key={m.name}>
                <span>{m.name}{m.name === models.default ? " (default)" : ""}</span>
                <span className="soft-note">{m.installed ? "Installed" : "Not installed"}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
