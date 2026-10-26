import { toolLabel } from "../format.js";

// Collapsible "show your working": which tools ran and the agent's steps.
export default function HowAnswered({ tools, trace }) {
  if ((!tools || tools.length === 0) && (!trace || trace.length === 0)) return null;
  return (
    <details className="how">
      <summary>How this was answered</summary>
      {tools && tools.length > 0 && (
        <ul className="how-list">
          {tools.map((t, i) => (
            <li key={i}>
              <strong>{toolLabel(t.tool)}</strong>
              {t.input ? <span className="how-detail">Asked: {t.input}</span> : null}
              {t.output ? <span className="how-detail">Result: {t.output}</span> : null}
            </li>
          ))}
        </ul>
      )}
      {trace && trace.length > 0 && (
        <ul className="how-list">
          {trace.map((s, i) => (
            <li key={i}><strong>{s.step}</strong><span className="how-detail">{s.detail}</span></li>
          ))}
        </ul>
      )}
    </details>
  );
}
