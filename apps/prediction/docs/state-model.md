# Modèle d'état des capteurs (`sensor-state-model`)

Second modèle du service Prediction : prédit, pour un site à un instant
donné, si chacun de ses **6 capteurs** sera `on` ou `off` — une
**classification multi-sorties** (une sortie on/off par capteur),
contrairement au modèle de consommation qui fait de la **régression**. Chaque
capteur est prédit individuellement : il n'y a pas d'état global du site.
Voir aussi [ml-pipeline.md](ml-pipeline.md) (modèle
consommation) et [architecture.md](architecture.md) (arborescence complète).

## Vue d'ensemble (entraînement + inférence)

```mermaid
flowchart LR
    subgraph entrainement["Entraînement (cron 24h)"]
        direction TB
        PG["PostgreSQL<br/>readings_curated<br/>(1 lecture/minute)"]
        AGG["aggregate_hourly()<br/>minute → heure, seuil 10%"]
        TRAIN["train_model()<br/>MultiOutputClassifier"]
        MLF["MLflow<br/>champion/challenger"]
        PG --> AGG --> TRAIN --> MLF
    end

    subgraph inference["Inférence (à la demande)"]
        direction TB
        API_P["GET /predict/state"]
        LOAD["load_latest(sensor-state-model)"]
        PRED["predict(site_id, heure)<br/>→ 6 états on/off + confiance"]
        API_P --> LOAD --> PRED
    end

    subgraph consommateurs["Consommateurs"]
        direction TB
        CORE["API Core<br/>/api/v1/predictions/sensors"]
        DASH["Dashboard<br/>modale Capteurs"]
        CORE --> DASH
    end

    MLF -.->|"alias current"| LOAD
    CORE --> API_P
    PRED --> CORE

    style entrainement fill:#fff4e6,stroke:#4a5568
    style inference fill:#eef6ff,stroke:#4a5568
    style consommateurs fill:#f0fff4,stroke:#4a5568
```

Deux chemins indépendants qui ne se recoupent qu'au niveau du modèle publié
dans MLflow : l'entraînement (planifié, lit `readings_curated`) et
l'inférence (à la demande, charge le dernier modèle promu). Les sections
suivantes détaillent chaque étape.

## Ce que le modèle apprend

Chaque ligne de `readings_curated` porte 6 mesures (`consumption_kw`,
`voltage_v`, `current_a`, `power_factor`, `temperature_celsius`,
`humidity_percent`). Une mesure **nulle** signifie que le capteur est `off`
(panne ou donnée manquante), sinon `on`.

| | Contenu |
|---|---|
| **Entrées (features)** | `site_id`, heure (pas la minute) |
| **Sorties (cibles)** | 6 états on/off, un par capteur (`SENSOR_COLUMNS`) |
| **Algorithme** | `MultiOutputClassifier(RandomForestClassifier)` |

Le modèle apprend des habitudes du type « ce site perd souvent l'humidité
vers 11 h ». Il ne voit ni la météo ni l'état des capteurs juste avant : il
prédit à partir du site et de l'heure uniquement.

### Agrégation horaire (`aggregate_hourly`)

`readings_curated` contient une lecture par site et par **minute**. À ce
grain, une panne est un événement quasi unique — une seule ligne par site
et par minute dans tout l'historique, jamais revue au même instant — donc
rien à apprendre, seulement du bruit. `train_model()` agrège d'abord les
lectures en buckets **(site, heure)** avant `build_features`/
`build_sensor_targets` : un capteur est `off` sur ce bucket si la part des
lectures de l'heure qui l'ont vu `off` atteint `MIN_OFF_RATIO_PER_HOUR`
(**10 % par défaut**), `on` sinon. Un ratio plutôt qu'un nombre fixe de
lectures, car le rythme réel varie selon la source (observé entre ~6 et
~40-45 lectures/heure/site selon l'échantillon) — voir « Limites connues »
pour le calcul de ce seuil. C'est aussi le grain que
`/predict/state/range` expose déjà (un point par heure).

```mermaid
flowchart LR
    subgraph minute["Lectures minute (readings_curated)"]
        direction TB
        M1["14:00 — humidity: 41%"]
        M2["14:05 — humidity: null"]
        M3["14:10 — humidity: null"]
        M4["14:15 — humidity: null"]
        M5["14:20 … 14:55 — humidity: OK"]
    end

    minute -->|"groupby(site_id, heure)"| bucket["Bucket (SITE001, 14h)<br/>12 lectures, 3 off"]
    bucket -->|"3/12 = 25% ≥ 10%"| off["humidity_percent = off<br/>pour l'heure 14h"]

    style off fill:#fde2e2,stroke:#c53030
```

## Pourquoi un second modèle plutôt qu'étendre le premier ?

Les cibles sont de nature différente (états catégoriels on/off vs
`consumption_kwh` continu), donc deux pipelines sklearn différents et deux
jeux de métriques (accuracy/F1 vs MAE/RMSE). Les deux modèles partagent en revanche
la même infrastructure de stockage/versioning (`ModelStorePort`, MLflow,
MinIO) — voir le diagramme de package ci-dessous.

## Où vit le code (package par modèle, dans chaque couche)

```mermaid
flowchart TB
    subgraph pres["presentation/api.py"]
        EP1["GET /predict, /predict/range"]
        EP2["GET /predict/state"]
    end

    subgraph app["application/"]
        subgraph appC["consumption/"]
            P1["predict.py"]
            TP1["train_and_publish.py"]
            R1["retrain_if_better.py"]
        end
        subgraph appS["state/"]
            P2["predict_state.py"]
            TP2["train_and_publish_state.py"]
            R2["retrain_state_if_better.py"]
        end
        Ports["ports/ — TrainingDataPort, StateTrainingDataPort,<br/>ModelStorePort (SavedModelMetadata.metrics: dict)"]
    end

    subgraph infra["infrastructure/"]
        subgraph mlC["ml/consumption/"]
            F1["features.py"]
            PL1["pipeline.py — RandomForestRegressor"]
            T1["trainer.py — MAE / RMSE"]
        end
        subgraph mlS["ml/state/"]
            F2["features.py"]
            PL2["pipeline.py — MultiOutputClassifier(RandomForestClassifier)"]
            T2["trainer.py — accuracy / F1 macro (on/off capteurs)"]
        end
        subgraph tdC["training_data/consumption/"]
            RD1["postgres_reader.py — filtre consumption_kwh"]
        end
        subgraph tdS["training_data/state/"]
            RD2["postgres_reader.py — filtre data_quality, lit les 6 capteurs"]
        end
        MS["model_store/ — MinioModelStore, MlflowModelStore<br/>(partagés, distingués par model_name)"]
    end

    EP1 --> P1
    EP2 --> P2
    P1 --> Ports
    TP1 --> Ports
    R1 --> Ports
    P2 --> Ports
    TP2 --> Ports
    R2 --> Ports

    TP1 -.-> mlC
    R1 -.-> mlC
    TP2 -.-> mlS
    R2 -.-> mlS

    Ports --> MS
    Ports --> tdC
    Ports --> tdS

    style appC fill:#eef6ff,stroke:#4a5568
    style appS fill:#fff4e6,stroke:#4a5568
    style mlC fill:#eef6ff,stroke:#4a5568
    style mlS fill:#fff4e6,stroke:#4a5568
    style tdC fill:#eef6ff,stroke:#4a5568
    style tdS fill:#fff4e6,stroke:#4a5568
```

## Entraînement et promotion (cron 24h, champion/challenger)

Même mécanique que le modèle de consommation
([seq_prediction.md](../../../docs/seq_prediction.md)), avec une métrique de
comparaison inversée : l'**accuracy** (part des états on/off de capteurs
correctement prédits) doit être plus **haute** pour promouvoir un candidat (le
MAE, lui, doit être plus **bas**).

Pour lancer un cycle à la demande, sans attendre le cron :

```bash
docker exec prediction python tests/manual/manual_retrain_state.py
```

```mermaid
sequenceDiagram
    autonumber
    participant Cron as APScheduler interne (cron 24h)
    participant Pred as Service Prediction (FastAPI)
    participant PG as PostgreSQL (readings_curated)
    participant MLflow as MLflow (Tracking + Registry)
    participant MinIO as MinIO (S3 - artifact store)

    loop Toutes les 24h
        Cron->>Pred: _run_scheduled_retrain_state()
        Pred->>PG: SELECT site_id, timestamp, data_quality + 6 mesures capteurs
        PG-->>Pred: Lectures curées, une par site et par minute
        Pred->>Pred: aggregate_hourly() — regroupe en buckets (site, heure)
        Pred->>Pred: train_model() — MultiOutputClassifier(RandomForest),<br/>accuracy + F1 macro on/off sur le test set
        Pred->>MLflow: register() — log_params/log_metrics + log_model<br/>(nouvelle version "sensor-state-model", alias non déplacé)
        MLflow->>MinIO: Stocke l'artifact du modèle
        Pred->>Pred: candidat.accuracy > champion.accuracy ?
        alt Candidat meilleur (ou premier entraînement)
            Pred->>MLflow: promote() — déplace l'alias "current"
        else Candidat pas meilleur
            Pred->>Pred: Candidat conservé pour historique, alias inchangé
        end
    end

    Note over Pred,MLflow: Au démarrage (main.py), _check_models_loaded_at_startup()<br/>tente load_latest("sensor-state-model") et log succès/échec —<br/>mais /predict/state recharge quand même à chaque appel<br/>(une promotion est visible immédiatement, sans redémarrage)
```

## Appel `GET /predict/state`

```mermaid
sequenceDiagram
    autonumber
    participant Client as Dashboard (Next.js)
    participant Core as API Core (FastAPI)
    participant Pred as Service Prediction (FastAPI)
    participant MLflow as MLflow (alias "current")

    Client->>Core: GET /api/v1/predictions/sensors?site_id=...&timestamp=... (Bearer JWT)
    Core->>Core: Vérifie le JWT + l'accès au site
    Core->>Pred: GET /predict/state?site_id=...&timestamp=...
    Pred->>MLflow: load_latest("sensor-state-model")
    alt Modèle disponible
        MLflow-->>Pred: pipeline + metadata (accuracy, f1_macro, trained_at)
        Pred->>Pred: predict(site_id, hour) → 6 états on/off
        Pred-->>Core: 200 OK {sensors: {capteur: on|off}, model_version}
        Core-->>Client: 200 OK
    else Aucun modèle promu
        Pred-->>Core: 503 state model not loaded
        Core-->>Client: 503 (PredictionModelNotLoadedError)
    end
```

## Métriques suivies

| Métrique | Modèle | Sens |
|---|---|---|
| `mae`, `rmse` | consumption | plus bas = meilleur |
| `accuracy`, `f1_macro` | state | plus haut = meilleur, calculés sur l'ensemble des états on/off de capteurs (F1 macro car un capteur est presque toujours `on` : l'accuracy seule serait trompeuse) |

Les deux sont stockées dans le même champ générique
`SavedModelMetadata.metrics: dict[str, float]`, journalisé tel quel dans
MLflow (`mlflow.log_metrics(metadata.metrics)`).

## Limites connues

- **Historique court** : le modèle ne connaît que les heures déjà observées ;
  il ne peut rien prédire de fiable sur les autres moments de la journée.
- **Pannes rares** (environ 7 % des mesures par capteur) : un modèle qui
  répondrait toujours `on` aurait une bonne accuracy, d'où le suivi du F1
  macro. La promotion se fait pour l'instant sur l'accuracy.
- **Granularité minute trop fine pour apprendre quoi que ce soit** : sans
  `aggregate_hourly`, chaque panne est un événement unique (une ligne par
  site et par minute, jamais revue), donc pure coïncidence plutôt qu'un
  motif généralisable — d'où l'agrégation à l'heure.
- **Seuil `MIN_OFF_RATIO_PER_HOUR` calibré sur un échantillon réel, pas figé** :
  un premier échantillon (994 lectures, 7 sites) suggérait ~6 lectures/heure/site,
  d'où un seuil initial à 30 %. Un second échantillon (un seul site sur ~20h) a
  montré une cadence bien plus dense (~87s entre lectures, ~40-45/heure) : à cette
  cadence, une vraie coupure réseau de 2-3 lectures consécutives (~4-5 min) ne pèse
  que ~5-7 % de l'heure, et un seuil à 30 % l'aurait classée `on` à tort. Le seuil
  a été baissé à **10 %** pour capter ces pannes courtes tout en restant net du
  bruit d'une lecture isolée (~2,5 % de l'heure à cette cadence). Si la cadence
  réelle de production diverge encore, ce seuil reste à revalider.
- **Pannes potentiellement aléatoires** : si le générateur de données ne
  corrèle pas vraiment les pannes à l'heure (ni à rien d'observable), même
  agrégées, elles restent en grande partie imprévisibles ; aucun modèle ne
  peut faire mieux que deviner face à du vrai bruit.
- **Ancien modèle** : un modèle enregistré avant ce changement prédisait un
  état global. `predict_state()` le refuse (503) tant qu'un ré-entraînement
  n'a pas promu un modèle par capteur.
