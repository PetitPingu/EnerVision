# Pipeline ML

Modèle de **régression** : prédire `consumption_kwh` à partir du site et
de l'heure de la lecture.

## Données d'entrée

Colonnes attendues après lecture (`TrainingDataPort`) :

| Colonne | Type | Description |
|---|---|---|
| `site_id` | string | Identifiant du site (ex. `SITE001`) |
| `timestamp` | datetime ISO8601 | Horodatage de la lecture |
| `consumption_kwh` | float | Consommation mesurée (target) |

## Feature engineering (`infrastructure/ml/features.py`)

```
RAW_COLUMNS     = site_id, timestamp, consumption_kwh
FEATURE_COLUMNS = site_id, hour, minute
TARGET          = consumption_kwh
```

`build_features(df)` :

1. Exclut les lignes où `consumption_kwh` est null.
2. Extrait `hour` et `minute` du timestamp (`format="ISO8601"` pour gérer
   les formats mixtes avec/sans microsecondes).
3. Retourne `(X, y)` prêts pour sklearn.

### Choix de features (phase 1)

| Feature | Inclus | Raison |
|---|---|---|
| `site_id` | Oui | OneHotEncoder — chaque site a un profil distinct |
| `hour`, `minute` | Oui | Patterns horaires de consommation |
| `day_of_week`, `month` | Non | Historique court au démarrage du projet |
| `temperature_celsius` | Non | Test A/B : performances dégradées sur nos données |

## Modèle (`infrastructure/ml/pipeline.py`)

Justification du choix `RandomForestRegressor` : voir
[model-choice.md](model-choice.md).

Pipeline sklearn :

```
ColumnTransformer
  ├── site_id  → OneHotEncoder(handle_unknown="ignore")
  └── hour, minute → passthrough
        ↓
RandomForestRegressor(n_estimators=100, random_state=42)
```

## Entraînement (`infrastructure/ml/trainer.py`)

`train_model(df)` :

1. `build_features(df)`
2. `train_test_split` (80/20 par défaut)
3. `fit` + évaluation sur le test set
4. Retourne `TrainingResult` : pipeline entraîné, MAE, RMSE, tailles train/test

## Métriques

| Métrique | Description |
|---|---|
| **MAE** | Erreur absolue moyenne (kWh) |
| **RMSE** | Racine de l'erreur quadratique moyenne (kWh) |

Les métriques sont persistées dans `metadata.json` lors de la publication
MinIO.

## Publication

Le use case `train_and_publish` sérialise le pipeline entraîné en
`model.joblib` et écrit les métadonnées :

```json
{
  "model_name": "energy-consumption",
  "trained_at": "2026-09-16T14-30-00Z",
  "mae": 25.15,
  "rmse": 36.21,
  "train_size": 382,
  "test_size": 128,
  "features": ["site_id", "hour", "minute"]
}
```

## Améliorations prévues (phase 2+)

- Features lag (`consumption_kwh` t-1h, t-24h)
- `day_of_week` quand l'historique sera suffisant
- Modèle 2 : classification risque/anomalie (`data_quality`)
- Registry MLflow à la place du stockage MinIO direct
