import SourceSlip from "./SourceSlip.jsx";

export default function EvidenceList({ sources, activeLabel, onSelect, idPrefix }) {
  return (
    <ol className="slips">
      {sources.map((s) => (
        <SourceSlip key={s.label} source={s} active={activeLabel === s.label} onSelect={onSelect} idPrefix={idPrefix} />
      ))}
    </ol>
  );
}
