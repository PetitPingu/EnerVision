"""Enrichit les lectures synthetiques inserees par backfill_model_health.py
avec les autres champs capteurs (voltage/courant/cos phi/temperature/
humidite), et simule des pannes capteur sur une fraction des lignes pour
verifier le pipeline de data_quality (good/partial/degraded/critical).

Ne touche qu'aux lignes que backfill_model_health.py a creees : celles-ci
sont reconnaissables sans ambiguite (data_quality='good' avec voltage_v
NULL — une vraie lecture "good" a toujours tous ses champs capteur
renseignes, cf. readings_curated en provenance de l'API mock).

Conventions reprises des vraies donnees (voir readings_curated en base) :
  - 0 raison de nullite  -> data_quality "good"
  - 1 raison             -> "partial"
  - 2-3 raisons          -> "degraded"
  - ["network_loss"]     -> "critical" (tous les champs capteur a NULL)
  - "consumption_sensor_failure"/"network_loss" -> consumption_kw(h) reste
    renseigne (imputation_methods="forward_fill"), jamais NULL.

Usage :
    python scripts/enrich_sensor_readings.py --site-id SITE001
"""

import argparse
import math
import os
import random

import psycopg

SITE_TYPES = {
    "SITE001": "office",
    "SITE002": "factory",
    "SITE003": "datacenter",
    "SITE004": "retail",
    "SITE005": "hospital",
    "SITE006": "office",
    "SITE007": "factory",
}

# Proportion de lignes affectees par une panne capteur simulee.
FAILURE_RATE = 0.10

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


def build_row(site_type: str, timestamp, consumption_kwh: float) -> dict:
    hour = timestamp.hour + timestamp.minute / 60
    power_factor = round(random.uniform(0.85, 0.99), 3)
    voltage_v = round(400 + random.gauss(0, 8), 1)
    # Puissance triphasee : P(kW) = sqrt(3) * V * I * cos(phi) / 1000
    current_a = round((consumption_kwh * 1000) / (math.sqrt(3) * voltage_v * power_factor), 2)
    temperature_celsius = round(16 + 8 * math.sin((hour - 9) / 24 * 2 * math.pi) + random.gauss(0, 1.5), 1)
    humidity_percent = round(50 + 10 * math.sin((hour - 15) / 24 * 2 * math.pi) + random.gauss(0, 4), 1)

    reasons: list[str] = []
    if random.random() < FAILURE_RATE:
        reasons = pick_failure_reasons()

    quality = data_quality_for(reasons)
    imputation_methods = None
    consumption_kw = consumption_kwh

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
        "site_type": site_type,
        "consumption_kw": consumption_kw,
        "voltage_v": voltage_v,
        "current_a": current_a,
        "power_factor": power_factor,
        "temperature_celsius": temperature_celsius,
        "humidity_percent": humidity_percent,
        "imputation_methods": imputation_methods,
        "null_reasons": reasons,
        "data_quality": quality,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--site-id", default="SITE001")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    random.seed(args.seed)

    database_url = args.database_url or os.environ.get(
        "DATABASE_URL", "postgresql://enervision:changeme@localhost:5432/enervision"
    )
    database_url = database_url.replace("postgresql+psycopg://", "postgresql://")
    site_type = SITE_TYPES.get(args.site_id, "office")

    with psycopg.connect(database_url, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select site_id, "timestamp", consumption_kwh
                from enervision.readings_curated
                where site_id = %s and data_quality = 'good' and voltage_v is null
                """,
                (args.site_id,),
            )
            rows = cur.fetchall()

            updates = []
            quality_counts: dict[str, int] = {}
            for site_id, timestamp, consumption_kwh in rows:
                enriched = build_row(site_type, timestamp, consumption_kwh or 0.0)
                quality_counts[enriched["data_quality"]] = quality_counts.get(enriched["data_quality"], 0) + 1
                updates.append(
                    (
                        enriched["site_type"],
                        enriched["consumption_kw"],
                        enriched["voltage_v"],
                        enriched["current_a"],
                        enriched["power_factor"],
                        enriched["temperature_celsius"],
                        enriched["humidity_percent"],
                        enriched["imputation_methods"],
                        enriched["null_reasons"],
                        enriched["data_quality"],
                        site_id,
                        timestamp,
                    )
                )

            cur.executemany(
                """
                update enervision.readings_curated
                set site_type = %s,
                    consumption_kw = %s,
                    voltage_v = %s,
                    current_a = %s,
                    power_factor = %s,
                    temperature_celsius = %s,
                    humidity_percent = %s,
                    imputation_methods = %s,
                    null_reasons = %s,
                    data_quality = %s
                where site_id = %s and "timestamp" = %s
                """,
                updates,
            )
        conn.commit()

    print(f"site_id       : {args.site_id} ({site_type})")
    print(f"lignes enrichies : {len(rows)}")
    print(f"repartition data_quality : {quality_counts}")


if __name__ == "__main__":
    main()
