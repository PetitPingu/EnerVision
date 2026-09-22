## Diagramme de séquence du Worker ETL

Implémenté dans `apps/etl_worker` : un seul job planifié (`EtlJob`,
`application/etl_job.py`), toutes les `ETL_POLL_INTERVAL_SECONDS` secondes
(60s par défaut, soit une minute). Pas de job séparé pour la
transformation — ingestion et curation se font dans le même passage,
lecture par lecture, sans jamais relire MinIO après coup.

### Mermaid

```mermaid
sequenceDiagram
    autonumber
    participant Cron as Scheduler (cron 1 min)
    participant Worker as Worker ETL (EtlJob)
    participant Mock as API Mock EnerVision
    participant MinIO as MinIO (S3, bucket raw)
    participant Impute as domain/imputation.py<br/>(ConsumptionKwhImputer, en mémoire)
    participant DB as Postgres (readings_curated)

    loop Toutes les minutes
        Cron->>Worker: Déclenche le job
        Worker->>Mock: GET /api/v1/readings?limit=7 (dernières données)
        Mock-->>Worker: 200 OK + données brutes (JSON)
        loop Pour chaque lecture
            Worker->>MinIO: PUT raw/{site_id}/{YYYY}/{MM}/{DD}/{HH}/{minutes}.json
            MinIO-->>Worker: 200 OK
            Worker->>Impute: impute(site_id, consumption_kwh)
            Impute-->>Worker: (valeur retenue, méthode)
        end
        Worker->>DB: UPSERT readings_curated (7 lignes, site_id + timestamp)
        DB-->>Worker: OK
    end

    Note over Worker,MinIO: Données brutes conservées telles quelles (traçabilité),<br/>avant toute transformation. Toutes les valeurs exceptées good suivent le même chemin.
```
