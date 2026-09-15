# Worker ETL (issue #19)

Le worker `etl_worker` implémente les deux étages prévus dans
[docs/seq_etl.md](seq_etl.md), sur des scheduler internes (APScheduler,
pas de cron externe) :

1. **Ingestion** (toutes les 60 secondes) : un seul appel
   `GET /api/v1/readings?limit=7` (les dernières lectures, une par site),
   écrites telles quelles dans le bucket MinIO `raw`
   (`raw/{date}/{site_id}.json` — un fichier par site et par jour,
   écrasé à chaque nouvelle lecture).
2. **Transformation** (toutes les heures) : relit tous les fichiers du
   jour dans `raw`, les valide (mêmes modèles Pydantic que l'ingestion),
   et les charge dans `consumption_readings` (Postgres/TimescaleDB).

Une lecture `critical` (tous les capteurs en panne, tout est `null`) suit
exactement le même chemin — rien n'est filtré ni corrigé à aucune étape
(voir [DATA-02 / issue #16](../packages/mockapi-client) pour cet
invariant lecture-seule).

## Démarrer l'infra nécessaire

Pas besoin de `core_api`/`prediction`/etc. pour ce worker :

```bash
docker compose up -d postgres minio minio-init
```

Si Postgres avait déjà été démarré **avant** ce ticket, la table
`consumption_readings` n'existe pas encore (les scripts de `db/init/` ne
s'exécutent qu'une fois, sur un volume vide) :

```bash
docker compose down -v
docker compose up -d postgres minio minio-init
```

## Lancer le worker en local

```bash
cd apps/etl_worker
cp .env.example .env   # puis ajuster si besoin (adresse de l'API mock, etc.)
python -m pip install -r requirements.txt -r requirements-dev.txt
python main.py
```

Le job d'ingestion logge une ligne JSON par site à chaque cycle :

```json
{"site": "SITE001", "status": "written", "data_quality": "good", "object_key": "2026-09-15/SITE001.json"}
```

Le job de transformation logge un résumé par heure :

```json
{"job": "transform", "date": "2026-09-15", "files": 7, "inserted": 7, "duplicates": 0, "errors": 0}
```

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
| 7 objets JSON dans `raw` (un par site, écrasés à chaque cycle) | Console web http://localhost:9001 (identifiants dans `.env`) → bucket `raw` |
| Transformation chargée dans Postgres | `docker compose exec postgres psql -U enervision -d enervision -c "SELECT count(*) FROM consumption_readings;"` |
| Une lecture `critical` est stockée, pas ignorée | `... WHERE data_quality = 'critical'` (aléatoire côté API mock, peut prendre plusieurs minutes à apparaître) |
| Rejouer la transformation ne crée aucun doublon | Relancer le job (attendre l'heure suivante, ou l'appeler manuellement), recompter : ne doit pas augmenter |

## Dépannage rapide

- **`docker compose up` échoue en construisant `prediction`/`recommendation`** :
  normal, ces apps n'ont pas encore de code ni de Dockerfile (autre
  ticket) — cible uniquement les services nécessaires, comme ci-dessus.
- **`.env` disparaît régulièrement** : vérifier qu'aucun script/outil ne
  fait de `git clean` ou ne le supprime explicitement — `.env` n'est
  jamais touché par les commandes git normales (il est dans
  `.gitignore`).
