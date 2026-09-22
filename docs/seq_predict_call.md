# Diagramme de séquence du appel au Service Prediction

> Aucune authentification n'est implémentée à ce jour sur `core_api` ni sur
> les services internes (pas de JWT, pas de clé API) — voir
> [seq_auth_token.md](seq_auth_token.md) pour le design proposé mais non
> câblé. Les échanges ci-dessous reflètent l'état réel : appels HTTP nus.

## Appel au Service Prediction

#### Mermaid

```mermaid
sequenceDiagram
    autonumber
    participant Client as Dashboard (Next.js)
    participant Core as Core API (FastAPI)
    participant Pred as Service Prediction (FastAPI)
    participant MLflow as MLflow (alias "current")

    Client->>Core: GET /api/v1/predictions/range?site_id=...&start_time=...&end_time=...
    Core->>Pred: GET /predict/range?site_id=...&start_time=...&end_time=...
    Pred->>MLflow: load_latest(model_name) (rechargé à chaque appel, pas de cache)
    MLflow-->>Pred: Pipeline sklearn + métadonnées (version)
    Pred->>Pred: Calcul de la/les prédiction(s)
    Pred-->>Core: 200 OK + prédictions
    Core-->>Client: 200 OK + prédictions
```

### Appel au Service Recommandation

#### Mermaid

```mermaid
sequenceDiagram
    autonumber
    participant Client as Dashboard (Next.js)
    participant Core as Core API (FastAPI)
    participant Reco as Service Recommandation (FastAPI)
    participant Pred as Service Prediction (FastAPI)
    participant PG as PostgreSQL (sites, readings_curated, recommendations)

    Client->>Core: GET /api/v1/recommendations?site_id=...
    Core->>Reco: GET /api/v1/recommendations?site_id=...
    Reco->>PG: Site (capacité) + dernier power_factor connu
    PG-->>Reco: Site, PowerFactorReading (ou None)
    Reco->>Pred: GET /predict?site_id=...&timestamp=...
    Pred-->>Reco: 200 OK + prédiction
    Reco->>Reco: Applique le moteur de règles à seuils (rules_engine)
    Reco->>PG: INSERT recommendations (une ligne par règle déclenchée)
    Reco-->>Core: 200 OK + recommandations (liste vide si aucune déclenchée)
    Core-->>Client: 200 OK + recommandations
```