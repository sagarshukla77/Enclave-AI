import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { formatDateTime } from "../format.js";

const ALLOWED = [".pdf", ".docx", ".png", ".jpg", ".jpeg"];
const extOf = (name) => (name.lastIndexOf(".") >= 0 ? name.slice(name.lastIndexOf(".")).toLowerCase() : "");
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

function summarize(r) {
  let text = `${plural(r.chunks_indexed, "passage")} indexed from ${plural(r.pages, "page")}.`;
  if (r.ocr_pages > 0) text += ` ${plural(r.ocr_pages, "page")} read with text recognition.`;
  if (r.vision_pages > 0) text += ` ${plural(r.vision_pages, "page")} read with the vision model.`;
  return text;
}

export default function Documents({ visible }) {
  const [docs, setDocs] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [queue, setQueue] = useState([]);
  const [dragging, setDragging] = useState(false);
  const [useVision, setUseVision] = useState(false);
  const [confirming, setConfirming] = useState(null);
  const [deleteError, setDeleteError] = useState("");
  const fileInput = useRef(null);

  const load = useCallback(() => {
    api.documents()
      .then((d) => { setDocs(d.documents); setLoadError(""); })
      .catch((e) => setLoadError(e.message));
  }, []);

  useEffect(() => { if (visible) load(); }, [visible, load]);

  const patchItem = (id, patch) => setQueue((q) => q.map((it) => (it.id === id ? { ...it, ...patch } : it)));

  async function handleFiles(fileList) {
    const files = Array.from(fileList);
    if (files.length === 0) return;
    const items = files.map((file, i) => ({
      id: `${Date.now()}-${i}-${Math.random().toString(36).slice(2, 6)}`,
      file,
      name: file.name,
      status: ALLOWED.includes(extOf(file.name)) ? "waiting" : "rejected",
    }));
    setQueue((q) => [
      ...items.map((it) => ({
        id: it.id, name: it.name, status: it.status,
        message: it.status === "rejected" ? `This file type is not supported. Use ${ALLOWED.join(", ")}.` : "",
      })),
      ...q,
    ]);
    for (const it of items) {
      if (it.status === "rejected") continue;
      patchItem(it.id, { status: "uploading" });
      try {
        const r = await api.upload(it.file, useVision);
        patchItem(it.id, { status: "done", message: summarize(r), warnings: r.warnings || [], empty: r.chunks_indexed === 0 });
      } catch (e) {
        patchItem(it.id, { status: "error", message: e.message });
      }
    }
    load();
  }

  async function remove(filename) {
    setDeleteError("");
    try {
      await api.deleteDocument(filename);
      setConfirming(null);
      load();
    } catch (e) {
      setDeleteError(e.message);
    }
  }

  return (
    <section className="view" hidden={!visible} aria-labelledby="docs-title">
      <header className="page-head">
        <div>
          <h1 id="docs-title">Documents</h1>
          <p className="lede">Add the reports, manuals and procedures you want to ask about. Scanned pages and photos are read with text recognition.</p>
        </div>
      </header>

      <div
        className={"dropzone" + (dragging ? " is-over" : "")}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}
      >
        <p className="dropzone-title">Drop files here</p>
        <p className="soft-note">PDF, Word (.docx), PNG or JPG, up to 50 MB each</p>
        <input
          ref={fileInput}
          id="file-input"
          type="file"
          multiple
          accept={ALLOWED.join(",")}
          className="visually-hidden"
          onChange={(e) => { handleFiles(e.target.files); e.target.value = ""; }}
        />
        <button type="button" className="btn primary" onClick={() => fileInput.current?.click()}>Choose files</button>
        <label className="check">
          <input type="checkbox" checked={useVision} onChange={(e) => setUseVision(e.target.checked)} />
          <span>Read images with the vision model <em>(only if one is set up; otherwise text recognition is used)</em></span>
        </label>
      </div>

      {queue.length > 0 && (
        <div className="upload-head">
          <button
            type="button"
            className="link-button"
            onClick={() => setQueue((q) => q.filter((it) => it.status === "waiting" || it.status === "uploading"))}
          >
            Clear list
          </button>
        </div>
      )}
      {queue.length > 0 && (
        <ul className="upload-list" aria-live="polite">
          {queue.map((it) => (
            <li key={it.id} className={"upload-item " + it.status}>
              <div>
                <strong>{it.name}</strong>
                <span className="upload-state">
                  {it.status === "waiting" && "Waiting"}
                  {it.status === "uploading" && "Reading and indexing…"}
                  {it.status === "done" && (it.empty ? "Added, but no text was found" : "Added")}
                  {it.status === "error" && "Failed"}
                  {it.status === "rejected" && "Not added"}
                </span>
              </div>
              {it.message && <p className={it.status === "error" || it.status === "rejected" ? "field-error" : "soft-note"}>{it.message}</p>}
              {it.warnings && it.warnings.map((w, i) => <p key={i} className="warn-note">{w}</p>)}
            </li>
          ))}
        </ul>
      )}

      <h2 className="section-title">In your knowledge base</h2>
      {loadError && <p className="error-note" role="alert">{loadError}</p>}
      {docs === null && !loadError && <p className="soft-note">Loading…</p>}
      {docs && docs.length === 0 && (
        <p className="empty-line">No documents yet. Add a file above to get started.</p>
      )}
      {docs && docs.length > 0 && (
        <div className="table-wrap sheet">
          <table>
            <thead>
              <tr><th>File</th><th>Pages</th><th>Passages</th><th>Added by</th><th>Added</th><th><span className="visually-hidden">Actions</span></th></tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.filename}>
                  <td className="cell-main">{d.filename}</td>
                  <td>{d.pages}</td>
                  <td>{d.chunks}</td>
                  <td>{d.uploaded_by || "unknown"}</td>
                  <td>{formatDateTime(d.uploaded_at)}</td>
                  <td className="cell-actions">
                    {confirming === d.filename ? (
                      <span className="confirm">
                        Remove this file?
                        <button type="button" className="btn danger small" onClick={() => remove(d.filename)}>Yes, remove</button>
                        <button type="button" className="btn quiet small" onClick={() => setConfirming(null)}>Keep</button>
                      </span>
                    ) : (
                      <button type="button" className="btn quiet small" onClick={() => { setConfirming(d.filename); setDeleteError(""); }}>
                        Remove<span className="visually-hidden"> {d.filename}</span>
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {deleteError && <p className="error-note" role="alert">{deleteError}</p>}
    </section>
  );
}
