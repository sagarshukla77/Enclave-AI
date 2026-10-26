import { isFailed, isNotFound } from "../format.js";

function Icon({ kind }) {
  const common = { width: 16, height: 16, viewBox: "0 0 16 16", "aria-hidden": true, fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round" };
  if (kind === "ok") return <svg {...common}><path d="M3 8.5l3.2 3L13 4.5" /></svg>;
  if (kind === "warn") return <svg {...common}><path d="M8 2.5l6 10.5H2z" /><path d="M8 7v3M8 11.6v.1" /></svg>;
  return <svg {...common}><circle cx="8" cy="8" r="5.6" /><path d="M5.6 5.6l4.8 4.8" /></svg>;
}

// The one-line trust signal under each answer.
export function getVerdict(answer, validation) {
  if (isFailed(answer)) return { kind: "bad", title: "Could not answer", note: "Something went wrong while answering. See the message above." };
  if (isNotFound(answer)) return { kind: "bad", title: "Not in your documents", note: "The documents you have added do not contain this. Nothing was guessed." };
  if (!validation) return null;
  if (validation.passed) return { kind: "ok", title: "Checked against sources", note: "Citations and numbers match the documents." };
  return { kind: "warn", title: "Answered, but flagged", note: "Check these points before relying on the answer.", issues: validation.issues || [] };
}

export default function Verdict({ answer, validation }) {
  const v = getVerdict(answer, validation);
  if (!v) return null;
  const kindClass = v.kind === "ok" ? "verdict-ok" : v.kind === "warn" ? "verdict-warn" : "verdict-bad";
  return (
    <div className={`verdict ${kindClass}`}>
      <div className="verdict-head">
        <Icon kind={v.kind} />
        <strong>{v.title}</strong>
      </div>
      <p>{v.note}</p>
      {v.issues && v.issues.length > 0 && (
        <ul>{v.issues.map((issue, i) => <li key={i}>{issue}</li>)}</ul>
      )}
    </div>
  );
}
