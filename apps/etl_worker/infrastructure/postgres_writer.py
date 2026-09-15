"""Insère les lectures dans readings_raw.

L'idempotence repose sur la contrainte d'unicité (site_id, timestamp) de la
table (voir db/init/002-readings-raw.sql) : un ON CONFLICT DO NOTHING
garantit qu'un redémarrage du worker ne crée jamais de doublon.
"""

import psycopg2
from mockapi_client import EnergyReading

from .config import Config

_INSERT_SQL = """
    INSERT INTO readings_raw (
        site_id, "timestamp", site_type, consumption_kw, consumption_kwh,
        voltage_v, current_a, power_factor, temperature_celsius,
        humidity_percent, null_reasons, data_quality
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (site_id, "timestamp") DO NOTHING
"""


class ReadingsRawWriter:
    """Écrit une EnergyReading dans readings_raw, de façon idempotente."""

    def __init__(self, dsn: str | None = None):
        self._dsn = dsn or Config.DATABASE_URL

    def insert(self, reading: EnergyReading) -> bool:
        """Insère la lecture. Retourne True si une ligne a été créée, False si doublon."""
        conn = psycopg2.connect(self._dsn)
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        _INSERT_SQL,
                        (
                            reading.site_id,
                            reading.timestamp,
                            reading.site_type,
                            reading.consumption_kw,
                            reading.consumption_kwh,
                            reading.voltage_v,
                            reading.current_a,
                            reading.power_factor,
                            reading.temperature_celsius,
                            reading.humidity_percent,
                            reading.null_reasons,
                            reading.data_quality,
                        ),
                    )
                    return cur.rowcount > 0
        finally:
            conn.close()
