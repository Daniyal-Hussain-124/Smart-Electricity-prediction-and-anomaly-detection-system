# FastAPI for Smart Gradient Analytics (load forecasting + anomaly detection)
# Run from the project folder:  uvicorn API.main:app --reload
# Docs / test page:             http://127.0.0.1:8000/docs

import json
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sklearn.metrics import (
    confusion_matrix,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    mean_squared_error,
    mean_absolute_error,
    r2_score,
)

MODELS = Path(__file__).resolve().parent.parent / "Models"
DATA = Path(__file__).resolve().parent.parent / "Data" / "processed" / "Cleaned.parquet"

MIN_HISTORY = 97      # current value + 96 steps back
MAX_HISTORY = 5000
STEP = pd.Timedelta(minutes=15)

state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # load everything once at startup
    state["forecaster"] = joblib.load(MODELS / "load_forecasting_model.pkl")
    state["anomaly_model"] = joblib.load(MODELS / "anomaly_deployed_model.pkl")
    state["art"] = json.loads((MODELS / "anomaly_artifacts.json").read_text())
    yield
    state.clear()

app = FastAPI(title="Smart Gradient Analytics API", version="1.0", lifespan=lifespan)

# lets the React page (any local port) call this API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    errors = [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})

# ---------- input / output schemas ----------
class SeriesInput(BaseModel):
    last_timestamp: datetime = Field(description="Time of the last reading, e.g. 2010-11-20T18:00:00")
    history: list[float] = Field(description="15-min average power in kW, oldest first, at least 97 values")
    
    @field_validator("history")
    @classmethod
    def check_history(cls, v):
        if len(v) < MIN_HISTORY:
            raise ValueError(f"need at least {MIN_HISTORY} readings (24 hours + the current one), got {len(v)}")
        if len(v) > MAX_HISTORY:
            raise ValueError(f"at most {MAX_HISTORY} readings per request")
        if not np.isfinite(v).all():
            raise ValueError("history contains NaN or infinite values, fill or remove them first")
        return v

class ForecastInput(SeriesInput):
    steps: int = Field(1, ge=1, le=96, description="How many 15-min steps ahead (1 = next 15 minutes)")

class AnomalyInput(SeriesInput):
    alert_rate: float | None = Field(None, ge=0.005, le=0.15, description="Share of normal readings you accept as flagged")

class ForecastPoint(BaseModel):
    timestamp: datetime
    predicted_power_kw: float

class ForecastOutput(BaseModel):
    steps: int
    note: str
    forecast: list[ForecastPoint]

class AnomalyPoint(BaseModel):
    timestamp: datetime
    power_kw: float
    is_anomaly: bool
    anomaly_score: float

class AnomalyOutput(BaseModel):
    note: str
    n_scored: int
    n_anomalies: int
    results: list[AnomalyPoint]

class AnomalyMetricsOutput(BaseModel):
    model: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    confusion_matrix: list[list[int]]
    note: str

class ForecastMetricsOutput(BaseModel):
    model: str
    mse: float
    mae: float
    r2_score: float
    note: str

# ---------- feature building ----------
def forecast_features(h: np.ndarray, ts: pd.Timestamp) -> pd.DataFrame:
    row = {
        "lag_0": h[-1], "lag_1": h[-2], "lag_2": h[-3], "lag_4": h[-5], "lag_96": h[-97],
        "rolling_mean_1h": h[-4:].mean(), "rolling_mean_6h": h[-24:].mean(),
        "hour": ts.hour, "day_of_week": ts.dayofweek, "month": ts.month,
        "is_weekend": int(ts.dayofweek >= 5),
    }
    cols = list(state["forecaster"].feature_names_in_)
    return pd.DataFrame([row])[cols]

def anomaly_features(h: np.ndarray, times: pd.DatetimeIndex) -> np.ndarray:
    art = state["art"]
    n = len(h)
    i = np.arange(MIN_HISTORY - 1, n)
    t = times[i]
    weekend = (t.dayofweek >= 5).astype(int)
    hour = t.hour
    mean = np.array([art["normal"][f"{w}_{hh}"]["mean"] for w, hh in zip(weekend, hour)])
    std = np.array([art["normal"][f"{w}_{hh}"]["std"] for w, hh in zip(weekend, hour)])
    power = h[i]
    zscore = (power - mean) / std
    diff_1 = h[i] - h[i - 1]
    change_vs_yesterday = h[i] - h[i - 96]
    windows = np.lib.stride_tricks.sliding_window_view(h, 4).mean(axis=1)
    rolling_mean_1h = windows[i - 4]
    X = np.column_stack([power, zscore, diff_1, change_vs_yesterday, rolling_mean_1h, hour])
    return (X - np.array(art["scaler_mean"])) / np.array(art["scaler_scale"])

# ---------- endpoints ----------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "forecaster": type(state["forecaster"]).__name__,
        "forecast_features": list(state["forecaster"].feature_names_in_),
        "anomaly_model": type(state["anomaly_model"]).__name__,
        "anomaly_features": state["art"]["features"],
        "min_history": MIN_HISTORY,
    }

@app.post("/forecast", response_model=ForecastOutput)
def forecast(req: ForecastInput):
    h = list(req.history)
    ts = pd.Timestamp(req.last_timestamp)
    out = []
    for _ in range(req.steps):
        pred = float(state["forecaster"].predict(forecast_features(np.array(h), ts))[0])
        ts = ts + STEP
        out.append(ForecastPoint(timestamp=ts.to_pydatetime(), predicted_power_kw=round(pred, 4)))
        h.append(pred)
    note = "one-step-ahead model" if req.steps == 1 else \
        "model is trained for the next 15 min only, later steps reuse earlier predictions and get less accurate"
    return ForecastOutput(steps=req.steps, note=note, forecast=out)

@app.post("/anomaly", response_model=AnomalyOutput)
def anomaly(req: AnomalyInput):
    h = np.asarray(req.history, dtype=float)
    times = pd.date_range(end=pd.Timestamp(req.last_timestamp), periods=len(h), freq="15min")
    X = anomaly_features(h, times)
    model = state["anomaly_model"]
    score = -model.decision_function(X)
    if req.alert_rate is None:
        flag = model.predict(X) == -1
    else:
        flag = score > np.quantile(state["art"]["score_quantiles"], 1 - req.alert_rate)
    pos = np.arange(MIN_HISTORY - 1, len(h))
    results = [
        AnomalyPoint(timestamp=times[p].to_pydatetime(), power_kw=float(h[p]),
                     is_anomaly=bool(f), anomaly_score=round(float(s), 4))
        for p, f, s in zip(pos, flag, score)
    ]
    note = "a flag is advice, not a verdict: check the appliance."
    return AnomalyOutput(note=note, n_scored=len(results), n_anomalies=int(flag.sum()), results=results)

@app.get("/metrics/anomaly", response_model=AnomalyMetricsOutput)
def anomaly_metrics():
    """Calculates evaluation metrics (Confusion Matrix, Accuracy, Precision, Recall, F1) for Isolation Forest on the test set."""
    df = pd.read_parquet(DATA)
    power = df["Global_active_power"].resample("15min").mean()
    train_end = pd.Timestamp(state["art"]["train_end"])
    
    test_power = power[power.index >= train_end]
    test_data = pd.DataFrame({"power": test_power})
    test_data["hour"] = test_data.index.hour
    test_data["is_weekend"] = (test_data.index.dayofweek >= 5).astype(int)
    
    art = state["art"]
    normal = art["normal"]
    
    # Compute test features
    means = np.array([normal[f"{w}_{h}"]["mean"] for w, h in zip(test_data["is_weekend"], test_data["hour"])])
    stds = np.array([normal[f"{w}_{h}"]["std"] for w, h in zip(test_data["is_weekend"], test_data["hour"])])
    
    test_data["zscore"] = (test_data["power"] - means) / stds
    test_data["diff_1"] = test_data["power"].diff()
    test_data["change_vs_yesterday"] = test_data["power"] - test_data["power"].shift(96)
    test_data["rolling_mean_1h"] = test_data["power"].shift(1).rolling(4).mean()
    test_data = test_data.dropna()
    
    X_test = test_data[["power", "zscore", "diff_1", "change_vs_yesterday", "rolling_mean_1h", "hour"]]
    Xs_test = (X_test - np.array(art["scaler_mean"])) / np.array(art["scaler_scale"])
    
    model = state["anomaly_model"]
    preds = model.predict(Xs_test)
    y_pred = (preds == -1).astype(int)  # 1 = anomaly, 0 = normal
    
    # Ground truth proxy based on absolute statistical z-score outliers (|z| > 3)
    y_true = (np.abs(test_data["zscore"]) > 3).astype(int)
    
    cm = confusion_matrix(y_true, y_pred).tolist()
    acc = float(accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    
    return AnomalyMetricsOutput(
        model="IsolationForest",
        accuracy=round(acc, 4),
        precision=round(prec, 4),
        recall=round(rec, 4),
        f1_score=round(f1, 4),
        confusion_matrix=cm,
        note="Evaluation metrics computed on the test partition using statistical z-score outliers (|z| > 3) as ground truth reference."
    )

@app.get("/metrics/forecast", response_model=ForecastMetricsOutput)
def forecast_metrics():
    """Calculates evaluation metrics (MSE, MAE, R2 Score) for the XGBoost forecasting model on a test sample."""
    df = pd.read_parquet(DATA)
    power = df["Global_active_power"].resample("15min").mean().dropna()
    
    # Take a representative sample from the latter portion of the series for performance evaluation
    test_series = power.iloc[int(len(power) * 0.70):int(len(power) * 0.75)]
    h = test_series.values
    times = test_series.index
    
    forecaster = state["forecaster"]
    cols = list(forecaster.feature_names_in_)
    
    X_rows = []
    y_true = []
    
    # Start from index 96 so we have enough history (97 points: index 0 to 96 inclusive) for lag_96
    for i in range(96, len(h)):
        ts = times[i]
        # Grab 97 historical points leading up to index i (inclusive of lag_96)
        window = h[i-96:i+1]
        row = {
            "lag_0": window[-1], 
            "lag_1": window[-2], 
            "lag_2": window[-3], 
            "lag_4": window[-5], 
            "lag_96": window[0], # The 97th item back from the current step
            "rolling_mean_1h": window[-4:].mean(), 
            "rolling_mean_6h": window[-24:].mean(),
            "hour": ts.hour, 
            "day_of_week": ts.dayofweek, 
            "month": ts.month,
            "is_weekend": int(ts.dayofweek >= 5),
        }
        X_rows.append(row)
        y_true.append(h[i])
        
    X_test = pd.DataFrame(X_rows)[cols]
    y_pred = forecaster.predict(X_test)
    
    mse = float(mean_squared_error(y_true, y_pred))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred))
    
    return ForecastMetricsOutput(
        model="XGBoostRegressor",
        mse=round(mse, 4),
        mae=round(mae, 4),
        r2_score=round(r2, 4),
        note="Metrics evaluated on a test subset of 15-minute aggregated power readings."
    )