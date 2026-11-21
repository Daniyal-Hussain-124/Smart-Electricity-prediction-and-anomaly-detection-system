import { STEP_MS, WINDOW } from "./config";

// "2010-11-07 18:00"
export const label = (ms) => new Date(ms).toISOString().slice(0, 16).replace("T", " ");

// time of reading number i in the sample data
export const timeAt = (sample, i) => Date.parse(sample.start + "Z") + i * STEP_MS;

// the JSON the API expects, for the window that ends at reading `end`
export function buildRequest(sample, end) {
  return {
    last_timestamp: new Date(timeAt(sample, end)).toISOString().slice(0, 19),
    history: sample.values.slice(end - WINDOW + 1, end + 1),
  };
}