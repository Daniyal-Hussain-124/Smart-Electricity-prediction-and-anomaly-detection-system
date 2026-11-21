# Smart Electricity Demand & Anomaly Detection System

## Group Members

| Name | Roll Number |
|---|---|
| Muzammil Ahmed | CT-24307 |
| Habib-ul-Rehman | CT-24080 |
| Daniyal Hussain | CT-24093 |

## Overview

A household energy assistant that does two things from smart-meter data:

1. **Forecasts** the average active power of the next 15 minutes (up to 96 steps ahead by recursion).
2. **Flags unusual consumption** with an unsupervised anomaly detector.

Both models are served by a **FastAPI** service and explored through a **React** dashboard.

The solution is hybrid: supervised learning (XGBoost), unsupervised outlier detection (Isolation Forest), and a small rule-based "normal usage" knowledge base (mean and standard deviation of power per weekday/weekend and hour, used as a z-score feature).

## Dataset

- **D1:** [UCI Individual Household Electric Power Consumption](https://doi.org/10.24432/C58K54) (Hebrail & Berard, 2006), CC BY 4.0.
  2,075,259 one-minute readings from one household in Sceaux, France, Dec 2006 to Nov 2010. No personal identifiers.
- **D2:** Synthetic labelled anomaly set derived from D1: 34,168 hourly rows, 683 injected faults (2.00%): spikes, drops and voltage sags.
- **K1:** Domain knowledge used for feature design and the normal-usage table.

> The raw dataset is not bundled. Download it from UCI and place it in the data folder (see below).

## Pipeline

```
UCI raw data -> clean & gap-fill (<= 60 min) -> cleaned series
   |-> Forecasting lane (15-min):  11 features -> 70/15/15 chronological split -> compare 5 models
   |-> Anomaly lane (hourly):      inject D2 faults -> 13 features + scaling -> Isolation Forest vs LOF
                    -> saved models + artifacts -> FastAPI (/health, /forecast, /anomaly) -> React dashboard
```

**Preprocessing highlights**
- 71 gaps of missing minutes; gaps up to 60 min linearly interpolated, 9 longer outages left empty (no invented data).
- IQR outliers kept, since appliance peaks are genuine and the detector must learn from them.
- `Global_intensity` dropped from detector features (correlation ~1.00 with active power).
- Leakage control: features use only data at or before time *t*; scaler and normal-usage table are learned from the training period only.

## Models and results

### Load forecasting (test set: 20,375 intervals, 17 Apr to 26 Nov 2010)

| Model | MAE (kW) | RMSE (kW) | R² |
|---|---|---|---|
| Persistence (baseline) | 0.2903 | 0.4914 | 0.6229 |
| Seasonal naive (baseline) | 0.6093 | 0.9146 | -0.3063 |
| Linear regression | 0.2887 | 0.4631 | 0.6652 |
| Random forest | 0.2709 | 0.4428 | 0.6938 |
| **XGBoost** | **0.2704** | **0.4380** | **0.7004** |

XGBoost lowers MAE by 6.9% and RMSE by 10.9% versus persistence.
**Features (11):** `lag_0, lag_1, lag_2, lag_4, lag_96, rolling_mean_1h, rolling_mean_6h, hour, day_of_week, month, is_weekend`.
**XGBoost settings:** up to 1,000 trees, learning rate 0.05, max depth 6, early stopping after 50 rounds, seed 42.

### Anomaly detection (experiment on D2)

| Model | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|
| **Isolation Forest** | 0.2953 | 0.2958 | 0.2955 | **0.9090** |
| Local Outlier Factor | 0.1243 | 0.1245 | 0.1244 | 0.5709 |

Alert-rate trade-off for Isolation Forest: 2% flagged gives recall 0.296; 5% flagged gives recall 0.559 and the best F1 (0.320); 10% flagged gives recall 0.818.

### Deployed detector

The API receives only a power history, so the deployed Isolation Forest uses **6 features** computed from power alone (15-min data): `power, zscore, diff_1, change_vs_yesterday, rolling_mean_1h, hour`.
It is mainly a **surge detector**: abnormal drops are rarely flagged. It was checked for alert rate (2.00% on training intervals) and on a surge scenario, but **not scored on labelled faults**. The experimental metrics above describe the 13-feature setup.

## Tech stack

| Purpose | Tools |
|---|---|
| Data | pandas, NumPy, PyArrow (Parquet) |
| Statistics | statsmodels (Augmented Dickey-Fuller) |
| Modelling | scikit-learn 1.9.1, XGBoost 3.4.1 |
| Plots | matplotlib, seaborn |
| Serving | FastAPI, Uvicorn, Pydantic, joblib |
| Dashboard | React, Vite, Recharts |

## Project structure

> Adjust folder names to match your repository.

```
.
├── data/                      # raw UCI file + cleaned Parquet
├── notebooks/                 # preprocessing, EDA, forecasting, anomaly experiments
├── models/
│   ├── forecaster.pkl         # XGBoost load forecaster
│   ├── anomaly_model.pkl      # Isolation Forest
│   └── anomaly_artifacts.json # scaler + normal-usage table (48 mean/std pairs)
├── api/                       # FastAPI service
├── dashboard/                 # React + Vite frontend
└── README.md
```

## Getting started

### 1. Backend

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install pandas numpy pyarrow statsmodels scikit-learn xgboost joblib fastapi uvicorn pydantic matplotlib seaborn
uvicorn api.main:app --reload   # adjust module path to your app
```

The API loads the saved models and artifacts once at start-up.

### 2. Dashboard

```bash
cd dashboard
npm install
npm run dev
```

### 3. Reproducing the experiments

1. Download the UCI dataset and place it in `data/`.
2. Run the notebooks in order: preprocessing, EDA, forecasting, anomaly detection.
3. Export the models and `anomaly_artifacts.json` to `models/`.

## API

| Endpoint | Purpose |
|---|---|
| `GET /health` | Service status (dashboard shows "API Live" / "API offline") |
| `POST /forecast` | Predicts next-15-minute power; up to 96 steps by recursion |
| `POST /anomaly` | Returns normal/anomalous flags and scores for a power history |

**Input rules:** only a timestamp and a list of power readings are accepted; histories must contain 97 to 5,000 readings, with no NaN or infinite values. Nothing is stored by the service.

## Dashboard

- **Forecast usage:** next-15-minute prediction with 15 min, 1 h or 6 h look-ahead.
- **Find anomalies:** flagged readings on a chart; optional fake 6 kW surge for demonstration.
- **Model metrics:** evaluation summary for both models.

## Ethics and privacy

- No personal identifiers; the API takes only power values and a timestamp.
- Load patterns can reveal when people are home or away, so any real deployment needs consent and secure storage.
- An anomaly flag is advice, not a verdict; it should prompt a human check, not automatic action.

## Limitations

- One household and one real data source; D2 is derived from D1, so it measures separability of injected faults, not real-world fault detection.
- Test period does not span a full year.
- Limited hyperparameter tuning (XGBoost early stopping only).
- Multi-step forecasts are recursive and degrade with horizon.
- Forecasts are slightly worse than persistence at 06:00 (sharp morning ramps).
- Deployed detector is not scored on labels and rarely flags drops.
- Prototype scale: bundled sample week, no live meter feed, authentication or persistent storage.

## References

1. Hebrail, G. and Berard, A. (2006). *Individual Household Electric Power Consumption*. UCI ML Repository.
2. Liu, Ting and Zhou (2008). *Isolation Forest*. IEEE ICDM.
3. Breunig et al. (2000). *LOF: Identifying Density-Based Local Outliers*. ACM SIGMOD.
4. Chen and Guestrin (2016). *XGBoost: A Scalable Tree Boosting System*. ACM SIGKDD.
5. Breiman (2001). *Random Forests*. Machine Learning, 45(1).
6. Dickey and Fuller (1979). *Distribution of the Estimators for Autoregressive Time Series with a Unit Root*. JASA.
7. Pedregosa et al. (2011). *Scikit-learn: Machine Learning in Python*. JMLR.
8. Chandola, Banerjee and Kumar (2009). *Anomaly Detection: A Survey*. ACM Computing Surveys.
9. Hyndman and Athanasopoulos (2021). *Forecasting: Principles and Practice*, 3rd ed. OTexts.

## License

Dataset: CC BY 4.0 (UCI). Add your own license for the project code.
