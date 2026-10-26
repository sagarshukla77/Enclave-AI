export const NOT_FOUND_TEXT = "Not found in provided documents.";

export function formatDateTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" });
}

export function formatSeconds(s) {
  if (s === undefined || s === null) return "";
  const n = Number(s);
  if (n < 1) return "under a second";
  if (n < 60) return `${Math.round(n)} s`;
  return `${Math.floor(n / 60)} min ${Math.round(n % 60)} s`;
}

// Old or mock audit rows may hold plain strings instead of {label, source, page, ...}
export function normalizeSources(sources) {
  return (sources || []).map((s, i) =>
    typeof s === "string" ? { label: `S${i + 1}`, source: s, page: null, score: null, text: "" } : s
  );
}

export function normalizeTools(tools) {
  return (tools || []).map((t) => (typeof t === "string" ? { tool: t, input: "", output: "" } : t));
}

export const isFailed = (answer) => (answer || "").startsWith("ERROR:");
export const isNotFound = (answer) => (answer || "").trim() === NOT_FOUND_TEXT;

const TOOL_NAMES = { document_search: "Searched your documents", calculator: "Used the calculator" };
export const toolLabel = (name) => TOOL_NAMES[name] || name;
