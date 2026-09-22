"""Genere un historique realiste par site (readings_curated + predictions_log)
pour que le monitoring du modele (drift + MAE, docs/monitoring_model.md)
soit calculable sur les 7 sites sans attendre l'accumulation naturelle.

Remplace backfill_model_health.py + enrich_sensor_readings.py par un seul
passage par site : plus besoin d'une premiere ecriture "plate" suivie d'un
enrichissement, les valeurs realistes (echelle, cycle journalier, capteurs,
pannes) sont generees directement.

Chaque site a un profil concret (type, echelle de consommation, amplitude
du cycle jour/nuit, effet week-end) au lieu d'une courbe generique — voir
SITE_PROFILES. Ces baselines reprennent les ordres de grandeur observes en
conditions reelles pour chaque site (pas de calibrage sur une lecture
existante : ce script part d'une base vide, cf. --wipe-first).

Fenetre temporelle : HISTORY_DAYS jours avant maintenant, pas de 1 minute
(cadence reelle de l'ETL, ETL_POLL_INTERVAL_SECONDS=60), au lieu d'une
grille grossiere (15 min) qui produirait une serie trop reguliere pour
entrainer un modele. HISTORY_DAYS > TRAINING_WINDOW_DAYS (10, cf.
domain/model_health.py) avec une marge, pour que la fenetre d'entrainement
du drift soit entierement couverte.

Une fraction des lectures simule une panne capteur (temperature/humidite/
electrique/consommation, ou perte reseau totale), avec le meme mapping
data_quality que les vraies donnees (0 raison -> good, 1 -> partial,
2-3 -> degraded, network_loss seul -> critical) : ca permet de verifier
l'ecran de suivi des capteurs (/sites) en plus du drift.

Usage :
    python scripts/seed_model_health_data.py --site-id SITE001

Pour repartir d'une base vide (efface TOUT readings_curated/predictions_log,
y compris les vraies donnees) :
    python scripts/seed_model_health_data.py --wipe-all

Necessite psycopg (v3) et un DATABASE_URL (ou --database-url) valide.
"""

import argparse
import math
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from statistics import fmean, pstdev

import psycopg

READING_INTERVAL = timedelta(minutes=1)
TRAINING_WINDOW_DAYS = 10
TRAINED_AT_OFFSET_DAYS = 1
HISTORY_DAYS = TRAINED_AT_OFFSET_DAYS + TRAINING_WINDOW_DAYS  # = 11
RECENT_WINDOW = timedelta(hours=24)
HORIZON_TARGET_WINDOW_DAYS = 7

# (type, echelle kWh, amplitude jour/nuit en fraction de l'echelle, effet
# week-end en fraction de l'echelle, bruit en fraction de l'echelle) — les
# echelles reprennent les ordres de grandeur observes en conditions reelles
# pour chaque site (docs/archi_database.md, sites SITE001-007).
SITE_PROFILES = {
    "SITE001": {"type": "office", "baseline_kwh": 165, "daily_amp": 0.22, "weekend": -0.35, "noise": 0.05},
    "SITE002": {"type": "factory", "baseline_kwh": 900, "daily_amp": 0.15, "weekend": -0.25, "noise": 0.06},
    "SITE003": {"type": "datacenter", "baseline_kwh": 720, "daily_amp": 0.04, "weekend": 0.0, "noise": 0.03},
    "SITE004": {"type": "retail", "baseline_kwh": 320, "daily_amp": 0.45, "weekend": 0.10, "noise": 0.07},
    "SITE005": {"type": "hospital", "baseline_kwh": 480, "daily_amp": 0.10, "weekend": -0.03, "noise": 0.04},
    "SITE006": {"type": "office", "baseline_kwh": 140, "daily_amp": 0.22, "weekend": -0.35, "noise": 0.05},
    "SITE007": {"type": "factory", "baseline_kwh": 820, "daily_amp": 0.15, "weekend": -0.25, "noise": 0.06},
}

# (label, horizon_representatif_en_heures, ecart-type d'erreur simule, en
# fraction de la baseline du site) — l'ecart-type croit avec l'horizon pour
# donner une bande d'erreur qui s'elargit sur le graphique (cf.
# domain/model_health.py HORIZON_BUCKETS).
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

# Proportion de lectures affectees par une panne capteur simulee.
FAILURE_RATE = 0.08

# (raisons possibles, poids) — un "network_loss" isole est plus rare et
# plus grave (tout le capteur est perdu) que les pannes partielles.
FAILURE_SCENARIOS = [
    (["temperature_sensor_failure"], 30),
    (["humidity_sensor_failure"], 30),
    (["electrical_sensor_failure"], 15),
    (["consumption_sensor_failure"], 15),
    (["electrical_sensor_failure", "temperature_sensor_failure"], 5),
    (["electrical_sensor_failure", "humidity_sensor_failure"], 5),
    (["temperature_sensor_failure", "humidity_sensor_failure"], 4),
    (["network_loss"], 3),
]


def floor_to_interval(dt: datetime, interval: timedelta) -> datetime:
    """Aligne `dt` sur une grille fixe (epoque UTC) de pas `interval`, pour
    que deux executions du script a des instants differents produisent les
    memes timestamps (upsert propre, et marqueur fiable pour distinguer ces
    lignes des vraies lors d'un nettoyage — cf. main())."""
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    seconds = (dt - epoch).total_seconds()
    floored = (seconds // interval.total_seconds()) * interval.total_seconds()
    return epoch + timedelta(seconds=floored)


def data_quality_for(reasons: list[str]) -> str:
    if reasons == ["network_loss"]:
        return "critical"
    if len(reasons) == 0:
        return "good"
    if len(reasons) == 1:
        return "partial"
    return "degraded"


def pick_failure_reasons() -> list[str]:
    reasons_list, weights = zip(*FAILURE_SCENARIOS)
    return list(random.choices(reasons_list, weights=weights, k=1)[0])


def consumption_at(t: datetime, profile: dict, mean_offset: float) -> float:
    """Valeur de consommation simulee : cycle journalier + effet week-end +
    bruit, aux amplitudes propres au profil du site (un datacenter est
    quasi plat, un commerce a un pic marque en journee, etc.), plus un
    decalage optionnel (utilise pour la fenetre 'recente' afin de simuler
    un drift)."""
    baseline = profile["baseline_kwh"]
    hour = t.hour + t.minute / 60
    daily = profile["daily_amp"] * baseline * math.sin((hour - 6) / 24 * 2 * math.pi)
    weekend = profile["weekend"] * baseline if t.weekday() >= 5 else 0.0
    noise = random.gauss(0, profile["noise"] * baseline)
    return max(0.0, baseline + mean_offset + daily + weekend + noise)


def build_sensor_fields(consumption_kwh: float) -> dict:
    """Tension/courant/cos phi/temperature/humidite realistes, correlees a
    `consumption_kwh` (cf. enrich_sensor_readings.py, meme formule
    triphasee), sans panne (appliquee ensuite si tiree au sort)."""
    power_factor = round(random.uniform(0.85, 0.99), 3)
    voltage_v = round(400 + random.gauss(0, 8), 1)
    current_a = round((consumption_kwh * 1000) / (math.sqrt(3) * voltage_v * power_factor), 2)
    return {
        "voltage_v": voltage_v,
        "current_a": current_a,
        "power_factor": power_factor,
    }


def build_readings(now: datetime, trained_at: datetime, profile: dict, drift_offset_std: float):
    history_start = floor_to_interval(now - timedelta(days=HISTORY_DAYS), READING_INTERVAL)
    recent_start = floor_to_interval(now - RECENT_WINDOW, READING_INTERVAL)
    trained_at = floor_to_interval(trained_at, READING_INTERVAL)

    # Phase 1 : fenetre d'entrainement, sans decalage — sert de reference
    # pour calibrer l'ampleur du drift simule sur la fenetre recente.
    training_readings = []
    t = history_start
    while t < trained_at:
        training_readings.append((t, consumption_at(t, profile, mean_offset=0.0)))
        t += READING_INTERVAL

    training_mean = fmean(v for _, v in training_readings)
    training_std = pstdev(v for _, v in training_readings) or (profile["noise"] * profile["baseline_kwh"])
    recent_offset = drift_offset_std * training_std

    # Phase 2 : de trained_at a maintenant, avec le decalage de drift
    # applique uniquement aux RECENT_WINDOW (24h) les plus recentes.
    rest_readings = []
    t = trained_at
    while t <= now:
        offset = recent_offset if t >= recent_start else 0.0
        rest_readings.append((t, consumption_at(t, profile, mean_offset=offset)))
        t += READING_INTERVAL

    all_readings = training_readings + rest_readings
    return all_readings, training_mean, training_std, recent_offset


def apply_sensor_quality(t: datetime, consumption_kwh: float) -> dict:
    """Combine consumption_kwh avec des champs capteurs realistes, et tire
    au sort une panne (cf. FAILURE_RATE/FAILURE_SCENARIOS) — memes regles
    que les vraies donnees (voir readings_curated en base)."""
    fields = build_sensor_fields(consumption_kwh)
    reasons: list[str] = []
    if random.random() < FAILURE_RATE:
        reasons = pick_failure_reasons()

    quality = data_quality_for(reasons)
    imputation_methods = None
    voltage_v, current_a, power_factor = fields["voltage_v"], fields["current_a"], fields["power_factor"]
    temperature_celsius = round(16 + 8 * math.sin((t.hour - 9) / 24 * 2 * math.pi) + random.gauss(0, 1.5), 1)
    humidity_percent = round(50 + 10 * math.sin((t.hour - 15) / 24 * 2 * math.pi) + random.gauss(0, 4), 1)

    if "network_loss" in reasons:
        voltage_v = current_a = power_factor = None
        temperature_celsius = humidity_percent = None
        imputation_methods = "forward_fill"
    else:
        if "electrical_sensor_failure" in reasons:
            voltage_v = current_a = power_factor = None
        if "temperature_sensor_failure" in reasons:
            temperature_celsius = None
        if "humidity_sensor_failure" in reasons:
            humidity_percent = None
        if "consumption_sensor_failure" in reasons:
            imputation_methods = "forward_fill"

    return {
        "consumption_kw": consumption_kwh,
        "voltage_v": voltage_v,
        "current_a": current_a,
        "power_factor": power_factor,
        "temperature_celsius": temperature_celsius,
        "humidity_percent": humidity_percent,
        "imputation_methods": imputation_methods,
        "null_reasons": reasons,
        "data_quality": quality,
    }


def build_predictions(readings: list[tuple[datetime, float]], now: datetime, profile: dict, model_version: str):
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

        error_std = error_std_fraction * profile["baseline_kwh"]
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
    profile = SITE_PROFILES.get(site_id)
    if profile is None:
        raise SystemExit(f"Site inconnu : {site_id} (attendu un de {sorted(SITE_PROFILES)})")

    now = datetime.now(timezone.utc).replace(microsecond=0)
    trained_at = now - timedelta(days=TRAINED_AT_OFFSET_DAYS)
    model_version = trained_at.strftime("%Y-%m-%dT%H-%M-%SZ")

    readings, training_mean, training_std, recent_offset = build_readings(
        now, trained_at, profile, drift_offset_std
    )
    predictions = build_predictions(readings, now, profile, model_version)

    print(f"site_id            : {site_id} ({profile['type']}, echelle {profile['baseline_kwh']} kWh)")
    print(f"model_version      : {model_version} (trained_at = now - {TRAINED_AT_OFFSET_DAYS}j)")
    print(f"readings generees  : {len(readings)} (sur {HISTORY_DAYS} jours, pas 1 min)")
    print(f"predictions generees : {len(predictions)}")
    print(f"training mean/std  : {training_mean:.2f} / {training_std:.2f} kWh")
    print(f"decalage recent    : +{recent_offset:.2f} kWh (~{drift_offset_std}x std entrainement)")

    with conn.cursor() as cur:
        # Nettoie un run precedent de CE script pour ce site (jamais les
        # vraies donnees : l'horodatage brut de l'API mock n'est ~jamais
        # pile a la seconde/microseconde pres).
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

        rows = []
        for ts, consumption_kwh in readings:
            enriched = apply_sensor_quality(ts, consumption_kwh)
            rows.append(
                (
                    site_id,
                    ts,
                    profile["type"],
                    enriched["consumption_kw"],
                    consumption_kwh,
                    enriched["voltage_v"],
                    enriched["current_a"],
                    enriched["power_factor"],
                    enriched["temperature_celsius"],
                    enriched["humidity_percent"],
                    enriched["imputation_methods"],
                    enriched["null_reasons"],
                    enriched["data_quality"],
                )
            )

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
            # curated_at = timestamp de la mesure elle-meme (pas l'instant
            # d'execution du script) : sans ca, server_default=now() donne
            # la meme valeur a toutes les lignes d'une transaction (now()
            # est fige au debut de la transaction sous Postgres), ce qui
            # ferait croire que tout a ete "curated" au meme instant plutot
            # qu'etale sur la semaine ecoulee.
            [(*row, row[1]) for row in rows],
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
    parser.add_argument(
        "--site-id",
        action="append",
        dest="site_ids",
        help="Site a generer (repetable). Par defaut : tous les sites de SITE_PROFILES.",
    )
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
    parser.add_argument(
        "--wipe-all",
        action="store_true",
        help="Vide entierement readings_curated et predictions_log avant de generer "
        "(TOUTES les donnees, y compris les vraies) — a utiliser en connaissance de cause.",
    )
    args = parser.parse_args()
    random.seed(args.seed)

    database_url = args.database_url or os.environ.get(
        "DATABASE_URL", "postgresql://enervision:changeme@localhost:5432/enervision"
    )
    database_url = database_url.replace("postgresql+psycopg://", "postgresql://")

    site_ids = args.site_ids or sorted(SITE_PROFILES)

    with psycopg.connect(database_url, autocommit=False) as conn:
        if args.wipe_all:
            wipe_all(conn)

        for site_id in site_ids:
            seed_site(conn, site_id, args.drift_offset_std)

    print(
        "OK — donnees inserees pour",
        ", ".join(site_ids),
        "— le prochain cycle de ModelHealthJob (etl_worker) publiera les metriques "
        "Prometheus correspondantes (ml_prediction_mae_24h, ml_feature_drift_score, "
        "ml_model_version, ml_prediction_mae_by_horizon).",
    )


if __name__ == "__main__":
    main()
