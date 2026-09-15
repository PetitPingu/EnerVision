## Diagramme de séquence du Worker ETL

### Ingestion des données brutes

Implémenté dans `apps/etl_worker` : ce worker se limite à l'ingestion —
récupérer les dernières lectures et les déposer brutes dans MinIO.
L'insertion en base (`consumption_readings`) et la détection d'alerte
Redis sont traitées dans une branche séparée dédiée à la transformation.

#### Mermaid

```mermaid
sequenceDiagram
    autonumber
    participant Cron as Scheduler (cron 1 min)
    participant Worker as Worker ETL
    participant Mock as API Mock EnerVision
    participant MinIO as MinIO (S3)

    loop Toutes les minutes
        Cron->>Worker: Déclenche le job ETL
        Worker->>Mock: GET /api/v1/readings?start_time={start_date}&end_time={end_date}&limit=7 (dernières données)
        Mock-->>Worker: 200 OK + données brutes (JSON)
        loop Pour chaque lecture
            Worker->>MinIO: PUT raw/{site_id}/{YYYY}/{MM}/{DD}/{HH}/{minutes}.json
            MinIO-->>Worker: 200 OK
        end
    end

    Note over Worker,MinIO: Données brutes conservées telles quelles (traçabilité),<br/>avant toute transformation. Une lecture "critical" suit le même chemin.
```
