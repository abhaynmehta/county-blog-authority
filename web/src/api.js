// Thin client over the audit API. Kept separate from components so tests
// can stub it, and so the base URL changes in exactly one place.

const BASE = import.meta.env?.VITE_API_BASE ?? "/api";

async function request(path, options) {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    // The API returns {detail: "..."} on error; fall back to the status.
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* response had no JSON body */
    }
    throw new Error(detail);
  }
  return response.json();
}

export const api = {
  health: () => request("/health"),
  audit: (content, slug = "untitled") =>
    request("/audit", { method: "POST", body: JSON.stringify({ content, slug }) }),
  schema: (content, slug = "untitled") =>
    request("/schema", { method: "POST", body: JSON.stringify({ content, slug }) }),
  projects: () => request("/projects"),
  corpus: () => request("/corpus"),
  cannibalization: () => request("/cannibalization"),
};

// Ordering used everywhere issues are displayed: worst first.
export const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"];

export function sortIssues(issues = []) {
  return [...issues].sort(
    (a, b) =>
      SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity),
  );
}

export function scoreBand(score) {
  if (score == null) return "unknown";
  if (score >= 80) return "good";
  if (score >= 60) return "fair";
  return "poor";
}
