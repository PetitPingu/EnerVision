## 1. Architecture infrastructure

Le système est déployé sur une seule VM on-premise mise à disposition par l'école, via Docker Compose. Six services applicatifs, une base relationnelle et un stockage objet compatible S3 tournent dans le même réseau Docker.

### Services :

Core API (FastAPI) - point d'entrée pour le dashboard, agrège les appels vers Prediction et Recommendation.
Recommendation (FastAPI) - règles à seuils, consomme les prédictions.
Prediction (FastAPI) - sert le modèle prédictif, expose la route /predict qui lit un modèle gardé en mémoire (rechargé toutes les 24h). Un cron interne (APScheduler) réentraîne le modèle sur l'historique Postgres, log le run et enregistre le modèle dans MLflow, puis recharge la version "Production" en mémoire.
Worker ETL (async) - au lieu d'un déclenchement externe managé par le cloud, c'est un processus qui tourne en continu dans son propre conteneur, avec un seul job planifié (APScheduler interne, toutes les 60s) qui ingère les dernières lectures et les dépose brutes dans le bucket `raw`, charge `readings_curated`, et détecte les transitions data_quality (publiées sur Redis Streams) — voir [seq_etl.md](seq_etl.md) et [ingestion-worker.md](ingestion-worker.md). Il n'expose pas d'endpoint HTTP - ce n'est pas une API, c'est un worker.
MLflow (Tracking + Model Registry) - trace les entraînements (paramètres, métriques) et versionne les modèles produits par Prediction ; interrogé uniquement par ce dernier, avec une UI exposée pour le suivi et la démonstration.
Dashboard (Next.js/React).

### Stockage :

PostgreSQL pour les données structurées (sites, relevés, prédictions, recommandations) et pour le backend store de MLflow (runs, métriques, registre des versions) dans un schéma dédié - pas de base supplémentaire à opérer.
MinIO pour le data lake brut (bucket `raw`, un fichier JSON par lecture, jamais écrasé) et pour l'artifact store de MLflow (fichiers de modèles entraînés) - équivalent S3 auto-hébergé, API compatible S3 donc le code d'accès (SDK boto3 côté Python) ne change pas si un jour on migre vers un vrai S3.
Redis (Streams) pour la détection d'alertes en quasi temps réel : `etl_worker` publie un événement `alert.detected` sur chaque **transition** de `data_quality` (entrée/sortie de `degraded`/`critical`, pas à chaque lecture — voir [ingestion-worker.md](ingestion-worker.md)), lu par `core_api` en `XREAD` simple (pas de consumer group : diffusion à tous les clients SSE connectés, pas de répartition de charge) et exposé au dashboard via SSE (`GET /api/v1/alerts/stream`).

Secrets : pas de Secrets Manager. En local, chaque service lit un .env (jamais commité, .env.example versionné pour le contenu attendu). En "prod" (la VM école), les valeurs sont stockées comme GitHub Secrets et injectées via le pipeline CI/CD au moment du déploiement SSH - donc aucun secret ne transite ni ne reste en clair sur la VM en dehors du .env généré au déploiement. Les identifiants MinIO/Postgres utilisés par MLflow suivent le même mécanisme, aucune gestion de secrets distincte à mettre en place.

#### Mermaid

```mermaid
flowchart TB
    Internet((Internet))
    Mock[["API Mock EnerVision (externe)"]]
    CI["GitHub Actions (CI/CD)"]
 
    subgraph VM["VM on-premise (ecole)"]
        subgraph Net["Docker Compose"]
            RP["Traefik - Reverse Proxy"]
            Dash["Dashboard (Next.js / React)"]
            API["Core API (FastAPI)"]
            Pred["Prediction (FastAPI)"]
            Reco["Recommendation (FastAPI)"]
            Etl["Worker ETL (async, remplace EventBridge)"]
            MLflow["MLflow (Tracking + Registry)"]
            PG[("PostgreSQL - donnees structurees + backend store MLflow")]
            Minio[("MinIO - bucket raw + artifact store MLflow (S3-compatible)")]
            Redis[("Redis Streams - alert.detected")]
        end
    end
 
    Internet --> RP
    RP --> Dash
    RP --> API
    RP -. "UI MLflow (auth basique)" .-> MLflow
    API --> Pred
    API --> Reco
    Reco --> Pred
    API --> PG
    Pred --> PG
    Pred -- "log runs / registry" --> MLflow
    MLflow --> PG
    MLflow --> Minio
    Etl --> PG
    Etl --> Minio
    Etl --> Mock
    Etl -- "XADD alert.detected (transitions)" --> Redis
    API -- "XREAD alert.detected (SSE)" --> Redis
    CI -. "deploie via SSH + injecte .env (GitHub Secrets)" .-> VM
 
    style Net fill:#f5f7fa,stroke:#4a5568,stroke-width:1px
```

Côté Dashboard, la consommation du flux SSE (`EventSource`) reste à faire —
hors périmètre de la mise en place initiale du flux Redis → `core_api`.