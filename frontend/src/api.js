import { API_URL } from "./config";

export async function checkHealth() {
  try {
    const res = await fetch(`${API_URL}/health`);
    return res.ok;
  } catch {
    return false;
  }
}

async function post(path, body) {
  let res;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error("Can't reach the API. Start uvicorn and check the address.");
  }
  const data = await res.json();
  if (!res.ok) throw new Error(Array.isArray(data.detail) ? data.detail[0].msg : "Request failed");
  return data;
}

async function get(path) {
  let res;
  try {
    res = await fetch(`${API_URL}${path}`);
  } catch {
    throw new Error("Can't reach the API. Start uvicorn and check the address.");
  }
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Request failed");
  return data;
}

export const getForecast = (body, steps) => post("/forecast", { ...body, steps });
export const getAnomalies = (body) => post("/anomaly", body);

// New evaluation metric endpoints
export const getAnomalyMetrics = () => get("/metrics/anomaly");
export const getForecastMetrics = () => get("/metrics/forecast");