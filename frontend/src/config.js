export const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
export const WINDOW = 192; // readings sent to the API (2 days of 15-minute data)
export const STEP_MS = 15 * 60 * 1000;
export const ANIMATE = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;