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

### Transformation horaire (bronze -> enervision.readings)

Second job APScheduler du même worker (cron, `minute=0`) : relit les
JSON bruts de l'heure précédente dans le bucket bronze et les charge
dans la table structurée `enervision.readings` (servie par core_api),
indépendamment de l'ingestion temps réel qui alimente déjà `readings_raw`.

#### Mermaid

```mermaid
sequenceDiagram
    autonumber
    participant Cron as APScheduler (cron, toutes les heures)
    participant Worker as Worker ETL
    participant Mock as API Mock EnerVision
    participant MinIO as MinIO (bucket bronze)
    participant PG as PostgreSQL (enervision)

    Cron->>Worker: HourlyTransformationJob.run()
    Worker->>Mock: GET /api/v1/sites
    Mock-->>Worker: 200 OK + liste des sites
    Worker->>PG: UPSERT enervision.sites (nécessaire : FK sur site_id)
    PG-->>Worker: OK

    Worker->>MinIO: GET bronze/{YYYY}/{MM}/{DD}/{HH-1}/*.json (heure précédente)
    MinIO-->>Worker: Fichiers bruts

    loop Pour chaque fichier
        Worker->>Worker: Validation Pydantic (EnergyReading), aucune correction de valeur
        alt JSON valide
            Worker->>PG: INSERT enervision.readings ... ON CONFLICT (site_id, timestamp) DO NOTHING
            PG-->>Worker: inséré / doublon
        else JSON invalide
            Worker->>Worker: Log erreur + skip
        end
    end

    Worker->>Worker: Log JSON stdout {job: transform, files, inserted, duplicates, errors}
```
