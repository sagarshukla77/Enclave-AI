// All calls to the backend live here.
// Development (npm run dev) talks to http://127.0.0.1:8000; the built app is served by the
// backend itself, so it uses the same address. Override with VITE_API_URL if needed.
const BASE = import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");
const TOKEN_KEY = "enclave_token";

let token = sessionStorage.getItem(TOKEN_KEY);
let onUnauthorized = () => {};

export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn; };
export const hasToken = () => Boolean(token);
export function setToken(value) {
  token = value;
  if (value) sessionStorage.setItem(TOKEN_KEY, value);
  else sessionStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.status = status;
  }
}

function detailText(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
  return "The request failed.";
}

async function request(path, { method = "GET", json, form, formData, params, raw = false } = {}) {
  const query = params
    ? "?" + new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== null)).toString()
    : "";
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  let body;
  if (json !== undefined) { headers["Content-Type"] = "application/json"; body = JSON.stringify(json); }
  else if (form) body = new URLSearchParams(form);
  else if (formData) body = formData;

  let res;
  try {
    res = await fetch(`${BASE}${path}${query}`, { method, headers, body });
  } catch {
    throw new ApiError("Cannot reach the backend. Make sure it is running (start_backend_windows.bat).", 0);
  }
  if (!res.ok) {
    let message = `Request failed (${res.status}).`;
    try { message = detailText((await res.json()).detail); } catch { /* not JSON */ }
    if (res.status === 401 && token) onUnauthorized();
    throw new ApiError(message, res.status);
  }
  return raw ? res : res.json();
}

export const api = {
  login: (username, password) => request("/login", { method: "POST", form: { username, password } }),
  health: () => request("/health"),
  me: () => request("/me"),
  models: () => request("/models"),
  modelStatus: () => request("/models/status"),
  documents: () => request("/documents"),
  upload: (file, useVision) => {
    const formData = new FormData();
    formData.append("file", file);
    return request("/upload", { method: "POST", formData, params: { use_vision: useVision ? "true" : "false" } });
  },
  deleteDocument: (filename) => request(`/documents/${encodeURIComponent(filename)}`, { method: "DELETE" }),
  chat: (question, model) => request("/chat", { method: "POST", json: { question, model: model || null } }),
  audit: ({ limit = 15, offset = 0, action = "ask" } = {}) => request("/audit", { params: { limit, offset, action } }),
};

// Download a Word/PDF report. A plain link can't send the login token, so fetch it as a file first.
export async function downloadReport(auditId, format) {
  const res = await request(`/report/${auditId}`, { params: { format }, raw: true });
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `report_${auditId}.${format}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
