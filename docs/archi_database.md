## 2. Schéma de la base de données postgres

Les tables ci-dessous existent réellement (schéma `enervision`, créées via
Alembic pour `sites`/`readings`/`alerts` et via
`db/init/002-consumption-readings.sql` pour `consumption_readings`) :
clé naturelle `site_id` (text, l'identifiant renvoyé par l'API mock, ex.
`SITE001`), pas d'UUID — plus simple à corréler directement avec les
payloads de l'API et les objets MinIO sans jointure supplémentaire.
`USERS`, `PREDICTIONS` et `RECOMMENDATIONS` restent des propositions non
implémentées, à confirmer avec l'équipe.

SITES — les entités métier de base, telles que renvoyées par l'API mock : nom, type, capacité, localisation, statut.

CONSUMPTION_READINGS — table alimentée par le job de transformation horaire du Worker ETL (issue #19, voir [seq_etl.md](seq_etl.md)) : une ligne par lecture transformée depuis le bucket MinIO `raw`, clé primaire naturelle `(site_id, timestamp)` qui porte l'idempotence (`ON CONFLICT DO NOTHING`). C'est une hypertable TimescaleDB. Aucune donnée n'y est corrigée ou filtrée — y compris les lectures `critical` (tous les champs de mesure `null`). Pas de clé étrangère vers SITES (site_id est un simple champ texte, non contraint).

READINGS — table structurée destinée à être servie par core_api (alimentation à définir, hors périmètre de l'issue #19). Même forme que CONSUMPTION_READINGS, mais avec clé étrangère vers SITES.

ALERTS — alertes de consommation relayées depuis l'API mock (voir `GET /api/v1/alerts`), rattachées à un site.

PREDICTIONS *(proposé)* — écrites par le worker/service Prediction toutes les 24h, avec model_version pour pouvoir tracer quelle version du modèle a produit quelle prédiction si vous voulez comparer plus tard.

RECOMMENDATIONS *(proposé)* — prediction_id est nullable parce qu'une recommandation peut aussi naître d'un état courant critique sans passer par une prédiction (ex. data_quality: critical détecté en direct) — pas seulement d'un pic anticipé.

USERS *(proposé)* — table d'authentification, volontairement isolée du reste : email (unique), password_hash (jamais le mot de passe en clair, bcrypt/argon2 côté FastAPI), role (ex. admin/viewer). Elle ne référence aucune autre table — c'est l'hypothèse que je veux qu'on confirme ensemble.

#### Mermaid

```mermaid
erDiagram
    USERS {
        uuid id PK
        varchar email UK
        varchar password_hash
        varchar role
        timestamptz created_at
        timestamptz updated_at
    }

    SITES {
        varchar site_id PK
        varchar site_name
        varchar site_type
        varchar location
        float capacity_kw
        varchar status
    }

    CONSUMPTION_READINGS {
        varchar site_id PK "pas de FK vers SITES"
        timestamptz timestamp PK
        varchar site_type
        float consumption_kw "nullable"
        float consumption_kwh "nullable"
        float voltage_v "nullable"
        float current_a "nullable"
        float power_factor "nullable"
        float temperature_celsius "nullable"
        float humidity_percent "nullable"
        text_array null_reasons
        varchar data_quality "good | partial | degraded | critical"
        timestamptz ingested_at
    }

    READINGS {
        varchar site_id PK_FK
        timestamptz timestamp PK
        varchar site_type
        float consumption_kw "nullable"
        float consumption_kwh "nullable"
        float voltage_v "nullable"
        float current_a "nullable"
        float power_factor "nullable"
        float temperature_celsius "nullable"
        float humidity_percent "nullable"
        text_array null_reasons
        varchar data_quality
    }

    ALERTS {
        varchar alert_id PK
        timestamptz timestamp
        varchar site_id FK
        varchar severity
        varchar type
        text message
        float value "nullable"
        float threshold
    }

    PREDICTIONS {
        uuid id PK
        varchar site_id FK
        timestamptz target_timestamp
        float predicted_consumption_kw
        varchar model_version "version du Model Registry MLflow"
        timestamptz generated_at
    }

    RECOMMENDATIONS {
        uuid id PK
        varchar site_id FK
        uuid prediction_id FK "nullable"
        varchar type "load_shedding | load_smoothing | maintenance_alert"
        text message
        timestamptz created_at
    }

    SITES ||--o{ READINGS : "mesure"
    SITES ||--o{ ALERTS : "concerne"
    SITES ||--o{ PREDICTIONS : "anticipe"
    SITES ||--o{ RECOMMENDATIONS : "recoit"
    PREDICTIONS |o--o| RECOMMENDATIONS : "declenche"
```
