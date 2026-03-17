"""
Seed demo data for AstroGeo presentation.
Creates: synthetic training data, trains models, seeds pgvector tables.
Run: python scripts/seed_demo_data.py
"""

import os
import sys

sys.path.append(os.getcwd())

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error
from sklearn.model_selection import train_test_split


def create_dirs():
    """Create required directories."""
    for d in ["models/production", "models/staging", "data/raw", "data/processed"]:
        Path(d).mkdir(parents=True, exist_ok=True)
    print("✅ Directories created")


def train_asteroid_model():
    """Train asteroid observation success model."""
    print("\n🔭 Training Asteroid Observation Planner model...")
    np.random.seed(42)
    n = 1247

    # Realistic feature distributions
    X = pd.DataFrame(
        {
            "magnitude": np.random.uniform(14, 22, n),
            "distance_au": np.random.uniform(0.01, 0.5, n),
            "velocity_km_s": np.random.uniform(5, 30, n),
            "moon_phase": np.random.uniform(0, 1, n),
            "cloud_cover_percent": np.random.uniform(0, 100, n),
            "object_altitude_deg": np.random.uniform(10, 85, n),
            "observer_latitude": np.random.uniform(8, 37, n),  # India range
        }
    )

    # Realistic labels (brighter, closer, clearer sky = more likely)
    prob = (
        0.3 * (22 - X.magnitude) / 8
        + 0.2 * (0.5 - X.distance_au) / 0.49
        + 0.25 * (1 - X.cloud_cover_percent / 100)
        + 0.15 * X.object_altitude_deg / 85
        + 0.1 * (1 - X.moon_phase)
    ).clip(0, 1)
    y = (np.random.uniform(0, 1, n) < prob).astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestClassifier(
        n_estimators=100, max_depth=12, random_state=42, n_jobs=-1
    )
    model.fit(X_train, y_train)

    acc = accuracy_score(y_test, model.predict(X_test))
    f1 = f1_score(y_test, model.predict(X_test))
    print(f"  Accuracy: {acc:.3f}, F1: {f1:.3f}")

    # Log to MLflow (optional)
    try:
        import mlflow
        import mlflow.sklearn

        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "mlruns"))
        mlflow.set_experiment("astrogeo-asteroid-planner")
        with mlflow.start_run(run_name="rf_v1"):
            mlflow.log_params(
                {"n_estimators": 100, "max_depth": 12, "training_samples": len(X_train)}
            )
            mlflow.log_metrics({"accuracy": acc, "f1_score": f1})
            mlflow.sklearn.log_model(
                model, "model", registered_model_name="AstroGeo-AsteroidPlanner"
            )
        print("  MLflow run logged ✅")
    except Exception as e:
        print(f"  MLflow logging skipped: {e}")

    joblib.dump(model, "models/production/asteroid_planner.joblib")
    print("  Saved to models/production/asteroid_planner.joblib ✅")
    return model


def train_satellite_change_model():
    """Train satellite change detection model."""
    print("\n🛰️  Training Satellite Change Detection model...")
    np.random.seed(43)
    n = 1200

    X = pd.DataFrame(
        {
            "ndvi_current": np.random.uniform(0.1, 0.8, n),
            "ndvi_3months_ago": np.random.uniform(0.1, 0.8, n),
            "rainfall_anomaly_pct": np.random.uniform(-60, 30, n),
            "temperature_avg": np.random.uniform(20, 42, n),
            "month": np.random.randint(1, 13, n),
        }
    )

    # Labels: 0=no_change, 1=deforestation, 2=urbanization, 3=drought_stress
    ndvi_drop = X.ndvi_3months_ago - X.ndvi_current
    y = np.where(
        (ndvi_drop > 0.15) & (X.rainfall_anomaly_pct < -20),
        3,  # drought
        np.where(
            ndvi_drop > 0.25,
            1,  # deforestation
            np.where(ndvi_drop > 0.10, 2, 0),  # urbanization / no change
        ),
    )

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestClassifier(
        n_estimators=150, max_depth=15, random_state=42, n_jobs=-1
    )
    model.fit(X_train, y_train)

    acc = accuracy_score(y_test, model.predict(X_test))
    print(f"  Accuracy: {acc:.3f}")

    joblib.dump(model, "models/production/satellite_change.joblib")
    print("  Saved to models/production/satellite_change.joblib ✅")
    return model


def train_drought_model():
    """Train drought severity regression model."""
    print("\n🌾 Training Drought Intelligence model...")
    np.random.seed(44)
    n = 980

    X = pd.DataFrame(
        {
            "soil_moisture": np.random.uniform(0.04, 0.35, n),
            "rainfall_anomaly_pct": np.random.uniform(-70, 40, n),
            "ndvi_delta": np.random.uniform(-0.5, 0.1, n),
            "temperature_anomaly": np.random.uniform(-2, 5, n),
            "month": np.random.randint(1, 13, n),
        }
    )

    # Severity 0-5: driven by soil moisture and rainfall
    y = (
        3.0 * (0.20 - X.soil_moisture) / 0.16
        + 2.0 * (-X.rainfall_anomaly_pct / 70)
        + 0.5 * X.temperature_anomaly / 5
    ).clip(0, 5)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=100, max_depth=10, random_state=42, n_jobs=-1
    )
    model.fit(X_train, y_train)

    mae = mean_absolute_error(y_test, model.predict(X_test))
    print(f"  MAE: {mae:.3f}")

    joblib.dump(model, "models/production/drought_intelligence.joblib")
    print("  Saved to models/production/drought_intelligence.joblib ✅")
    return model


def print_seed_sql():
    """Print seed SQL for pgvector tables."""
    print("\n" + "=" * 60)
    print("📄 Seed SQL for pgvector tables")
    print("   Run this in PostgreSQL after init_postgis.sql")
    print("=" * 60)
    print(
        """
INSERT INTO asteroid_obs_embeddings (asteroid_id, approach_date, magnitude, distance_au, cloud_cover, moon_phase, outcome, summary_text) VALUES
('2024 BX1', '2024-10-14 21:30:00', 18.2, 0.03, 15.0, 0.21, true, 'Asteroid 2024 BX1 successfully observed from Mumbai on 2024-10-14. Magnitude 18.2, distance 0.03 AU, 15%% cloud cover, new moon phase. 84%% success rate in similar conditions.'),
('2024 YR4', '2024-11-20 22:00:00', 19.1, 0.07, 35.0, 0.65, false, 'Asteroid 2024 YR4 observation failed from Pune. High cloud cover 35%% and 65%% moon phase reduced visibility. Recommend rescheduling.'),
('2023 DZ2', '2023-03-25 20:15:00', 17.5, 0.11, 8.0, 0.05, true, '2023 DZ2 excellent observation from Bangalore. Near-new-moon, clear skies, magnitude 17.5 clearly visible with 8-inch telescope.');

INSERT INTO change_event_embeddings (region_name, event_date, change_type, ndvi_delta, area_ha, data_source, summary_text) VALUES
('Western Ghats, Maharashtra', '2023-10-15', 'deforestation', -0.32, 1250.5, 'Sentinel-2 (10m)', 'Western Ghats deforestation event Oct 2023: NDVI dropped from 0.71 to 0.39 over 1250 ha. Likely illegal logging. Rainfall anomaly: -8%%.'),
('Nashik District, Maharashtra', '2024-06-20', 'drought_stress', -0.28, 8500.0, 'Sentinel-2 + MODIS', 'Nashik district vegetation stress June 2024: NDVI decline 0.28 correlated with -42%% monsoon rainfall anomaly. 8500 ha affected.'),
('Pune Urban Fringe', '2023-12-01', 'urbanization', -0.18, 320.0, 'Sentinel-2 (10m)', 'Rapid urbanization at Pune fringe: 320 ha converted from agriculture to construction. NDVI drop 0.18 consistent with concrete expansion.');

INSERT INTO drought_event_embeddings (district_name, state_name, event_date, severity_score, soil_moisture, rainfall_anomaly, ndvi_delta, summary_text) VALUES
('Osmanabad', 'Maharashtra', '2023-09-30', 3.4, 0.09, -42.0, -0.27, 'Osmanabad district drought warning Level 3 (Sep 2023). Soil moisture 0.09 m3/m3 (threshold: 0.15). Rainfall deficit -42%%. 0.27 NDVI decline indicates severe crop stress. IMD-verified.'),
('Latur', 'Maharashtra', '2023-09-15', 4.1, 0.07, -55.0, -0.35, 'Latur district drought emergency Level 4 (Sep 2023). Critical soil moisture 0.07 m3/m3. Rainfall -55%% below normal. Kharif crop failure likely. IMD verified, NDAP advisory issued.'),
('Solapur', 'Maharashtra', '2019-08-20', 3.8, 0.08, -48.0, -0.31, 'Solapur 2019 severe drought (historical reference). Severity 3.8/5.0. Similar SMAP readings in 2023 preceded Level 4 conditions. Key reference for model calibration.');
    """
    )


if __name__ == "__main__":
    print("=" * 60)
    print("🌌 AstroGeo AI — Demo Data Seeder")
    print("=" * 60)

    create_dirs()
    train_asteroid_model()
    train_satellite_change_model()
    train_drought_model()
    print_seed_sql()

    print("\n" + "=" * 60)
    print("✅ Demo data seeding complete!")
    print("=" * 60)
    print(
        """
Next steps:
  1. docker-compose up -d
  2. psql -U astrogeo_user -d astrogeo_db -f scripts/init_postgis.sql
  3. Run the seed SQL above in PostgreSQL
  4. alembic upgrade head
  5. uvicorn src.api.main:app --reload
  6. Visit http://localhost:8000/docs
  7. Try: POST /api/v1/demo/query with query="Will asteroid 2024 BX1 be visible from Mumbai?"
    """
    )
