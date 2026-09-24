"""Alimente predictions_log avec de vraies prédictions du modèle servi, pour
que la MAE du monitoring (docs/monitoring_model.md) repose sur assez de
points sans attendre que le dashboard génère du trafic.

À lancer DANS le conteneur prediction (même code, mêmes variables
d'environnement que le service), sans rien changer à l'image :

    docker cp scripts/seed_predictions.py prediction:/app/seed_predictions.py
    docker exec -w /app prediction python seed_predictions.py --dry-run
    docker exec -w /app prediction python seed_predictions.py

Pourquoi pas une boucle sur GET /predict : le service recharge le modèle
depuis MLflow à chaque requête, dans un nouveau dossier temporaire jamais
supprimé (~100 Mo par appel dans /tmp du conteneur). Quelques centaines
d'appels ont suffi à saturer le disque du serveur le 23/09/2026. Ici, le
modèle est téléchargé une seule fois, dans un dossier supprimé en fin de
chargement, et toutes les prédictions sont calculées en un seul lot.

Les lignes écrites sont identiques à celles de /predict (même modèle via
l'alias `current`, mêmes features, même model_version = trained_at,
generated_at = now() côté Postgres).

Deux fenêtres, sur une grille de `--step-minutes` :
  - passé  (`--past-days`)    : rapprochable tout de suite avec les mesures
    déjà présentes -> visible au prochain cycle de ModelHealthJob (<= 1h).
  - futur  (`--future-hours`) : rapproché au fil de l'eau, à mesure que les
    mesures réelles arrivent.

Limite à garder en tête : les points passés tombent dans la fenêtre
d'entraînement du modèle actif (10 jours avant trained_at), donc la MAE
obtenue sur eux est une erreur "en échantillon", plus optimiste que la
vraie erreur de généralisation. Les points futurs, eux, sont honnêtes.
"""

import argparse
import os
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone

# Lancé depuis /app (-w /app) : rend importable le code du service.
sys.path.insert(0, os.getcwd())

from application.consumption.predict import _build_prediction_input  # noqa: E402
from db_schema.models import PredictionLog  # noqa: E402
from infrastructure.config import Config  # noqa: E402
from infrastructure.model_store import create_model_store  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402

DEFAULT_SITES = [f"SITE{i:03d}" for i in range(1, 8)]
INSERT_BATCH_SIZE = 1000


def floor_to_step(dt: datetime, step: timedelta) -> datetime:
    """Aligne `dt` sur une grille fixe (époque UTC) : deux exécutions
    successives visent les mêmes instants plutôt qu'une grille décalée."""
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    seconds = (dt - epoch).total_seconds()
    return epoch + timedelta(seconds=(seconds // step.total_seconds()) * step.total_seconds())


def build_targets(now: datetime, past_days: float, future_hours: float, step: timedelta) -> list[datetime]:
    start = floor_to_step(now - timedelta(days=past_days), step) + step
    end = now + timedelta(hours=future_hours)
    targets = []
    t = start
    while t <= end:
        targets.append(t)
        t += step
    return targets


def load_model_once(model_name: str):
    """(pipeline, model_version) du modèle servi, sans rien laisser sur disque.

    MODEL_STORE=mlflow : télécharge la version pointée par l'alias `current`
    dans un dossier temporaire supprimé aussitôt (MlflowModelStore.load_latest
    ne passe pas de dst_path et laisse une copie dans /tmp). Autre store
    (minio) : load_latest charge déjà en mémoire, sans fichier temporaire.
    """
    if Config.MODEL_STORE != "mlflow":
        pipeline, metadata = create_model_store().load_latest(model_name)
        return pipeline, metadata.trained_at

    import mlflow.sklearn
    from infrastructure.model_store.mlflow_store import _ALIAS, _metadata_from_run
    from mlflow.tracking import MlflowClient

    mlflow.set_tracking_uri(Config.MLFLOW_TRACKING_URI)
    client = MlflowClient(tracking_uri=Config.MLFLOW_TRACKING_URI)
    model_version = client.get_model_version_by_alias(model_name, _ALIAS)
    metadata = _metadata_from_run(model_name, client.get_run(model_version.run_id))

    with tempfile.TemporaryDirectory() as dst_path:
        pipeline = mlflow.sklearn.load_model(
            f"models:/{model_name}/{model_version.version}", dst_path=dst_path
        )
    return pipeline, metadata.trained_at


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sites", nargs="+", default=DEFAULT_SITES)
    parser.add_argument("--past-days", type=float, default=7)
    parser.add_argument("--future-hours", type=float, default=24)
    parser.add_argument("--step-minutes", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true", help="Affiche le plan sans charger le modèle ni écrire.")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    step = timedelta(minutes=args.step_minutes)
    targets = build_targets(now, args.past_days, args.future_hours, step)
    past_count = sum(1 for target in targets if target <= now) * len(args.sites)
    total = len(targets) * len(args.sites)

    print(f"modèle       : {Config.MODEL_NAME} (store {Config.MODEL_STORE})")
    print(f"sites        : {', '.join(args.sites)}")
    print(f"fenêtre      : {targets[0]:%Y-%m-%d %H:%M} -> {targets[-1]:%Y-%m-%d %H:%M} UTC (pas {args.step_minutes} min)")
    print(f"prédictions  : {total} ({past_count} passées, {total - past_count} futures)")
    if args.dry_run:
        return

    pipeline, model_version = load_model_once(Config.MODEL_NAME)
    print(f"model_version: {model_version}")

    rows = []
    for site_id in args.sites:
        predicted = pipeline.predict(_build_prediction_input(site_id, tuple(targets)))
        rows.extend(
            {
                "id": uuid.uuid4(),
                "site_id": site_id,
                "target_timestamp": target,
                "predicted_consumption_kwh": float(value),
                "model_version": model_version,
            }
            for target, value in zip(targets, predicted)
        )

    engine = create_engine(Config.DATABASE_URL)
    with engine.begin() as conn:
        for start in range(0, len(rows), INSERT_BATCH_SIZE):
            conn.execute(PredictionLog.__table__.insert(), rows[start : start + INSERT_BATCH_SIZE])

    print(f"OK — {len(rows)} lignes écrites dans predictions_log. Le prochain cycle de "
          "ModelHealthJob (etl_worker, horaire) mettra à jour Grafana.")


if __name__ == "__main__":
    main()
