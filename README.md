# EnerVision

## Stockage

Le détail du socle de stockage (TimescaleDB + MinIO) est décrit dans
[docs/data-storage.md](docs/data-storage.md).

## Ingestion temps réel

Le worker de polling des sites (readings_raw + bucket bronze + Redis
Streams) est décrit dans [docs/ingestion-worker.md](docs/ingestion-worker.md).
