# Model Registry MLflow (`MlflowModelStore`)

## Contexte

Le ticket "infra MLflow" demandait d'ajouter le serveur MLflow (Tracking +
Model Registry) à `docker-compose.yml`, prêt à être utilisé par
`apps/prediction` — sa liste de tâches ne couvrait que l'infra (conteneur
`mlflow`, `MLFLOW_TRACKING_URI`). L'écriture de l'implémentation
`ModelStorePort` elle-même (ce document) va au-delà de cette liste : elle
concrétise l'objectif du ticket (*"remplacer MinioModelStore par une
implémentation ModelStorePort basée sur MLflow"*), mais ce n'était pas une
tâche explicitement listée — à mentionner si ce travail est présenté comme
la réalisation stricte du ticket.

## Ce qui existe maintenant

`MlflowModelStore` ([infrastructure/model_store/mlflow_store.py](../infrastructure/model_store/mlflow_store.py))
implémente `ModelStorePort`, exactement comme `MinioModelStore`. Les deux
**coexistent** derrière la variable `MODEL_STORE` — voir
[configuration.md](configuration.md). `docker-compose.yml` fixe
`MODEL_STORE=mlflow` pour le service `prediction` : c'est l'implémentation
réellement utilisée par `/predict` et `train_and_publish` aujourd'hui
(`minio` reste le défaut du code si la variable n'est pas définie, ex. en
local hors Docker sans la surcharger). Aucune suppression de
`MinioModelStore` : décision explicite, la bascule définitive fera l'objet
d'un autre ticket si elle a lieu.

| Implémentation | Fichier | Enregistrement |
|---|---|---|
| `MinioModelStore` | `model_store/minio_store.py` | Fichiers `.joblib`/`.json` dans MinIO, pointeur `latest/` |
| `MlflowModelStore` | `model_store/mlflow_store.py` | **Model Registry MLflow** (ce document) |

## Comment `save()` enregistre dans le Registry

```python
with mlflow.start_run(run_name=metadata.trained_at) as run:
    mlflow.log_params({...})          # trained_at, train_size, test_size, features
    mlflow.log_metrics({...})         # mae, rmse
    mlflow.sklearn.log_model(pipeline, artifact_path="model")
    run_id = run.info.run_id

model_version = mlflow.register_model(model_uri=f"runs:/{run_id}/model", name=metadata.model_name)
client.set_registered_model_alias(metadata.model_name, "current", model_version.version)
```

Trois étapes distinctes côté MLflow, à ne pas confondre :

1. **Le run** (Tracking) : une entrée d'historique avec params/metrics/artefact. Ne fait pas encore partie du Registry.
2. **`register_model()`** : crée (ou incrémente) une **version** du modèle nommé `metadata.model_name` dans le Registry, en pointant vers l'artefact du run. C'est l'enregistrement au sens propre.
3. **`set_registered_model_alias()`** : déplace l'alias `current` sur cette nouvelle version.

## Pourquoi un alias, et pourquoi pas `"latest"`

L'alias joue le même rôle que le pointeur `{model_name}/latest/` de
`MinioModelStore` : toujours désigner la dernière version entraînée sans
suivre un numéro de version à la main. Nommé **`current`**, pas `"latest"` —
ce nom est réservé en interne par MLflow (conflit avec la notion historique
de "dernière version" du Registry) et lève une erreur à la création
(`'latest' alias name (case insensitive) is reserved`), découvert en testant
contre le vrai serveur.

## Comment `load_latest()` résout l'alias

```python
model_version = client.get_model_version_by_alias(model_name, "current")
run = client.get_run(model_version.run_id)
pipeline = mlflow.sklearn.load_model(f"models:/{model_name}@current")
```

MLflow n'a pas de sidecar `metadata.json` comme `MinioModelStore` : `mae`,
`rmse`, `train_size`, `test_size`, `features` sont reconstruits depuis les
params/metrics du run associé à la version (voir `_metadata_from_run`).

## Stockage physique

Le Registry ne stocke que des métadonnées (Postgres, schéma dédié `mlflow` —
voir [archi_infra.md](../../../docs/archi_infra.md)). L'artefact du modèle
(le fichier réellement chargé par `load_model`) est écrit par MLflow dans le
bucket MinIO **`models`** — le même que `MinioModelStore`, réutilisé tel
quel (pas de bucket dédié, décision du ticket). Pas de collision possible :
MLflow préfixe ses clés par `experiment_id` (numérique), `MinioModelStore`
par `model_name` (ex. `energy-consumption/...`).

## Tests

Le Registry ne se mocke pas facilement (pas un simple appel HTTP à
simuler). `tests/model_store/test_mlflow_store.py` utilise un backend
SQLite jetable par test (`sqlite:///{tmp_path}/mlflow.db`) : le store
fichier de MLflow (`file:`) **ne supporte pas** le Model Registry (d'où
l'obligation d'un backend Postgres en prod, cf. le ticket), mais SQLite si —
tests rapides, isolés, et qui exercent le vrai comportement MLflow plutôt
qu'un mock.

Vérifié aussi en conditions réelles contre le stack complet (Postgres +
MinIO + serveur `mlflow`) via `tests/manual/manual_train_and_publish.py`
avec `MODEL_STORE=mlflow` : modèle réellement enregistré, réellement
rechargé, métadonnées identiques.

## Migrer un modèle déjà entraîné sous MinioModelStore

`MODEL_STORE=mlflow` étant maintenant le défaut, le Registry démarre vide
même si un modèle existe déjà dans MinIO (entraîné par quelqu'un avant cette
bascule) — `/predict` renverrait 503 tant que rien n'est enregistré côté
MLflow. Plutôt que de ré-entraîner (et perdre le modèle/les métriques déjà
obtenus), `tests/manual/manual_migrate_minio_to_mlflow.py` importe le
modèle existant tel quel :

```bash
python tests/manual/manual_migrate_minio_to_mlflow.py [model_name]
```

Lit `{model_name}/latest` depuis MinIO via `MinioModelStore.load_latest()`,
puis l'enregistre via `MlflowModelStore.save()` — mêmes pipeline et
métriques (MAE, RMSE, features...), sans recalcul. Idempotent, ne modifie
jamais MinIO (lecture seule côté source). Vérifié de bout en bout : un
modèle entraîné sous `MODEL_STORE=minio` a été importé et rechargé depuis
MLflow avec des métriques strictement identiques (MAE 32.66, RMSE 37.74).

## Version MLflow : 2.22.5 → 3.16.1

La CI Trivy (`.github/workflows/trivy.yml`, `severity: CRITICAL,HIGH`,
`exit-code: 1`, aucune exception configurée) a détecté 18 CVE HIGH/CRITICAL
dans `mlflow==2.22.5`, toutes corrigées uniquement à partir de la branche
3.x (aucun correctif en 2.x). Épinglé sur `3.16.1` (dernière stable au
moment du fix) dans `mlflow/requirements.txt` **et**
`apps/prediction/requirements.txt` (même raison qu'expliqué plus haut :
client/serveur = deux images buildées séparément, doivent rester
synchronisées). Deux ruptures de compatibilité rencontrées et corrigées :

- **Protection anti DNS-rebinding** (nouvelle en 3.x, justement pour
  corriger une des CVE ci-dessus) : le serveur rejette par défaut tout
  `Host` qui n'est pas `localhost`/IP privée. Le nom DNS interne Docker
  `mlflow` (utilisé par `prediction` et les scripts manuels) devait être
  ajouté explicitement via `--allowed-hosts` dans `mlflow/entrypoint.sh`.
- **Sérialisation skops par défaut** (remplace pickle, plus sûr contre les
  CVE de désérialisation) : `RandomForestRegressor` contient un type
  (`sklearn.tree._tree.Tree`) que skops refuse de sérialiser sans
  confirmation explicite. Déclaré de confiance via `skops_trusted_types`
  dans `MlflowModelStore.save()` — légitime ici puisqu'on sérialise un
  modèle qu'on vient d'entraîner nous-mêmes, pas un fichier tiers.

Vérifié après coup : suite de tests (30/30), entraînement réel, `/predict`
et script de migration, tous revalidés contre `3.16.1`. Trivy relancé
localement sur `apps/prediction` : 0 vulnérabilité restante.

## Ce qui n'est pas fait

- Pas de **stages** (`Staging`/`Production`) — seul l'alias `current` existe. `seq_prediction.md` mentionne une transition vers un stage "Production" : pas implémenté ici.
- Pas de **rétention/nettoyage** des anciennes versions — chaque `save()` en crée une nouvelle, indéfiniment.
