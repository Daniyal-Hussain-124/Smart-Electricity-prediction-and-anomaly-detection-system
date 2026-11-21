# Builds everything the DEPLOYED anomaly detector needs (report section 8.6):
#   1) the 6-feature Isolation Forest (200 trees, contamination 0.02, seed 42) -> Models/anomaly_deployed_model.pkl
#      (anomaly_detection_model.pkl is the 13-feature hourly experiment from the notebook and is not used by the API)
#   2) the StandardScaler (mean / scale of the 6 features)
#   3) the "normal usage" table (mean/std per weekday-weekend and hour) used for the zscore feature
#   4) score quantiles of the training period, so the API can offer a custom alert rate
# Train part only (first 70% of the 15-minute series).
# Run once from the project folder:  python API/build_anomaly_artifacts.py

import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "Data" / "processed" / "Cleaned.parquet"
MODEL = ROOT / "Models" / "anomaly_deployed_model.pkl"
OUT = ROOT / "Models" / "anomaly_artifacts.json"

FEATURES = ["power", "zscore", "diff_1", "change_vs_yesterday", "rolling_mean_1h", "hour"]

df = pd.read_parquet(DATA)
power = df["Global_active_power"].resample("15min").mean()
train_end = power.index[int(len(power) * 0.70)]

data = pd.DataFrame({"power": power})
data["hour"] = data.index.hour
data["is_weekend"] = (data.index.dayofweek >= 5).astype(int)

# normal usage per (weekend, hour), train part only
normal = data[data.index < train_end].groupby(["is_weekend", "hour"])["power"].agg(["mean", "std"])
key = pd.MultiIndex.from_arrays([data["is_weekend"], data["hour"]])

data["zscore"] = (data["power"] - normal["mean"].reindex(key).values) / normal["std"].reindex(key).values
data["diff_1"] = data["power"].diff()
data["change_vs_yesterday"] = data["power"] - data["power"].shift(96)
data["rolling_mean_1h"] = data["power"].shift(1).rolling(4).mean()

data = data.dropna()

X_train = data[data.index < train_end][FEATURES]

scaler = StandardScaler().fit(X_train)
Xs = scaler.transform(X_train)

model = IsolationForest(n_estimators=200, contamination=0.02, random_state=42, n_jobs=-1).fit(Xs)
joblib.dump(model, MODEL)

# check: with contamination=0.02 about 2% of the train rows should be flagged
share = (model.predict(Xs) == -1).mean()
print(f"flagged share on train: {share:.4f} (expected about 0.02)")
assert abs(share - 0.02) < 0.002, "flagged share on train is not about 2%, check the data/notebook version"

artifacts = {
    "features": FEATURES,
    "scaler_mean": scaler.mean_.tolist(),
    "scaler_scale": scaler.scale_.tolist(),
    "normal": {f"{w}_{h}": {"mean": float(r["mean"]), "std": float(r["std"])}
               for (w, h), r in normal.iterrows()},
    "train_end": str(train_end),
    "score_quantiles": np.quantile(-model.decision_function(Xs), np.linspace(0, 1, 1001)).tolist(),
}

OUT.write_text(json.dumps(artifacts, indent=2))
print("saved", OUT)