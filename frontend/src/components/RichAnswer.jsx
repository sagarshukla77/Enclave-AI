// Renders answer text. "[S1]" tags become numbered citation chips that point at the evidence slips.
// Model output is rendered as plain text (never as HTML), so it cannot inject markup.
export default function RichAnswer({ text, sources, onCite, activeLabel }) {
  const known = new Set((sources || []).map((s) => s.label));
  const parts = (text || "").split(/(\[S\d+\])/g);
  return (
    <p className="answer-text">
      {parts.map((part, i) => {
        const m = part.match(/^\[(S\d+)\]$/);
        if (!m || !known.has(m[1])) return <span key={i}>{part}</span>;
        const label = m[1];
        const num = label.slice(1);
        if (!onCite) return <sup key={i} className="cite cite-static">{num}</sup>;
        return (
          <button
            key={i}
            type="button"
            className={"cite" + (activeLabel === label ? " is-active" : "")}
            onClick={() => onCite(label)}
            aria-label={`Show source ${num}`}
          >
            {num}
          </button>
        );
      })}
    </p>
  );
}
