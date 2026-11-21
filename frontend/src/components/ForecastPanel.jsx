import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getForecast } from "../api";
import { buildRequest, label, timeAt } from "../utils";

export default function ForecastPanel({ sample, end, apiUp }) {
  const [steps, setSteps] = useState(4);
  const [out, setOut] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => setOut(null), [end, steps]);

  async function run() {
    setBusy(true);
    setError("");
    try {
      const body = buildRequest(sample, end);
      const data = await getForecast(body, steps);
      setOut({ data, history: body.history });
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const rows = useMemo(() => {
    if (!out) return [];
    const past = out.history.slice(-96).map((v, i) => ({ t: label(timeAt(sample, end - 95 + i)), actual: v }));
    past[past.length - 1].forecast = past[past.length - 1].actual; // joins the two lines
    const future = out.data.forecast.map((p, i) => ({
      t: label(timeAt(sample, end + 1 + i)),
      forecast: p.predicted_power_kw,
      truth: sample.values[end + 1 + i],
    }));
    return [...past, ...future];
  }, [out]);

  const first = out ? out.data.forecast[0].predicted_power_kw : null;
  const truth = out ? sample.values[end + 1] : undefined;

  return (
    <>
      <section className="controls">
        <label>
          Look ahead{" "}
          <select value={steps} onChange={(e) => setSteps(+e.target.value)}>
            <option value={1}>15 minutes</option>
            <option value={4}>1 hour</option>
            <option value={24}>6 hours</option>
          </select>
        </label>
        <button className="run" onClick={run} disabled={busy || !apiUp}>
          {busy ? "Running…" : "Run forecast"}
        </button>
      </section>

      {error && <p className="error">{error}</p>}

      {out ? (
        <section>
          <p className="result">
            Next 15 minutes: <strong>{first.toFixed(2)} kW</strong>
            {truth !== undefined && <> · the real reading was {truth.toFixed(2)} kW</>}
            {steps > 1 && <small> Later hours reuse earlier predictions, so they are less accurate.</small>}
          </p>
          <div className="chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="#d9e1e5" vertical={false} />
                <XAxis dataKey="t" tickFormatter={(t) => t.slice(5)} minTickGap={48} />
                <YAxis unit=" kW" width={64} />
                <Tooltip />
                <Line name="Actual" dataKey="actual" stroke="#16232B" dot={false} strokeWidth={2} />
                <Line name="Forecast" dataKey="forecast" stroke="#0E7C86" dot={false} strokeWidth={3} />
                <Line name="Real (for comparison)" dataKey="truth" stroke="#16232B" strokeDasharray="4 4" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
      ) : (
        <p className="empty">Pick a moment, then run a forecast to see the chart.</p>
      )}
    </>
  );
}