# Worker ETL (issue #19)

Le worker `etl_worker` implémente le cycle décrit dans
[docs/seq_etl.md](seq_etl.md) : un seul job planifié (APScheduler, pas de
cron externe), toutes les 60 secondes, qui fait tout en un cycle :

1. Un seul appel `GET /api/v1/readings?limit=7` (les dernières lectures,
   une par site).
2. Pour chaque lecture : écriture brute dans le bucket MinIO `raw`
   (`raw/{date}/{site_id}_{timestamp}.json` — un fichier par lecture,
   jamais écrasé : l'horodatage dans la clé garantit qu'aucune donnée
   intraday n'est perdue).
3. Insertion dans `consumption_readings` (Postgres/TimescaleDB),
   idempotente (`ON CONFLICT DO NOTHING`).
4. Publication d'une alerte sur Redis Streams (`alert.detected`) si
   `data_quality == "critical"`.

Chaque étape (MinIO, Postgres, Redis) est isolée par son propre
`try/except` : une panne sur l'une n'empêche jamais les autres de
s'exécuter, ni le cycle suivant de démarrer.

Une lecture `critical` (tous les capteurs en panne, tout est `null`) suit
exactement le même chemin — rien n'est filtré ni corrigé à aucune étape
(voir [DATA-02 / issue #16](../packages/mockapi-client) pour cet
invariant lecture-seule).

## Démarrer l'infra nécessaire

`consumption_readings` est créée par une migration Alembic
(`apps/core_api/alembic/versions/0e803d9159b4_create_consumption_readings.py`,
gérée avec les autres tables — voir [archi_database.md](archi_database.md)),
appliquée automatiquement au démarrage du conteneur `core_api`
(`alembic upgrade head`, voir son Dockerfile). Il faut donc lancer
`core_api` au moins une fois avant le worker ETL, même si celui-ci ne
l'appelle jamais directement :

```bash
docker compose up -d postgres minio minio-init redis core_api
```

`core_api` dépend à son tour de `prediction`/`recommendation` dans
`docker-compose.yml` (`depends_on`) — tant qu'ils n'ont pas de Dockerfile,
appliquer la migration à la main suffit :

```bash
docker compose build core_api
docker run --rm --network enervision_enervision-net \
  -e DATABASE_URL="postgresql+psycopg://enervision:changeme@postgres:5432/enervision" \
  enervision-core_api sh -c "alembic upgrade head"
```

## Lancer le worker en local

```bash
cd apps/etl_worker
cp .env.example .env   # puis ajuster si besoin (adresse de l'API mock, etc.)
python -m pip install -r requirements.txt -r requirements-dev.txt
python main.py
```

Une ligne de log JSON par lecture traitée, à chaque cycle :

```json
{"site": "SITE001", "status": "inserted", "data_quality": "good", "object_key": "2026-09-15/SITE001_20260915T151204246264.json"}
```

`status` vaut `"duplicate"` si la ligne existait déjà en base,
`"raw_write_error"`/`"db_error"`/`"alert_publish_error"` si l'une des
trois destinations était indisponible à ce cycle-là (le worker continue,
il ne plante jamais sur une panne ponctuelle).

## Lancer les tests unitaires

```bash
cd apps/etl_worker
python -m pytest -v
```

> Si `pytest` (sans `python -m`) dit "commande introuvable", c'est que le
> dossier `Scripts`/`bin` de ton interpréteur n'est pas sur le PATH —
> `python -m pytest` fonctionne toujours.

## Vérifier

| Point | Comment vérifier |
|---|---|
| 7 nouveaux objets JSON dans `raw` par cycle (un par site, jamais écrasés) | Console web http://localhost:9001 (identifiants dans `.env`) → bucket `raw` |
| Lignes chargées dans Postgres | `docker compose exec postgres psql -U enervision -d enervision -c "SELECT count(*) FROM consumption_readings;"` |
| Une lecture `critical` est stockée, pas ignorée | `... WHERE data_quality = 'critical'` (aléatoire côté API mock, peut prendre plusieurs minutes à apparaître) |
| Une alerte est publiée sur `critical` | `docker compose exec redis redis-cli XRANGE alert.detected - +` |
| Redémarrer ne crée aucun doublon | Noter `SELECT count(*)`, redémarrer le worker, laisser tourner un cycle, recompter : ne doit ni reculer ni sauter anormalement |

## Dépannage rapide

- **`docker compose up` échoue en construisant `prediction`/`recommendation`** :
  normal, ces apps n'ont pas encore de code ni de Dockerfile (autre
  ticket) — cible uniquement les services nécessaires, comme ci-dessus.
- **`.env` disparaît régulièrement** : vérifier qu'aucun script/outil ne
  fait de `git clean` ou ne le supprime explicitement — `.env` n'est
  jamais touché par les commandes git normales (il est dans
  `.gitignore`).
