# Worker d'ingestion (issue #19)

Le worker `etl_worker` se limite à l'**ingestion** : un seul job planifié
(APScheduler, pas de cron externe), toutes les 60 secondes.

1. Un seul appel `GET /api/v1/readings?limit=7` (les dernières lectures,
   une par site).
2. Pour chaque lecture : écriture brute dans le bucket MinIO `raw`
   (`raw/{site_id}/{YYYY}/{MM}/{DD}/{HH}/{minutes}.json` — partitionné
   par site d'abord, puis par heure locale Europe/Paris).

L'insertion en base (`consumption_readings`) et la publication d'alertes
(Redis Streams) sont hors périmètre de ce worker — elles sont traitées
dans une branche séparée dédiée à la transformation.

Une lecture `critical` (tous les capteurs en panne, tout est `null`) suit
exactement le même chemin — rien n'est filtré ni corrigé
(voir [DATA-02 / issue #16](../packages/mockapi-client) pour cet
invariant lecture-seule).

## Démarrer l'infra nécessaire

Seul MinIO est requis pour ce worker :

```bash
docker compose up -d minio minio-init
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
{"site": "SITE001", "status": "written", "data_quality": "good", "object_key": "SITE001/2026/09/15/17/45.json"}
```

`status` vaut `"raw_write_error"` si MinIO était indisponible à ce
cycle-là (le worker continue, il ne plante jamais sur une panne
ponctuelle), ou `"error"` si l'API mock elle-même était injoignable.

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
| 7 nouveaux objets JSON dans `raw` par cycle (un par site) | Console web http://localhost:9001 (identifiants dans `.env`) → bucket `raw` |
| Une lecture `critical` est écrite, pas ignorée | Parcourir les objets récents d'un site dans la console MinIO (aléatoire côté API mock, peut prendre plusieurs minutes à apparaître) |

## Dépannage rapide

- **`.env` disparaît régulièrement** : vérifier qu'aucun script/outil ne
  fait de `git clean` ou ne le supprime explicitement — `.env` n'est
  jamais touché par les commandes git normales (il est dans
  `.gitignore`).
