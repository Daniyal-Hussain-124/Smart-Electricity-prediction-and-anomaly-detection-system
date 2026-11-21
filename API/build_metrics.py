import json

from main import MODELS, compute_anomaly_metrics, compute_forecast_metrics

out = {
    "anomaly": compute_anomaly_metrics().model_dump(),
    "forecast": compute_forecast_metrics().model_dump(),
}
(MODELS / "metrics.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
print("saved", MODELS / "metrics.json")