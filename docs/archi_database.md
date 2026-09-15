## 2. Schéma de la base de données postgres

5 tables, UUID en clé primaire partout (plus simple à générer côté application que des séquences, et ça évite de fuiter le volume de données via des IDs séquentiels si l'API est un jour publique).

USERS — table d'authentification, volontairement isolée du reste : email (unique), password_hash (jamais le mot de passe en clair, bcrypt/argon2 côté FastAPI), role (ex. admin/viewer). Elle ne référence aucune autre table — c'est l'hypothèse que je veux qu'on confirme ensemble ci-dessous.

SITES — les entités métier de base : nom, capacité, région. Point d'ancrage pour tout le reste.

CONSUMPTION_READINGS — les relevés bruts ingérés par le Worker ETL, avec consumption_kw nullable et data_quality (good/degraded/critical) pour refléter fidèlement ce que renvoie le mock, sans perdre l'information de dégradation.

PREDICTIONS — écrites par le worker/service Prediction toutes les 24h, avec model_version pour pouvoir tracer quelle version du modèle a produit quelle prédiction si vous voulez comparer plus tard.

RECOMMENDATIONS — prediction_id est nullable parce qu'une recommandation peut aussi naître d'un état courant critique sans passer par une prédiction (ex. data_quality: critical détecté en direct) — pas seulement d'un pic anticipé.

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
        uuid id PK
        varchar name
        float capacity_kw
        varchar region
        timestamptz created_at
    }
 
    CONSUMPTION_READINGS {
        uuid id PK
        uuid site_id FK
        timestamptz reading_timestamp
        float consumption_kw "nullable"
        varchar data_quality "good | degraded | critical"
        timestamptz created_at
    }
 
    PREDICTIONS {
        uuid id PK
        uuid site_id FK
        timestamptz target_timestamp
        float predicted_consumption_kw
        varchar model_version "version du Model Registry MLflow"
        timestamptz generated_at
    }
 
    RECOMMENDATIONS {
        uuid id PK
        uuid site_id FK
        uuid prediction_id FK "nullable"
        varchar type "load_shedding | load_smoothing | maintenance_alert"
        text message
        timestamptz created_at
    }
 
    SITES ||--o{ CONSUMPTION_READINGS : "mesure"
    SITES ||--o{ PREDICTIONS : "anticipe"
    SITES ||--o{ RECOMMENDATIONS : "recoit"
    PREDICTIONS |o--o| RECOMMENDATIONS : "declenche"
```

#### Diagramme

![image](images/archi_database.png)