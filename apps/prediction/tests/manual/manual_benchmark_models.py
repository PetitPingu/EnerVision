"""Script manuel : compare plusieurs algorithmes de régression sur le même
split train/test, pour préparer le benchmark "RF vs Gradient Boosting" évoqué
dans docs/model-choice.md. Chaque candidat est testé en deux variantes :
non pondéré, et pondéré par ancienneté (RECENCY_HALF_LIFE_DAYS — une lecture
récente compte plus qu'une lecture vieille). Les features elles-mêmes
(site_id, hour, minute, day_of_week) sont partagées avec le pipeline de
production via build_features()/build_pipeline_for().

Ne modifie ni MinIO ni le Model Registry servi par /predict : chaque
candidat est loggé dans une expérience MLflow dédiée
("consumption-model-benchmark"), séparée de celle utilisée par
retrain_if_better/train_and_publish, à titre de comparaison seulement (aucun
appel à promote()/register_model côté "current").

Usage (depuis apps/prediction) :
    python tests/manual/manual_benchmark_models.py

Variables d'environnement : DATABASE_URL / TRAINING_DATA_SOURCE,
MLFLOW_TRACKING_URI (voir .env a la racine du monorepo).
"""

import socket
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import mlflow
import pandas as pd
from mlflow.exceptions import MlflowException
from sklearn.base import RegressorMixin, clone
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from sklearn.model_selection import train_test_split

from infrastructure.config import Config
from infrastructure.ml.consumption.features import TARGET_COLUMN, build_features
from infrastructure.ml.consumption.pipeline import build_pipeline_for
from infrastructure.training_data import create_training_data_reader

RANDOM_STATE = 42
TEST_SIZE = 0.2
EXPERIMENT_NAME = "consumption-model-benchmark"

# Pondération par ancienneté ("une lecture récente vaut plus qu'une lecture
# vieille") : demi-vie en jours — à ce point, une lecture pèse moitié moins
# qu'une lecture d'aujourd'hui. 3 jours car l'historique dispo est court
# (~10 jours, voir docs/model-choice.md) : une demi-vie plus longue n'aurait
# quasiment aucun effet différenciant sur une fenêtre aussi courte.
# Distinct de la colonne data_quality (bonne/mauvaise mesure) : ici on ne
# juge que l'âge de la lecture, pas sa fiabilité.
RECENCY_HALF_LIFE_DAYS = 3.0

# Candidats : le RandomForest actuel (baseline en prod), un boosting
# (alternative "phase 2" citée dans docs/model-choice.md) et une régression
# linéaire (pour quantifier le gain du non-linéaire, même recommandation).
CANDIDATES: list[tuple[str, RegressorMixin]] = [
    ("random_forest (baseline actuelle)", RandomForestRegressor(n_estimators=100, random_state=RANDOM_STATE)),
    ("hist_gradient_boosting", HistGradientBoostingRegressor(random_state=RANDOM_STATE)),
    ("ridge", Ridge(random_state=RANDOM_STATE)),
]


@dataclass(frozen=True)
class BenchmarkResult:
    name: str
    mae: float
    rmse: float
    train_seconds: float


def _recency_weights(timestamps: pd.Series, reference: pd.Timestamp) -> pd.Series:
    """Poids par décroissance exponentielle : 1.0 pour une lecture à `reference`,
    0.5 pour une lecture vieille de RECENCY_HALF_LIFE_DAYS, etc."""
    age_days = (reference - timestamps).dt.total_seconds() / 86400
    return 0.5 ** (age_days / RECENCY_HALF_LIFE_DAYS)


def _mlflow_reachable(tracking_uri: str, timeout_seconds: float = 1.5) -> bool:
    """Sonde TCP rapide avant d'appeler l'API MLflow : le client mlflow retente
    plusieurs fois avec backoff sur une connexion refusee/absente, ce qui peut
    bloquer ce script manuel de longues secondes en local sans serveur MLflow up."""
    parsed = urlparse(tracking_uri)
    host, port = parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)
    if not host:
        return False
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def run_benchmark() -> list[BenchmarkResult]:
    print(f"Source donnees : {Config.TRAINING_DATA_SOURCE}")
    reader = create_training_data_reader()
    df = reader.fetch_training_data()
    if df.empty:
        print("Aucune donnee d'entrainement disponible. Arret.")
        return []

    # Mêmes lignes/ordre que build_features() (même filtre dropna) : permet
    # d'aligner les timestamps sur x/y pour la pondération par ancienneté.
    cleaned = df.dropna(subset=[TARGET_COLUMN]).reset_index(drop=True)
    timestamps = pd.to_datetime(cleaned["timestamp"], format="ISO8601")

    x, y = build_features(df)
    x_train, x_test, y_train, y_test, ts_train, _ts_test = train_test_split(
        x, y, timestamps, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )
    print(f"train: {len(x_train)} lignes | test: {len(x_test)} lignes")
    print()

    weights_train = _recency_weights(ts_train, reference=timestamps.max())

    tracking_enabled = False
    if not _mlflow_reachable(Config.MLFLOW_TRACKING_URI):
        print(f"MLflow ({Config.MLFLOW_TRACKING_URI}) injoignable — resultats affiches uniquement, pas de tracking.")
    else:
        try:
            mlflow.set_tracking_uri(Config.MLFLOW_TRACKING_URI)
            mlflow.set_experiment(EXPERIMENT_NAME)
            tracking_enabled = True
        except MlflowException as exc:
            # Ex. serveur distant avec --allowed-hosts restreint (403 "Invalid
            # Host header", voir mlflow/entrypoint.sh) : tracking indisponible
            # depuis ce poste, mais ce n'est pas bloquant pour comparer les modeles.
            print(f"MLflow a refuse la connexion ({exc}) — resultats affiches uniquement, pas de tracking.")

    results: list[BenchmarkResult] = []
    for base_name, regressor in CANDIDATES:
        # Variante non pondérée (comportement actuel) + variante pondérée par
        # ancienneté ("plus une lecture est vieille, moins elle compte"),
        # côte à côte pour isoler l'effet de la pondération par candidat.
        for suffix, sample_weight in (("", None), (" + recency_weight", weights_train)):
            name = base_name + suffix
            pipeline = build_pipeline_for(clone(regressor))
            fit_params = {"model__sample_weight": sample_weight} if sample_weight is not None else {}

            start = time.perf_counter()
            pipeline.fit(x_train, y_train, **fit_params)
            train_seconds = time.perf_counter() - start

            predictions = pipeline.predict(x_test)
            mae = mean_absolute_error(y_test, predictions)
            rmse = root_mean_squared_error(y_test, predictions)
            results.append(BenchmarkResult(name, mae, rmse, train_seconds))

            if tracking_enabled:
                with mlflow.start_run(run_name=name):
                    mlflow.log_params(
                        {
                            "model": base_name,
                            "recency_weighted": sample_weight is not None,
                            "train_size": len(x_train),
                            "test_size": len(x_test),
                        }
                    )
                    mlflow.log_metrics({"mae": mae, "rmse": rmse, "train_seconds": train_seconds})

    return results


def print_report(results: list[BenchmarkResult]) -> None:
    if not results:
        return

    baseline = next((r for r in results if "baseline" in r.name), results[0])
    ranked = sorted(results, key=lambda r: r.mae)

    print("=== Comparatif (trie par MAE croissant) ===")
    header = f"{'modele':45} {'MAE (kWh)':>10} {'RMSE (kWh)':>11} {'temps (s)':>10} {'vs baseline':>12}"
    print(header)
    print("-" * len(header))
    for r in ranked:
        delta_pct = (r.mae - baseline.mae) / baseline.mae * 100 if baseline.mae else 0.0
        delta_str = f"{delta_pct:+.1f}%" if r is not baseline else "—"
        print(f"{r.name:45} {r.mae:10.2f} {r.rmse:11.2f} {r.train_seconds:10.3f} {delta_str:>12}")
    print()

    best = ranked[0]
    if best is baseline:
        print(f"Aucun candidat ne bat la baseline ({baseline.name}, MAE={baseline.mae:.2f}).")
    else:
        print(
            f"Meilleur candidat : {best.name} "
            f"(MAE={best.mae:.2f} vs {baseline.mae:.2f} pour la baseline)."
        )


if __name__ == "__main__":
    print_report(run_benchmark())
