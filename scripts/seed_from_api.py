"""Variante de seed_model_health_data.py qui recupere les lectures depuis
la VRAIE API mock EnerVision (GET /api/v1/readings) au lieu d'inventer une
courbe de consommation — les valeurs (et les pannes capteur simulees par
l'API elle-meme) sont donc directement "concretes" par site, pas une
approximation maison.

predictions_log reste synthetique (l'API mock ne fournit pas d'historique
de PREDICTIONS, seulement de mesures) : les predictions sont generees en
ajoutant un bruit croissant avec l'horizon aux vraies valeurs recuperees,
memes conventions que seed_model_health_data.py (HORIZON_PROFILE).

L'API limite chaque appel a 1000 points (voir openapi.json) ; on decoupe
donc la fenetre demandee en tranches de ~1000 minutes (~16h40) pour obtenir
un point par minute sur toute la periode.

Usage :
    python scripts/seed_from_api.py --site-id SITE001
    python scripts/seed_from_api.py --wipe-all   # tous les sites, base vide avant
"""

import argparse
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from statistics import fmean, pstdev

import psycopg
import requests

API_BASE_URL = "https://api-mock.charlieandre.fr"
API_AUTH = ("projet_eadl", "projet_eadl140926250926")
API_MAX_LIMIT = 1000

READING_INTERVAL = timedelta(minutes=1)
TRAINING_WINDOW_DAYS = 10
TRAINED_AT_OFFSET_DAYS = 1
HISTORY_DAYS = TRAINED_AT_OFFSET_DAYS + TRAINING_WINDOW_DAYS  # = 11
RECENT_WINDOW = timedelta(hours=24)
HORIZON_TARGET_WINDOW_DAYS = 7

SITE_IDS = ["SITE001", "SITE002", "SITE003", "SITE004", "SITE005", "SITE006", "SITE007"]

# (label, horizon_representatif_en_heures, ecart-type d'erreur simule, en
# fraction de la moyenne de consommation du site) — cf. seed_model_health_data.py.
HORIZON_PROFILE = [
    ("0-1h", 0.5, 0.03),
    ("1-3h", 2.0, 0.05),
    ("3-6h", 4.5, 0.08),
    ("6-12h", 9.0, 0.12),
    ("12-24h", 18.0, 0.16),
    ("1-3j", 48.0, 0.20),
    ("3-7j", 120.0, 0.25),
]
PREDICTIONS_PER_BUCKET = 8


def floor_to_interval(dt: datetime, interval: timedelta) -> datetime:
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    seconds = (dt - epoch).total_seconds()
    floored = (seconds // interval.total_seconds()) * interval.total_seconds()
    return epoch + timedelta(seconds=floored)


def fetch_readings(site_id: str, start: datetime, end: datetime) -> list[dict]:
    """Recupere l'historique reel du mock, en decoupant en tranches de
    API_MAX_LIMIT minutes (limite de l'API) pour obtenir ~1 point/minute
    sur toute la periode [start, end]."""
    readings: list[dict] = []
    chunk = timedelta(minutes=API_MAX_LIMIT)
    chunk_start = start

    while chunk_start < end:
        chunk_end = min(chunk_start + chunk, end)
        response = requests.get(
            f"{API_BASE_URL}/api/v1/readings",
            auth=API_AUTH,
            params={
                "site_id": site_id,
                "start_time": chunk_start.strftime("%Y-%m-%dT%H:%M:%S"),
                "end_time": chunk_end.strftime("%Y-%m-%dT%H:%M:%S"),
                "limit": API_MAX_LIMIT,
            },
            timeout=30,
        )
        response.raise_for_status()
        readings.extend(response.json())
        chunk_start = chunk_end

    return readings


def forward_fill_consumption(readings: list[dict]) -> None:
    """Meme contrat que apps/etl_worker/domain/imputation.py : seul
    consumption_kw(h) est reconstitue (valeur precedente connue), les
    autres champs capteur restent NULL en cas de panne. Modifie `readings`
    en place, ajoute la cle 'imputation_methods'."""
    last_kw = last_kwh = None
    for row in readings:
        row["imputation_methods"] = None
        if row["consumption_kw"] is None or row["consumption_kwh"] is None:
            if last_kw is not None:
                row["consumption_kw"] = last_kw
                row["consumption_kwh"] = last_kwh
                row["imputation_methods"] = "forward_fill"
            else:
                row["imputation_methods"] = "no_history"
        else:
            last_kw = row["consumption_kw"]
            last_kwh = row["consumption_kwh"]


def apply_drift_offset(readings: list[dict], now: datetime, drift_offset_std: float) -> tuple[float, float, float]:
    """Decale la moyenne de consumption_kwh sur RECENT_WINDOW (24h) d'un
    multiple de l'ecart-type de la fenetre d'entrainement, pour que
    ml_feature_drift_score soit non nul (cf. domain/model_health.py
    compute_drift_score) — sans ca, des donnees reelles "normales" ne
    montrent jamais de derive a demontrer."""
    recent_start = floor_to_interval(now - RECENT_WINDOW, READING_INTERVAL)
    training_end = recent_start

    training_values = [
        r["consumption_kwh"]
        for r in readings
        if r["consumption_kwh"] is not None and r["timestamp"] < training_end
    ]
    training_mean = fmean(training_values) if training_values else 0.0
    training_std = pstdev(training_values) if len(training_values) > 1 else max(training_mean * 0.1, 1.0)
    offset = drift_offset_std * training_std

    for row in readings:
        if row["timestamp"] >= recent_start and row["consumption_kwh"] is not None:
            row["consumption_kwh"] += offset
            row["consumption_kw"] += offset

    return training_mean, training_std, offset


def build_predictions(readings: list[dict], now: datetime, mean_consumption: float, model_version: str):
    by_ts = {r["timestamp"]: r["consumption_kwh"] for r in readings if r["consumption_kwh"] is not None}
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

        error_std = error_std_fraction * mean_consumption
        for target_ts in targets:
            actual = by_ts[target_ts]
            predicted = max(0.0, actual + random.gauss(0, error_std))
            generated_at = target_ts - timedelta(hours=horizon_hours)
            predictions.append((target_ts, predicted, model_version, generated_at, label))

    return predictions


def wipe_all(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("delete from enervision.predictions_log")
        print(f"predictions_log videe ({cur.rowcount} lignes)")
        cur.execute("delete from enervision.readings_curated")
        print(f"readings_curated videe ({cur.rowcount} lignes)")
    conn.commit()


def seed_site(conn, site_id: str, drift_offset_std: float) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    start = floor_to_interval(now - timedelta(days=HISTORY_DAYS), READING_INTERVAL)
    trained_at = now - timedelta(days=TRAINED_AT_OFFSET_DAYS)
    model_version = trained_at.strftime("%Y-%m-%dT%H-%M-%SZ")

    print(f"site_id            : {site_id} — recuperation depuis {API_BASE_URL} ...")
    raw = fetch_readings(site_id, start, now)
    for row in raw:
        row["timestamp"] = floor_to_interval(
            datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")), READING_INTERVAL
        )

    forward_fill_consumption(raw)
    training_mean, training_std, offset = apply_drift_offset(raw, now, drift_offset_std)

    mean_consumption = fmean(r["consumption_kwh"] for r in raw if r["consumption_kwh"] is not None)
    predictions = build_predictions(raw, now, mean_consumption, model_version)

    print(f"lectures recuperees : {len(raw)} (sur {HISTORY_DAYS} jours, ~1 point/min)")
    print(f"predictions generees : {len(predictions)}")
    print(f"training mean/std  : {training_mean:.2f} / {training_std:.2f} kWh")
    print(f"decalage recent    : +{offset:.2f} kWh (~{drift_offset_std}x std entrainement)")

    with conn.cursor() as cur:
        cur.execute(
            """
            delete from enervision.readings_curated
            where site_id = %s
              and extract(second from "timestamp") = 0
              and extract(microsecond from "timestamp") = 0
            """,
            (site_id,),
        )
        cur.execute(
            """
            delete from enervision.predictions_log
            where site_id = %s
              and extract(second from target_timestamp) = 0
              and extract(microsecond from target_timestamp) = 0
            """,
            (site_id,),
        )

        rows = [
            (
                r["site_id"],
                r["timestamp"],
                r["site_type"],
                r["consumption_kw"],
                r["consumption_kwh"],
                r["voltage_v"],
                r["current_a"],
                r["power_factor"],
                r["temperature_celsius"],
                r["humidity_percent"],
                r["imputation_methods"],
                r["null_reasons"],
                r["data_quality"],
                r["timestamp"],  # curated_at = timestamp de la mesure, pas l'instant du script
            )
            for r in raw
        ]

        cur.executemany(
            """
            insert into enervision.readings_curated
                (site_id, "timestamp", site_type, consumption_kw, consumption_kwh,
                 voltage_v, current_a, power_factor, temperature_celsius,
                 humidity_percent, imputation_methods, null_reasons, data_quality,
                 curated_at)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (site_id, "timestamp") do update set
                site_type = excluded.site_type,
                consumption_kw = excluded.consumption_kw,
                consumption_kwh = excluded.consumption_kwh,
                voltage_v = excluded.voltage_v,
                current_a = excluded.current_a,
                power_factor = excluded.power_factor,
                temperature_celsius = excluded.temperature_celsius,
                humidity_percent = excluded.humidity_percent,
                imputation_methods = excluded.imputation_methods,
                null_reasons = excluded.null_reasons,
                data_quality = excluded.data_quality,
                curated_at = excluded.curated_at
            """,
            rows,
        )

        cur.executemany(
            """
            insert into enervision.predictions_log
                (id, site_id, target_timestamp, predicted_consumption_kwh, model_version, generated_at)
            values (%s, %s, %s, %s, %s, %s)
            """,
            [
                (uuid.uuid4(), site_id, target_ts, predicted, version, generated_at)
                for target_ts, predicted, version, generated_at, _label in predictions
            ],
        )
    conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--site-id", action="append", dest="site_ids", help="Repetable. Par defaut : les 7 sites.")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--drift-offset-std", type=float, default=1.3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--wipe-all", action="store_true")
    args = parser.parse_args()
    random.seed(args.seed)

    database_url = args.database_url or os.environ.get(
        "DATABASE_URL", "postgresql://enervision:changeme@localhost:5432/enervision"
    )
    database_url = database_url.replace("postgresql+psycopg://", "postgresql://")

    site_ids = args.site_ids or SITE_IDS

    with psycopg.connect(database_url, autocommit=False) as conn:
        if args.wipe_all:
            wipe_all(conn)

        for site_id in site_ids:
            seed_site(conn, site_id, args.drift_offset_std)

    print(
        "OK — donnees inserees pour", ", ".join(site_ids),
        "— le prochain cycle de ModelHealthJob (etl_worker) publiera les metriques Prometheus.",
    )


if __name__ == "__main__":
    main()
