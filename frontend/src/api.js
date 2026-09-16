const BASE_URL = "http://localhost:8000";

async function post(path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request to ${path} failed (${res.status})`);
  }
  return res.json();
}

export function generateSchedule() {
  return post("/api/generate");
}

export function disruptBreakdown(tankerId) {
  return post("/api/disrupt/breakdown", { tanker_id: tankerId });
}

export function disruptUrgent(zoneName) {
  return post("/api/disrupt/urgent", { zone_name: zoneName });
}
