# Worker ETL (ingestion + curation)

Le worker `etl_worker` : un seul job planifié (`EtlJob`, APScheduler,
pas de cron externe), toutes les 60 secondes.

1. Un seul appel `GET /api/v1/readings?limit=7` (les dernières lectures,
   une par site).
2. Pour chaque lecture, dans le même passage :
   - écriture brute dans le bucket MinIO `raw`
     (`raw/{site_id}/{YYYY}/{MM}/{DD}/{HH}/{minutes}.json` — partitionné
     par site d'abord, puis par heure locale Europe/Paris) ;
   - `consumption_kwh` comblé si manquant (forward-fill, dernière
     valeur connue du site, mémorisée en RAM par le worker —
     `domain/imputation.py`) ;
   - upsert direct dans `readings_curated` (Postgres/TimescaleDB), une
     table prête à consommer comme features pour l'entraînement d'un
     modèle.

Avant tout ça, dans le même passage, le worker détecte aussi une
**transition** de `data_quality` pour le site et publie un événement sur
Redis Streams si besoin — voir [Alertes data_quality](#alertes-data_quality-redis-streams)
ci-dessous.

Une lecture `critical` (tous les capteurs en panne, tout est `null`) suit
exactement le même chemin en écriture brute — rien n'est filtré ni
corrigé côté MinIO. Seul `consumption_kwh` est éventuellement comblé
côté `readings_curated`, tous les autres champs y gardent leur valeur
brute telle quelle, `None` inclus.

## Alertes data_quality (Redis Streams)

`domain/data_quality_transition.py` (`DataQualityTransitionDetector`) garde
en mémoire, par site, le dernier `data_quality` connu (`good` | `partial` |
`degraded` | `critical`) et détecte les changements de **zone** à publier —
anti-flood : un site qui reste dans la même zone sur plusieurs cycles
consécutifs ne republie rien.

Trois zones, par sévérité croissante : `good` (aucune), `partial` (mineure —
un souci isolé identifié mais réel), `degraded`/`critical` (alerte).

| Transition | Événement publié |
|---|---|
| Site jamais vu depuis le démarrage du worker | aucun (pas de base de comparaison, même logique que `"no_history"`) |
| `good`/`partial` → `degraded`/`critical` | alerte |
| `good`/`degraded`/`critical` → `partial` | alerte mineure (remplace une alerte en cours le cas échéant) |
| `partial`/`degraded`/`critical` → `good` | retour à la normale |
| `degraded` ↔ `critical` | aucun (anti-flood, même zone) |
| `partial` → `partial` (cycles consécutifs) | aucun (anti-flood, même zone) |

`infrastructure/alert_publisher.py` (`AlertPublisher`) publie sur le stream
Redis `alert.detected` (`XADD ... MAXLEN ~ 500` — le stream sert de tampon
temps réel pour un dashboard qui se (re)connecte, pas d'historique durable).
Champs envoyés : `site_id`, `timestamp`, `data_quality` (strings bruts) et
`null_reasons` (JSON-encodé, seul champ non scalaire). Une panne Redis est
loggée (`alert_publish_error`) et n'interrompt jamais le cycle — surtout,
`DataQualityTransitionDetector.commit()` n'est appelé qu'après une
publication réussie (`detect_transition()` seul ne modifie plus l'état) :
la transition n'est donc jamais considérée "vue" tant qu'elle n'a pas été
publiée, et sera retentée au(x) cycle(s) suivant(s) jusqu'à ce que Redis
soit de nouveau disponible.

`REDIS_HOST`/`REDIS_PORT` dans `infrastructure/config.py` (mêmes défauts que
MinIO : `localhost` en dev hors docker-compose, `redis`/service compose en
conteneur).

## Stratégie d'imputation

Un seul cas, volontairement simple : **forward-fill**, sur
`consumption_kwh` uniquement — reprend la dernière valeur connue du
site, quelle que soit la taille du trou.

`imputation_methods` (colonne texte nullable de `readings_curated`)
distingue trois cas pour chaque lecture :

| Valeur | Signification |
|---|---|
| `None` | `consumption_kwh` était déjà connue, rien à combler |
| `"forward_fill"` | manquante, comblée par la dernière valeur connue du site |
| `"no_history"` | manquante, mais aucune valeur antérieure en mémoire (site jamais vu, ou worker redémarré depuis) — reste `None` |

> L'historique est tenu **en mémoire** par le worker (`ConsumptionKwhImputer`),
> pas relu depuis MinIO ou Postgres : simple et rapide, mais perdu à
> chaque redémarrage du worker — d'où `"no_history"` plutôt qu'une
> valeur inventée sans base au premier cycle qui suit un redémarrage.

## Démarrer l'infra nécessaire

MinIO (source), Postgres (destination) et Redis (alertes data_quality) :

```bash
docker compose up -d minio minio-init postgres redis
```

Appliquer les migrations (une fois, ou après un `git pull` qui en ajoute) :

```bash
cd packages/db-schema
python -m pip install -e . -e .[dev]
python -m alembic upgrade head
```

## Lancer le worker en local

Un seul `.env`, à la racine du repo (partagé par tous les services,
Docker comme apps Python en local) — pas de `.env` séparé dans
`apps/etl_worker`.

```bash
# .env à la racine (aucun .env.example versionné, voir docs/data-storage.md)
cd apps/etl_worker
python -m pip install -r requirements.txt -r requirements-dev.txt
python main.py
```

Une ligne de log JSON par lecture traitée, puis un résumé par cycle :

```json
{"site": "SITE001", "status": "written", "data_quality": "good", "object_key": "SITE001/2026/09/15/17/45.json", "imputation_method": null}
{"site": null, "status": "curated", "data_quality": null, "written": 7}
```

`status` vaut `"raw_write_error"` si MinIO était indisponible pour cette
lecture (le worker continue, il ne plante jamais sur une panne
ponctuelle — cette lecture est alors exclue de l'upsert Postgres),
`"error"` si l'API mock elle-même était injoignable, ou
`"curated_write_error"` si Postgres l'était. Une transition data_quality
ajoute une ligne de log séparée juste avant celle de l'écriture raw :
`"alert_published"` (avec `event`: `"alert"` ou `"recovery"`), ou
`"alert_publish_error"` si Redis était indisponible.

## Lancer les tests unitaires

```bash
cd apps/etl_worker
python -m pytest -v --cov=domain --cov-report=term-missing
```

`domain/imputation.py` et `domain/data_quality_transition.py` sont testés en
isolation (valeur connue, trou comblé, absence d'historique, transitions,
sites indépendants).

> Si `pytest` (sans `python -m`) dit "commande introuvable", c'est que le
> dossier `Scripts`/`bin` de ton interpréteur n'est pas sur le PATH —
> `python -m pytest` fonctionne toujours.

## Vérifier

| Point | Comment vérifier |
|---|---|
| 7 nouveaux objets JSON dans `raw` par cycle (un par site) | Console web http://localhost:9001 (identifiants dans `.env`) → bucket `raw` |
| Une lecture `critical` est écrite, pas ignorée | Parcourir les objets récents d'un site dans la console MinIO (aléatoire côté API mock, peut prendre plusieurs minutes à apparaître) |
| Une ligne par lecture dans `readings_curated` | `psql` ou tout client Postgres : `SELECT * FROM enervision.readings_curated ORDER BY timestamp DESC LIMIT 10;` |
| `consumption_kwh` comblé signalé | `imputation_methods = 'forward_fill'` sur la ligne concernée |
| Une transition data_quality publie un événement, une seule fois même sur plusieurs cycles `critical` d'affilée | `redis-cli XRANGE alert.detected - +` |

## Dépannage rapide

- **`.env` disparaît régulièrement** : vérifier qu'aucun script/outil ne
  fait de `git clean` ou ne le supprime explicitement — `.env` n'est
  jamais touché par les commandes git normales (il est dans
  `.gitignore`).
