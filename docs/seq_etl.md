## Diagramme de séquence du Worker ETL

### Ingestion des données brutes avec détection d'alertes temps réel (Redis Streams)

#### Mermaid

```mermaid
sequenceDiagram
    autonumber
    participant Cron as Scheduler (cron 1 min)
    participant Worker as Worker ETL
    participant Mock as API Mock EnerVision
    participant MinIO as MinIO (S3)
    participant Redis as Redis Streams

    loop Toutes les minutes
        Cron->>Worker: Déclenche le job ETL
        Worker->>Mock: GET /api/v1/readings?start_time={start_date}&end_time={end_date}&limit=7 (dernières données)
        Mock-->>Worker: 200 OK + données brutes (JSON)
        Worker->>MinIO: PUT raw/{date}/{site_id}.json
        MinIO-->>Worker: 200 OK
        alt data_quality == "critical" ou seuil dépassé
            Worker->>Redis: XADD alert.detected {site_id, timestamp, data_quality}
        end
    end

    Note over Worker,MinIO: Données brutes conservées telles quelles (traçabilité),<br/>avant toute transformation
    Note over Worker,Redis: Détection à la minute, indépendante du job<br/>de transformation horaire (qui reste inchangé)
```

### Transformation des données brutes

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
        Worker->>MinIO: GET raw/{date}/*.json (données brutes en attente)
        MinIO-->>Worker: Fichiers bruts
        Worker->>Worker: Parsing / validation / transformation
        alt Données valides
            Worker->>PG: INSERT INTO consumption_readings
            PG-->>Worker: OK
        else Données invalides
            Worker->>Worker: Log erreur + skip
        end
    end
```
