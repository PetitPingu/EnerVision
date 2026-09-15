-- Table d'atterrissage des lectures transformées par le worker ETL
-- (voir docs/seq_etl.md). La clé primaire (site_id, timestamp) porte
-- l'idempotence : un INSERT ... ON CONFLICT (site_id, timestamp) DO
-- NOTHING ne crée jamais de doublon, y compris après redémarrage.

CREATE TABLE IF NOT EXISTS consumption_readings (
    site_id TEXT NOT NULL,
    "timestamp" TIMESTAMPTZ NOT NULL,
    site_type TEXT NOT NULL,
    consumption_kw DOUBLE PRECISION,
    consumption_kwh DOUBLE PRECISION,
    voltage_v DOUBLE PRECISION,
    current_a DOUBLE PRECISION,
    power_factor DOUBLE PRECISION,
    temperature_celsius DOUBLE PRECISION,
    humidity_percent DOUBLE PRECISION,
    null_reasons TEXT[] NOT NULL DEFAULT '{}',
    data_quality TEXT NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (site_id, "timestamp")
);

SELECT create_hypertable('consumption_readings', 'timestamp', if_not_exists => TRUE);
