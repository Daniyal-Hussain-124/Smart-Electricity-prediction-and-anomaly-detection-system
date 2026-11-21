import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getAnomalies } from "../api";
import { ANIMATE } from "../config";
import { buildRequest } from "../utils";

export default function AnomalyPanel({ sample, end, apiUp }) {
  const [spike, setSpike] = useState(false);
  const [out, setOut] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => setOut(null), [end, spike]);

  async function run() {
    setBusy(true);
    setError("");
    try {
      const body = buildRequest(sample, end);
      if (spike) body.history[body.history.length - 1] += 6; // fake surge on the latest reading
      setOut(await getAnomalies(body));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const rows = useMemo(
    () => (out ? out.results.map((r) => ({ t: r.timestamp.slice(0, 16).replace("T", " "), power: r.power_kw, flag: r.is_anomaly })) : []),
    [out]
  );
  const flagged = rows.filter((r) => r.flag);

  return (
    <>
      <section className="controls">
        <label>
          <input type="checkbox" checked={spike} onChange={(e) => setSpike(e.target.checked)} /> Add a fake 6 kW surge to
          the latest reading
        </label>
        <button className="run" onClick={run} disabled={busy || !apiUp}>
          {busy ? "Running…" : "Check readings"}
        </button>
      </section>

      {error && <p className="error">{error}</p>}

      {out ? (
        <section>
          <div className="stats">
            <div className={flagged.length ? "alert" : ""}>
              <span>Flagged as unusual</span>
              <strong>{flagged.length}</strong>
            </div>
            <div>
              <span>Readings checked</span>
              <strong>{rows.length}</strong>
            </div>
          </div>

          <div className="chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="#d3dde3" vertical={false} />
                <XAxis dataKey="t" tickFormatter={(t) => t.slice(5)} minTickGap={48} />
                <YAxis unit=" kW" width={64} />
                <Tooltip />
                <Line
                  name="Power"
                  dataKey="power"
                  stroke="#12212B"
                  dot={false}
                  strokeWidth={2}
                  isAnimationActive={ANIMATE}
                  animationDuration={1200}
                />
                {flagged.map((f) => (
                  <ReferenceDot key={f.t} x={f.t} y={f.power} r={6} fill="#D8402F" stroke="none" />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {flagged.length > 0 && (
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Power</th>
                </tr>
              </thead>
              <tbody>
                {flagged.map((f) => (
                  <tr key={f.t}>
                    <td>{f.t}</td>
                    <td>{f.power.toFixed(2)} kW</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      ) : (
        <p className="empty">Pick a moment, then run the check to see the chart.</p>
      )}
    </>
  );
}