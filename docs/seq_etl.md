## Diagramme de séquence du Worker ETL

### Ingestion temps réel (issue #19)

Implémenté dans `apps/etl_worker` : un scheduler APScheduler interne au
worker (pas de cron externe) boucle toutes les 60 secondes sur tous les
sites retournés par l'API mock, et effectue une écriture double
idempotente avant de publier un événement — voir
[docs/ingestion-worker.md](ingestion-worker.md) pour le détail.

#### Mermaid

```mermaid
sequenceDiagram
    autonumber
    participant Scheduler as APScheduler (interne, 60s)
    participant Worker as Worker ETL
    participant Mock as API Mock EnerVision
    participant PG as PostgreSQL (readings_raw)
    participant MinIO as MinIO (bucket bronze)
    participant Redis as Redis Streams

    loop Toutes les 60 secondes
        Scheduler->>Worker: ingest_all_sites()
        Worker->>Mock: GET /api/v1/sites
        Mock-->>Worker: 200 OK + liste des sites
        loop Pour chaque site
            Worker->>Mock: GET /api/v1/sites/{site_id}/current
            Mock-->>Worker: 200 OK + lecture (raw_payload conservé)
            Worker->>PG: INSERT readings_raw ... ON CONFLICT (site_id, timestamp) DO NOTHING
            PG-->>Worker: inséré / doublon
            alt Nouvellement inséré
                Worker->>MinIO: PUT bronze/{YYYY}/{MM}/{DD}/{HH}/{site_id}_{timestamp}.json
                MinIO-->>Worker: 200 OK
                Worker->>Redis: XADD reading.ingested {site_id, timestamp, data_quality, payload}
            else Doublon (idempotence)
                Note over Worker: Pas de ré-écriture MinIO ni de republication de l'événement
            end
            Worker->>Worker: Log JSON stdout {site, status, data_quality}
        end
    end

    Note over Worker,Redis: Une lecture "critical" (tous les champs de mesure null)<br/>suit exactement le même chemin — jamais filtrée ni écartée
```

### Transformation des données brutes (à venir)

Étape distincte, pas encore implémentée : contrairement au plan initial,
l'ingestion (ci-dessus) écrit déjà directement dans `readings_raw` en
même temps que le JSON brut dans `bronze` — il n'y a pas de job séparé
qui relit MinIO pour peupler Postgres. Ce diagramme reste pertinent pour
un futur retraitement/backfill (ex. DATA-04, imputation) qui relirait le
bucket `bronze` indépendamment de l'ingestion temps réel.

#### Mermaid

```mermaid
sequenceDiagram
    autonumber
    participant Cron as Scheduler (cron 1h)
    participant Worker as Worker ETL
    participant MinIO as MinIO (S3)
    participant PG as PostgreSQL
 
    loop Toutes les heures
        Cron->>Worker: Déclenche le job de transformation
        Worker->>MinIO: GET bronze/{date}/*.json (données brutes en attente)
        MinIO-->>Worker: Fichiers bruts
        Worker->>Worker: Parsing / validation / transformation
        alt Données valides
            Worker->>PG: INSERT INTO readings
            PG-->>Worker: OK
        else Données invalides
            Worker->>Worker: Log erreur + skip
        end
    end
```
