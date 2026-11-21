import { useEffect, useState } from "react";
import { getAnomalyMetrics, getForecastMetrics } from "../api";

export default function MetricsPanel({ apiUp }) {
  const [anomalyMetrics, setAnomalyMetrics] = useState(null);
  const [forecastMetrics, setForecastMetrics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!apiUp) return;
    setLoading(true);
    Promise.all([getAnomalyMetrics(), getForecastMetrics()])
      .then(([anomaly, forecast]) => {
        setAnomalyMetrics(anomaly);
        setForecastMetrics(forecast);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [apiUp]);

  if (!apiUp) return <p className="empty">Connect to the API to view model performance metrics.</p>;
  if (loading) return <p className="empty">Loading evaluation metrics…</p>;
  if (error) return <p className="error">{error}</p>;

  return (
    <section>
      <h2>Model Evaluation Metrics</h2>
      <p className="note">Performance assessed on held-out test partitions.</p>

      {forecastMetrics && (
        <div style={{ marginBottom: "36px" }}>
          <h3>XGBoost Load Forecaster</h3>
          <div className="stats">
            <div>
              <span>Mean Squared Error (MSE)</span>
              <strong>{forecastMetrics.mse}</strong>
            </div>
            <div>
              <span>Mean Absolute Error (MAE)</span>
              <strong>{forecastMetrics.mae}</strong>
            </div>
            <div>
              <span>R² Score</span>
              <strong>{forecastMetrics.r2_score}</strong>
            </div>
          </div>
          <small>{forecastMetrics.note}</small>
        </div>
      )}

      {anomalyMetrics && (
        <div>
          <h3>Isolation Forest Anomaly Detector</h3>
          <div className="stats">
            <div>
              <span>Accuracy</span>
              <strong>{(anomalyMetrics.accuracy * 100).toFixed(1)}%</strong>
            </div>
            <div>
              <span>Precision</span>
              <strong>{(anomalyMetrics.precision * 100).toFixed(1)}%</strong>
            </div>
            <div>
              <span>Recall</span>
              <strong>{(anomalyMetrics.recall * 100).toFixed(1)}%</strong>
            </div>
            <div>
              <span>F1 Score</span>
              <strong>{anomalyMetrics.f1_score}</strong>
            </div>
          </div>

          <p style={{ marginTop: "24px", marginBottom: "8px" }}>
            <strong>Confusion Matrix:</strong>
          </p>
          <table>
            <thead>
              <tr>
                <th></th>
                <th>Predicted Normal</th>
                <th>Predicted Anomaly</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Actual Normal</strong></td>
                <td>{anomalyMetrics.confusion_matrix[0][0]}</td>
                <td>{anomalyMetrics.confusion_matrix[0][1]}</td>
              </tr>
              <tr>
                <td><strong>Actual Anomaly</strong></td>
                <td>{anomalyMetrics.confusion_matrix[1][0]}</td>
                <td>{anomalyMetrics.confusion_matrix[1][1]}</td>
              </tr>
            </tbody>
          </table>
          <small style={{ display: "block", marginTop: "12px" }}>{anomalyMetrics.note}</small>
        </div>
      )}
    </section>
  );
}