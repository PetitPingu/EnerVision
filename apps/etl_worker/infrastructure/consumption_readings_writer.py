"""Insère les lectures transformées dans consumption_readings.

Idempotence via la contrainte (site_id, timestamp) : un ON CONFLICT DO
NOTHING garantit qu'une ré-exécution du job de transformation ne crée
jamais de doublon.
"""

import psycopg2
from mockapi_client import EnergyReading

from .config import Config

_INSERT_SQL = """
    INSERT INTO consumption_readings (
        site_id, "timestamp", site_type, consumption_kw, consumption_kwh,
        voltage_v, current_a, power_factor, temperature_celsius,
        humidity_percent, null_reasons, data_quality
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (site_id, "timestamp") DO NOTHING
"""


class ConsumptionReadingsWriter:
    """Écrit une EnergyReading dans consumption_readings, de façon idempotente."""

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
