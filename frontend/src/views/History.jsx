import { Fragment, useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { formatDateTime, formatSeconds, isFailed, normalizeSources, normalizeTools } from "../format.js";
import RichAnswer from "../components/RichAnswer.jsx";
import Verdict from "../components/Verdict.jsx";
import EvidenceList from "../components/EvidenceList.jsx";
import HowAnswered from "../components/HowAnswered.jsx";
import ReportButtons from "../components/ReportButtons.jsx";

const PAGE = 15;
const FILTERS = [
  { id: "ask", label: "Questions" },
  { id: "upload", label: "Uploads" },
  { id: "delete", label: "Removals" },
  { id: "all", label: "Everything" },
];
const ACTION_LABEL = { ask: "Question", upload: "Upload", delete: "Removal" };

function Detail({ row }) {
  const [cite, setCite] = useState(null);
  const sources = normalizeSources(row.sources);
  if ((row.action || "ask") !== "ask") {
    return <p className="soft-note">{row.answer}</p>;
  }
  const failed = isFailed(row.answer);
  return (
    <div className="history-detail">
      <h3 className="question">{row.question}</h3>
      {failed ? (
        <p className="error-note">{row.answer.replace(/^ERROR:\s*/, "")}</p>
      ) : (
        <>
          <RichAnswer
            text={row.answer}
            sources={sources}
            activeLabel={cite}
            onCite={(label) => {
              setCite(label);
              document.getElementById(`h${row.id}-${label}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }}
          />
          {/* The audit log does not store the check result, so only answer-based verdicts (e.g. not found) show here. */}
          <Verdict answer={row.answer} />
        </>
      )}
      {sources.length > 0 && <EvidenceList sources={sources} activeLabel={cite} onSelect={setCite} idPrefix={`h${row.id}`} />}
      <HowAnswered tools={normalizeTools(row.tools_used)} />
      {!failed && <ReportButtons auditId={row.id} />}
    </div>
  );
}

export default function History({ visible }) {
  const [filter, setFilter] = useState("ask");
  const [page, setPage] = useState(0);
  const [rows, setRows] = useState(null);
  const [hasNext, setHasNext] = useState(false);
  const [error, setError] = useState("");
  const [openId, setOpenId] = useState(null);

  const load = useCallback(() => {
    setError("");
    api.audit({ limit: PAGE + 1, offset: page * PAGE, action: filter })
      .then((data) => { setHasNext(data.length > PAGE); setRows(data.slice(0, PAGE)); })
      .catch((e) => setError(e.message));
  }, [filter, page]);

  useEffect(() => { if (visible) load(); }, [visible, load]);

  function pick(id) {
    setFilter(id);
    setPage(0);
    setOpenId(null);
    setRows(null);
  }

  return (
    <section className="view" hidden={!visible} aria-labelledby="history-title">
      <header className="page-head">
        <div>
          <h1 id="history-title">History</h1>
          <p className="lede">Every question, upload and removal is recorded here, so any answer can be traced back and reported.</p>
        </div>
      </header>

      <div className="segmented" role="group" aria-label="Show">
        {FILTERS.map((f) => (
          <button key={f.id} type="button" aria-pressed={filter === f.id} onClick={() => pick(f.id)}>{f.label}</button>
        ))}
      </div>

      {error && <p className="error-note" role="alert">{error}</p>}
      {rows === null && !error && <p className="soft-note">Loading…</p>}
      {rows && rows.length === 0 && <p className="empty-line">Nothing recorded here yet.</p>}

      {rows && rows.length > 0 && (
        <div className="table-wrap sheet">
          <table className="history-table">
            <thead>
              <tr>
                <th>When</th><th>Who</th><th>{filter === "ask" ? "Question" : "Item"}</th><th>Took</th><th><span className="visually-hidden">Open</span></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const open = openId === r.id;
                const failed = isFailed(r.answer);
                const action = r.action || "ask";
                return (
                  <Fragment key={r.id}>
                    <tr className={open ? "is-open" : ""}>
                      <td>{formatDateTime(r.timestamp)}</td>
                      <td>{r.user}</td>
                      <td className="cell-main">
                        {filter !== "ask" && <span className="tag">{ACTION_LABEL[action] || action}</span>}
                        {r.question}
                        {failed && <span className="tag tag-bad">Failed</span>}
                      </td>
                      <td>{action === "ask" ? formatSeconds(r.duration_seconds) : ""}</td>
                      <td className="cell-actions">
                        <button type="button" className="btn quiet small" aria-expanded={open} onClick={() => setOpenId(open ? null : r.id)}>
                          {open ? "Close" : "Open"}
                        </button>
                      </td>
                    </tr>
                    {open && (
                      <tr className="detail-row"><td colSpan={5}><Detail row={r} /></td></tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {rows && (page > 0 || hasNext) && (
        <div className="pager">
          <button type="button" className="btn quiet" disabled={page === 0} onClick={() => { setPage(page - 1); setOpenId(null); }}>Newer</button>
          <span>Page {page + 1}</span>
          <button type="button" className="btn quiet" disabled={!hasNext} onClick={() => { setPage(page + 1); setOpenId(null); }}>Older</button>
        </div>
      )}
    </section>
  );
}
