## Diagramme de séquence du Worker ETL

### Cycle ETL complet : ingestion, transformation et détection d'alertes

Un seul worker, un seul job planifié (toutes les minutes) : ingestion,
insertion en base et détection d'alerte se font dans le même cycle,
plutôt que sur deux jobs séparés (ingestion 1 min / transformation 1h).

#### Mermaid

```mermaid
sequenceDiagram
    autonumber
    participant Cron as Scheduler (cron 1 min)
    participant Worker as Worker ETL
    participant Mock as API Mock EnerVision
    participant MinIO as MinIO (S3)
    participant PG as PostgreSQL
    participant Redis as Redis Streams

    loop Toutes les minutes
        Cron->>Worker: Déclenche le job ETL
        Worker->>Mock: GET /api/v1/readings?start_time={start_date}&end_time={end_date}&limit=7
        Mock-->>Worker: 200 OK + données brutes (JSON)

        loop Pour chaque lecture
            Worker->>MinIO: PUT raw/{date}/{site_id}_{timestamp}.json
            MinIO-->>Worker: 200 OK
            Worker->>PG: INSERT INTO consumption_readings ... ON CONFLICT DO NOTHING
            PG-->>Worker: OK
            alt data_quality == "critical"
                Worker->>Redis: XADD alert.detected {site_id, timestamp, data_quality}
            end
        end
    end

    Note over Worker,PG: Chaque étape (MinIO, PG, Redis) est isolée : une panne<br/>d'une des trois ne bloque jamais les autres, ni le cycle suivant
    Note over Worker,MinIO: Une lecture "critical" (tous les champs de mesure null)<br/>suit le même chemin — jamais filtrée ni corrigée
```
