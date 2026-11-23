import { useState } from "react";

const LONG = 260;

// One piece of evidence: file, page, how well it matched, and the passage itself.
export default function SourceSlip({ source, active, onSelect, idPrefix = "slip" }) {
  const [open, setOpen] = useState(false);
  const text = source.text || "";
  const long = text.length > LONG;
  const shown = open || !long ? text : text.slice(0, LONG).trimEnd() + "…";
  const match = typeof source.score === "number" ? `${Math.round(source.score * 100)}% match` : null;
  return (
    <li id={`${idPrefix}-${source.label}`} className={"slip" + (active ? " is-active" : "")}>
      <button type="button" className="slip-tab" onClick={() => onSelect?.(source.label)} aria-pressed={active}>
        Source {source.label.slice(1)}
      </button>
      <div className="slip-body">
        <p className="slip-file">{source.source}</p>
        <p className="slip-meta">
          {source.page ? `Page ${source.page}` : "Page not recorded"}
          {match ? `, ${match}` : ""}
        </p>
        {text && <blockquote>{shown}</blockquote>}
        {long && (
          <button type="button" className="link-button" onClick={() => setOpen(!open)}>
            {open ? "Show less" : "Show full passage"}
          </button>
        )}
      </div>
    </li>
  );
}
