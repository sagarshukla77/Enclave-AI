import { useState } from "react";
import { downloadReport } from "../api.js";

export default function ReportButtons({ auditId }) {
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState("");

  async function get(format) {
    setBusy(format);
    setError("");
    try {
      await downloadReport(auditId, format);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="report-actions">
      <span className="report-label">Save as report</span>
      <button type="button" className="btn quiet" onClick={() => get("docx")} disabled={busy !== null}>
        {busy === "docx" ? "Preparing…" : "Word"}
      </button>
      <button type="button" className="btn quiet" onClick={() => get("pdf")} disabled={busy !== null}>
        {busy === "pdf" ? "Preparing…" : "PDF"}
      </button>
      {error && <span className="field-error" role="alert">{error}</span>}
    </div>
  );
}
