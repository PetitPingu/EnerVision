# EnerVision

## Stockage

Le détail du socle de stockage (TimescaleDB + MinIO) est décrit dans
[docs/data-storage.md](docs/data-storage.md).

## Ingestion temps réel

Le worker de polling des sites (bucket raw + consumption_readings)
est décrit dans [docs/ingestion-worker.md](docs/ingestion-worker.md).

## Monitoring

Le monitoring infra (Prometheus + Grafana) est décrit dans
[docs/monitoring.md](docs/monitoring.md).

## Test de charge

Le scénario Locust sur `core_api` et son intégration CI sont décrits dans
[docs/load-testing.md](docs/load-testing.md).
