"""Backfill de predictions_log / readings_curated pour visualiser le
monitoring du modele (drift + MAE, docs/monitoring_model.md) sans attendre
plusieurs jours d'accumulation reelle.

Genere, pour un site donne :
  - des lectures readings_curated couvrant la fenetre d'entrainement du
    modele (TRAINING_WINDOW_DAYS avant `trained_at`) + les 7 derniers jours,
    calibrees sur l'echelle REELLE recente du site (derniere lecture connue),
    avec un decalage de moyenne applique aux 24 dernieres heures pour
    simuler un drift visible sur le dashboard.
  - des predictions_log rapprochables avec ces lectures (a l'interieur de
    la tolerance de rapprochement), reparties sur les differentes tranches
    d'horizon (HORIZON_BUCKETS) pour peupler la bande d'erreur du graphique.

Les timestamps generes sont alignes sur une grille fixe de 15 minutes
(UTC, independante de l'heure d'execution) : relancer le script ecrase
proprement les lignes precedemment inserees au lieu de les dupliquer ou
de laisser un melange incoherent d'anciennes/nouvelles valeurs.

Usage :
    python scripts/backfill_model_health.py --site-id SITE001

Necessite psycopg (v3) installe et une base Postgres accessible via
DATABASE_URL (ou --database-url). Le stack docker compose doit exposer le
port postgres sur l'hote (voir docker-compose.yml).
"""

import argparse
import math
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from statistics import fmean, pstdev

import psycopg

READING_INTERVAL = timedelta(minutes=15)
TRAINING_WINDOW_DAYS = 10
TRAINED_AT_OFFSET_DAYS = 12
RECENT_WINDOW = timedelta(hours=24)
HORIZON_TARGET_WINDOW_DAYS = 7

DEFAULT_BASELINE_KWH = 20.0

# (label, horizon_representatif_en_heures, ecart-type d'erreur simule, en
# fraction de la baseline du site) — l'ecart-type croit avec l'horizon pour
# donner une bande d'erreur qui s'elargit sur le graphique (cf.
# domain/model_health.py HORIZON_BUCKETS).
HORIZON_PROFILE = [
    ("0-1h", 0.5, 0.08),
    ("1-3h", 2.0, 0.15),
    ("3-6h", 4.5, 0.22),
    ("6-12h", 9.0, 0.32),
    ("12-24h", 18.0, 0.42),
    ("1-3j", 48.0, 0.60),
    ("3-7j", 120.0, 0.85),
]
PREDICTIONS_PER_BUCKET = 8


def floor_to_interval(dt: datetime, interval: timedelta) -> datetime:
    """Aligne `dt` sur une grille fixe (epoque UTC) de pas `interval`, pour
    que deux executions du script a des instants differents produisent les
    memes timestamps (upsert propre au lieu d'un doublon decale)."""
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    seconds = (dt - epoch).total_seconds()
    floored = (seconds // interval.total_seconds()) * interval.total_seconds()
    return epoch + timedelta(seconds=floored)


def fetch_baseline_kwh(conn, site_id: str) -> float:
    """Derniere valeur reelle connue de consumption_kwh pour ce site — sert
    de reference d'echelle (les sites vont de ~150 a ~950 kWh, une baseline
    fixe produirait un "drift" qui n'est qu'un artefact d'echelle, pas un
    vrai signal)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            select consumption_kwh from enervision.readings_curated
            where site_id = %s and consumption_kwh is not null
            order by "timestamp" desc limit 1
            """,
            (site_id,),
        )
        row = cur.fetchone()
    return float(row[0]) if row else DEFAULT_BASELINE_KWH


def consumption_at(t: datetime, baseline: float, mean_offset: float) -> float:
    """Valeur de consommation simulee : cycle journalier + creux le
    week-end + bruit (amplitudes proportionnelles a `baseline`), plus un
    decalage optionnel (utilise pour la fenetre 'recente' afin de simuler
    un drift)."""
    hour = t.hour + t.minute / 60
    daily = 0.20 * baseline * math.sin((hour - 6) / 24 * 2 * math.pi)
    weekend = -0.10 * baseline if t.weekday() >= 5 else 0.0
    noise = random.gauss(0, 0.05 * baseline)
    return max(0.0, baseline + mean_offset + daily + weekend + noise)


def build_readings(now: datetime, trained_at: datetime, baseline: float, drift_offset_std: float):
    history_start = floor_to_interval(trained_at - timedelta(days=TRAINING_WINDOW_DAYS), READING_INTERVAL)
    week_start = floor_to_interval(now - timedelta(days=HORIZON_TARGET_WINDOW_DAYS), READING_INTERVAL)
    recent_start = floor_to_interval(now - RECENT_WINDOW, READING_INTERVAL)
    trained_at = floor_to_interval(trained_at, READING_INTERVAL)

    # Phase 1 : fenetre d'entrainement, sans decalage — sert de reference
    # pour calibrer l'ampleur du drift simule sur la fenetre recente.
    training_readings = []
    t = history_start
    while t < trained_at:
        training_readings.append((t, consumption_at(t, baseline, mean_offset=0.0)))
        t += READING_INTERVAL

    training_mean = fmean(v for _, v in training_readings)
    training_std = pstdev(v for _, v in training_readings) or (0.05 * baseline)
    recent_offset = drift_offset_std * training_std

    # Phase 2 : comble le vide entre la fin de la fenetre d'entrainement et
    # le debut de la fenetre "7 derniers jours" (pas utilise par les calculs
    # de drift/MAE, juste pour eviter un trou si les fenetres se chevauchent
    # peu ; peut etre vide selon TRAINED_AT_OFFSET_DAYS).
    filler_readings = []
    t = trained_at
    while t < week_start:
        filler_readings.append((t, consumption_at(t, baseline, mean_offset=0.0)))
        t += READING_INTERVAL

    # Phase 3 : 7 derniers jours, avec le decalage de drift applique
    # uniquement aux RECENT_WINDOW (24h) les plus recentes.
    week_readings = []
    t = max(week_start, trained_at)
    while t <= now:
        offset = recent_offset if t >= recent_start else 0.0
        week_readings.append((t, consumption_at(t, baseline, mean_offset=offset)))
        t += READING_INTERVAL

    all_readings = training_readings + filler_readings + week_readings
    return all_readings, training_mean, training_std, recent_offset


def build_predictions(readings: list[tuple[datetime, float]], now: datetime, baseline: float, model_version: str):
    by_ts = {ts: value for ts, value in readings}
    week_start = floor_to_interval(now - timedelta(days=HORIZON_TARGET_WINDOW_DAYS), READING_INTERVAL)
    recent_start = floor_to_interval(now - RECENT_WINDOW, READING_INTERVAL)

    week_pool = sorted(ts for ts in by_ts if ts >= week_start)
    recent_pool = [ts for ts in week_pool if ts >= recent_start]

    predictions = []
    for label, horizon_hours, error_std_fraction in HORIZON_PROFILE:
        pool = recent_pool if horizon_hours < 24 else week_pool
        if not pool:
            continue
        sample_size = min(PREDICTIONS_PER_BUCKET, len(pool))
        step = max(1, len(pool) // sample_size)
        targets = pool[::step][:sample_size]

        error_std = error_std_fraction * baseline
        for target_ts in targets:
            actual = by_ts[target_ts]
            predicted = max(0.0, actual + random.gauss(0, error_std))
            generated_at = target_ts - timedelta(hours=horizon_hours)
            predictions.append((target_ts, predicted, model_version, generated_at, label))

    return predictions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--site-id", default="SITE001")
    parser.add_argument("--database-url", default=None)
    parser.add_argument(
        "--drift-offset-std",
        type=float,
        default=1.3,
        help="Decalage de moyenne applique aux 24 dernieres heures, en ecarts-types "
        "de la fenetre d'entrainement (1.0-2.0 = drift modere, >2.0 = critique, "
        "cf. DRIFT_MODERATE_THRESHOLD/DRIFT_CRITICAL_THRESHOLD dans core_api).",
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    random.seed(args.seed)

    database_url = args.database_url or os.environ.get(
        "DATABASE_URL", "postgresql://enervision:changeme@localhost:5432/enervision"
    )
    database_url = database_url.replace("postgresql+psycopg://", "postgresql://")

    now = datetime.now(timezone.utc).replace(microsecond=0)
    trained_at = now - timedelta(days=TRAINED_AT_OFFSET_DAYS)
    model_version = trained_at.strftime("%Y-%m-%dT%H-%M-%SZ")

    with psycopg.connect(database_url, autocommit=False) as conn:
        baseline = fetch_baseline_kwh(conn, args.site_id)

        readings, training_mean, training_std, recent_offset = build_readings(
            now, trained_at, baseline, args.drift_offset_std
        )
        predictions = build_predictions(readings, now, baseline, model_version)

        print(f"site_id            : {args.site_id}")
        print(f"baseline (reel)    : {baseline:.2f} kWh (derniere lecture connue)")
        print(f"model_version      : {model_version} (trained_at = now - {TRAINED_AT_OFFSET_DAYS}j)")
        print(f"readings generees  : {len(readings)}")
        print(f"predictions generees : {len(predictions)}")
        print(f"training mean/std  : {training_mean:.2f} / {training_std:.2f} kWh")
        print(f"decalage recent    : +{recent_offset:.2f} kWh (~{args.drift_offset_std}x std entrainement)")

        recent_start = floor_to_interval(now - RECENT_WINDOW, READING_INTERVAL)

        with conn.cursor() as cur:
            # Nettoie les lectures synthetiques d'un run precedent (grille
            # de timestamps differente avant l'introduction de
            # floor_to_interval, ou echelle non calibree) : tout ce qui
            # precede la fenetre "recente" est de toute facon artificiel
            # (le vrai historique du projet ne remonte pas aussi loin), on
            # peut donc reecrire cette zone sans risque de perdre de vraies
            # donnees. La fenetre recente (24h) est preservee telle quelle,
            # seule la grille exacte y est upsertee juste apres.
            cur.execute(
                """
                delete from enervision.readings_curated
                where site_id = %s and "timestamp" < %s
                """,
                (args.site_id, recent_start),
            )

            cur.executemany(
                """
                insert into enervision.readings_curated
                    (site_id, "timestamp", consumption_kwh, data_quality, null_reasons)
                values (%s, %s, %s, 'good', '{}')
                on conflict (site_id, "timestamp") do update
                    set consumption_kwh = excluded.consumption_kwh
                """,
                [(args.site_id, ts, value) for ts, value in readings],
            )

            # predictions_log n'a pas de cle naturelle a upserter : on
            # supprime d'abord les predictions qu'on avait generees sur ces
            # memes target_timestamp (grille fixe -> stables d'un run a
            # l'autre), plus tout ce qui precede la fenetre recente (meme
            # justification que pour readings_curated ci-dessus, y compris
            # les predictions d'un run precedent sur une grille differente),
            # pour qu'un rerun ne les empile pas indefiniment.
            target_timestamps = sorted({p[0] for p in predictions})
            cur.execute(
                """
                delete from enervision.predictions_log
                where site_id = %s
                  and (target_timestamp = any(%s) or target_timestamp < %s)
                """,
                (args.site_id, target_timestamps, recent_start),
            )

            cur.executemany(
                """
                insert into enervision.predictions_log
                    (id, site_id, target_timestamp, predicted_consumption_kwh, model_version, generated_at)
                values (%s, %s, %s, %s, %s, %s)
                """,
                [
                    (uuid.uuid4(), args.site_id, target_ts, predicted, version, generated_at)
                    for target_ts, predicted, version, generated_at, _label in predictions
                ],
            )
        conn.commit()

    print("OK — donnees inserees. Le prochain cycle de ModelHealthJob (etl_worker) "
          "publiera les metriques Prometheus correspondantes (ml_prediction_mae_24h, "
          "ml_feature_drift_score, ml_model_version, ml_prediction_mae_by_horizon).")


if __name__ == "__main__":
    main()
