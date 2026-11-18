// Thin client for the FastAPI backend. Every function returns parsed JSON and
// throws Error(detail) on a non-2xx response, so the UI can show the backend's
// own (translated) message.

export const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class NetworkError extends Error {}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${API}${path}`, options);
  } catch {
    throw new NetworkError("network"); // the UI replaces this with ui.error.network
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = body?.detail;
    // FastAPI validation errors (422) send a list of {msg}; our own errors send a string.
    const message = Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : detail;
    throw new Error(message || `${res.status} ${res.statusText}`);
  }
  return body;
}

const postJson = (path, body) =>
  request(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const getLabels = () => request("/labels");

export function upload(file, sheet) {
  const form = new FormData();
  form.append("file", file);
  if (sheet) form.append("sheet", sheet);
  return request("/upload", { method: "POST", body: form });
}

export const configure = (body) => postJson("/configure", body);
export const getEda = (sid) => request(`/eda?session_id=${encodeURIComponent(sid)}`);
export const getFindings = (sid) => request(`/findings?session_id=${encodeURIComponent(sid)}`);
export const preview = (body) => postJson("/preview", body);
export const apply = (body) => postJson("/apply", body);
export const exportUrl = (sid) => `${API}/export?session_id=${encodeURIComponent(sid)}`;
