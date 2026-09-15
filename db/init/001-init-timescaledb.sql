-- Foundation setup for the EnerVision TimescaleDB instance.
-- Application-specific schemas/hypertables belong in later, dedicated migrations.

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE SCHEMA IF NOT EXISTS enervision;
