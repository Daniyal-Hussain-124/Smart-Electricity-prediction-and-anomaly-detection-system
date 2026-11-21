import { useEffect, useState } from "react";
import { checkHealth } from "./api";
import { WINDOW } from "./config";
import AnomalyPanel from "./components/AnomalyPanel";
import ForecastPanel from "./components/ForecastPanel";
import Header from "./components/Header";
import TimePicker from "./components/TimePicker";
import MetricsPanel from "./components/MetricsPanel";

export default function App() {
  const [sample, setSample] = useState(null);
  const [apiUp, setApiUp] = useState(null);
  const [tab, setTab] = useState("forecast");
  const [end, setEnd] = useState(WINDOW);

  useEffect(() => {
    fetch("/sample_data.json")
      .then((r) => r.json())
      .then((s) => {
        setSample(s);
        setEnd(Math.min(WINDOW + 130, s.values.length - 1));
      });
    checkHealth().then(setApiUp);
  }, []);

  if (!sample) return <main className="page">Loading sample readings…</main>;

  let Panel;
  if (tab === "forecast") Panel = ForecastPanel;
  else if (tab === "anomaly") Panel = AnomalyPanel;
  else Panel = MetricsPanel;

  return (
    <main className="page">
      <Header apiUp={apiUp} />
      
      {tab !== "metrics" && <TimePicker sample={sample} end={end} setEnd={setEnd} />}

      <nav role="tablist">
        <button role="tab" aria-selected={tab === "forecast"} onClick={() => setTab("forecast")}>
          Forecast usage
        </button>
        <button role="tab" aria-selected={tab === "anomaly"} onClick={() => setTab("anomaly")}>
          Find anomalies
        </button>
        <button role="tab" aria-selected={tab === "metrics"} onClick={() => setTab("metrics")}>
          Model metrics
        </button>
      </nav>
      
      <Panel sample={sample} end={end} apiUp={apiUp} />
    </main>
  );
}