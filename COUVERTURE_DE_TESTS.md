# Couverture de tests — analyse (branche `feat/check-couverture-de-tests`)

Contexte : aucun des 5 packages Python n'a de coverage mesuré ni gaté en CI
(seul `prediction` a ses tests unitaires exécutés en CI, via
`prediction-tests.yml` — sans `--cov`). Cette branche fait tourner
`pytest-cov` en local sur chaque service pour voir où on en est réellement,
avec `-m "not integration"` (comportement par défaut de chaque `pytest.ini` :
seule la suite unitaire rapide, pas les tests qui tapent un vrai
Postgres/Redis/MinIO).

Deux passages : la 1ère analyse a fait remonter 2 tests cassés (jamais vus
avant, faute d'être gatés en CI) ; la 2ème analyse est le résultat après
correction.

---

## 1ère analyse — état brut

| Service | Coverage (source only) | Résultat |
|---|---|---|
| `prediction` | 89% | ✅ 74 passed |
| `core_api` | 85% | ✅ 104 passed |
| `recommendation` | 84% | ✅ 25 passed |
| `etl_worker` | 82% | ❌ **1 failed**, 85 passed |
| `packages/db-schema` | 97% | ❌ **1 failed**, 11 passed |

### Échec 1 — `etl_worker`, bombe à retardement

`tests/test_model_health_job.py::test_run_publishes_mae_and_drift_when_reconciled_predictions_exist`

```
assert published["mae"] == {"SITE001": 10.0}
E       AssertionError: assert {} == {'SITE001': 10.0}
```

**Cause** : la fixture `_reconciled()` figeait des dates en dur
(`generated_at=datetime(2026, 9, 21, 10, 30, ...)`). Le job filtre avec
`compute_mae_24h(reconciled, now)` où `now = datetime.now(timezone.utc)` —
l'horodatage réel au moment de l'exécution
(`apps/etl_worker/application/model_health_job.py:43`). Le jour où le test a
été écrit, ces dates figées étaient récentes ; le temps réel a avancé, elles
sont sorties de la fenêtre glissante de 24h, et `mae_by_site` ressort vide.
Le test n'a jamais été "vraiment" cassé par un changement de code — il
devait mécaniquement finir par casser tout seul, à une date fixe, tant que
personne ne le faisait tourner. C'est exactement le genre de régression
qu'une CI qui gate ces tests aurait détectée immédiatement, au lieu de rester
invisible pendant des mois.

**Correctif** (`apps/etl_worker/tests/test_model_health_job.py`) :
dates relatives à `datetime.now(timezone.utc)` au lieu de dates absolues.

```diff
 def _reconciled(**overrides) -> ReconciledPrediction:
+    now = datetime.now(timezone.utc)
     data = {
         "site_id": "SITE001",
-        "target_timestamp": datetime(2026, 9, 21, 11, 0, tzinfo=timezone.utc),
+        "target_timestamp": now - timedelta(minutes=30),
         "predicted_consumption_kwh": 100.0,
         "actual_consumption_kwh": 90.0,
         "model_version": "2026-09-16T14-30-00Z",
-        "generated_at": datetime(2026, 9, 21, 10, 30, tzinfo=timezone.utc),
+        "generated_at": now - timedelta(hours=1),
         **overrides,
     }
     return ReconciledPrediction(**data)
```

Le test `test_run_publishes_mae_by_horizon_when_enough_samples_exist` a
aussi été aligné sur `datetime.now(timezone.utc)` par cohérence, bien que
non cassé (`compute_mae_by_horizon` ne filtre pas sur l'horloge réelle, donc
pas de risque immédiat — mais autant éviter la même bombe à retardement si
cette fonction évolue).

### Échec 2 — `packages/db-schema`, assertion pas mise à jour

`tests/test_models.py::test_registers_one_table_per_entity_in_the_enervision_schema`

```
assert set(tables) == {...}
E       AssertionError: assert {'enervision....r_sites', ...} == {'enervision....vision.users'}
E       Extra items in the left set:
E       'enervision.predictions_log'
```

**Cause** : `db_schema.models.PredictionLog` (table `predictions_log`,
utilisée par `PredictionLogWriter` côté `prediction` pour journaliser chaque
appel à `/predict`, voir `apps/prediction/infrastructure/prediction_log_writer.py`)
a été ajoutée au schéma ORM sans que ce test — qui vérifie l'ensemble exact
des tables enregistrées — soit mis à jour en même temps. Même cause racine
que le premier échec : personne ne fait tourner cette suite, donc rien ne
prévient quand elle devient obsolète.

**Correctif** (`packages/db-schema/tests/test_models.py`) :

```diff
     assert set(tables) == {
         "enervision.sites",
         "enervision.alerts",
         "enervision.readings_curated",
         "enervision.recommendations",
+        "enervision.predictions_log",
         "enervision.users",
         "enervision.user_sites",
     }
```

### Points faibles de coverage déjà visibles (attendus, pas alarmants)

Dans les 3 services à architecture hexagonale, tout ce qui tombe sous ~30-55%
est systématiquement une classe qui touche une vraie DB/API externe :
`user_repository.py` (29%), `site_access_repository.py` (47%),
`prediction_client.py` (28%) côté `core_api` ; `model_health_reader.py`
(44%), `raw_reader.py` (53%) côté `etl_worker` ;
`power_factor_repository.py`/`recommendation_repository.py`/`site_repository.py`
(~54%) côté `recommendation`. Cohérent avec le pattern : ces classes sont
couvertes par les tests `tests/integration/` (contre un vrai Postgres), pas
par les unitaires — donc absentes du chiffre `-m "not integration"` ci-dessus.

---

## 2ème analyse — après correction

| Service | Coverage (source only) | Résultat | Évolution |
|---|---|---|---|
| `prediction` | 89% | ✅ 74 passed | inchangé |
| `etl_worker` | **85%** | ✅ 86 passed | +3 pts (le test corrigé exerce en plus les branches drift/model_health_reader) |
| `core_api` | 85% | ✅ 104 passed | inchangé |
| `recommendation` | 84% | ✅ 25 passed | inchangé (aucun échec au 1er passage) |
| `packages/db-schema` | 97% | ✅ 12 passed | inchangé |

**5/5 suites unitaires vertes.** Détail service par service :

### `core_api` — 85% (739 lignes, 104 tests, 13 exclus car `integration`)
```
application/collector.py                 91%
application/ports.py                    100%
domain/entities.py                      100%
infrastructure/active_alerts_reader.py   56%   <- couvert par tests/integration
infrastructure/api_client.py             93%
infrastructure/auth.py                  100%
infrastructure/config.py                100%
infrastructure/latest_readings_reader.py 53%   <- couvert par tests/integration
infrastructure/login_throttle.py        100%
infrastructure/model_health_client.py   100%
infrastructure/password_policy.py        94%
infrastructure/prediction_client.py      28%   <- couvert par tests/integration
infrastructure/recommendation_client.py 100%
infrastructure/redis_alert_stream.py     97%
infrastructure/session.py                56%   <- couvert par tests/integration
infrastructure/site_access_repository.py 47%   <- couvert par tests/integration
infrastructure/user_repository.py        29%   <- couvert par tests/integration
presentation/api.py                      98%
```

### `etl_worker` — 85% (568 lignes, 86 tests, 6 exclus car `integration`)
```
application/backfill_curated_from_raw.py 83%
application/backfill_readings.py         76%
application/etl_job.py                  100%
application/model_health_job.py          89%   <- 70% avant le fix
domain/data_quality_transition.py       100%
domain/imputation.py                    100%
domain/model_health.py                   98%
infrastructure/alert_publisher.py       100%
infrastructure/config.py                100%
infrastructure/curated_writer.py         97%
infrastructure/model_health_metrics.py   40%   <- couvert par tests/integration
infrastructure/model_health_reader.py    44%   <- couvert par tests/integration
infrastructure/raw_reader.py             53%   <- couvert par tests/integration
infrastructure/raw_writer.py            100%
```

### `recommendation` — 84% (164 lignes, 25 tests, 8 exclus car `integration`)
```
application/generate_recommendations.py 100%
application/ports.py                    100%
application/rules_engine.py              94%
domain/entities.py                      100%
infrastructure/config.py                100%
infrastructure/power_factor_repository.py    54%   <- couvert par tests/integration
infrastructure/prediction_client.py     100%
infrastructure/recommendation_repository.py  54%   <- couvert par tests/integration
infrastructure/session.py                56%   <- couvert par tests/integration
infrastructure/site_repository.py        55%   <- couvert par tests/integration
```

### `prediction` — 89% (639 lignes, 74 tests, 5 exclus car `integration`)
```
application/consumption/predict.py                    100%
application/consumption/retrain_if_better.py            95%
application/consumption/train_and_publish.py            93%
application/ports/*                                    100%
application/state/predict_state.py                      96%
application/state/retrain_state_if_better.py             95%
application/state/train_and_publish_state.py             93%
infrastructure/config.py                                100%
infrastructure/ml/consumption/*                      94-100%
infrastructure/ml/state/*                             95-100%
infrastructure/model_store/factory.py                    73%
infrastructure/model_store/minio_store.py                95%
infrastructure/model_store/mlflow_store.py                98%
infrastructure/prediction_log_writer.py                   69%   <- couvert par tests/integration
infrastructure/training_data/consumption/json_file_reader.py  62%
infrastructure/training_data/consumption/postgres_reader.py   29%   <- couvert par tests/integration
infrastructure/training_data/factory.py                   72%
```

### `packages/db-schema` — 97% (70 lignes, 12 tests)
```
src/db_schema/config.py     100%
src/db_schema/database.py    80%
src/db_schema/models.py     100%
```

---

## À retenir

1. **Les deux échecs n'étaient pas des bugs de code** — le code métier
   (`model_health_job.py`, `models.py`) était correct. Ce sont les tests
   eux-mêmes qui avaient dérivé (dates figées, assertion pas mise à jour).
   Argument fort pour l'oral : ça illustre concrètement pourquoi ne pas
   gater ces suites en CI est risqué — pas seulement en théorie.
2. **La coverage globale est déjà solide** (82-97% selon le service) sans
   aucun effort dédié jusqu'ici — les zones basses sont presque toutes des
   classes d'accès DB/API externe, volontairement laissées aux tests
   `integration/` plutôt que mockées à outrance.
3. **Prochaine étape naturelle** : un workflow CI (`unit-tests.yml`,
   matrice `core_api`/`etl_worker`/`recommendation`/`packages/db-schema`,
   même pattern que `prediction-tests.yml`) pour que ces suites — et donc
   ces classes de régression — soient surveillées en continu au lieu d'être
   découvertes au hasard d'un `pytest-cov` lancé manuellement.
