const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  createInteraction: (payload) =>
    request("/api/interactions", { method: "POST", body: JSON.stringify(payload) }),

  updateInteraction: (id, payload) =>
    request(`/api/interactions/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),

  listInteractions: (hcpName) =>
    request(`/api/interactions${hcpName ? `?hcp_name=${encodeURIComponent(hcpName)}` : ""}`),

  searchHcps: (q) => request(`/api/hcps?q=${encodeURIComponent(q)}`),

  chat: (message, sessionId) =>
    request("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, session_id: sessionId }),
    }),
};
