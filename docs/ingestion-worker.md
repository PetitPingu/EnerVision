# Worker d'ingestion temps réel (issue #19)

Le worker `etl_worker` interroge l'API mock EnerVision toutes les 60
secondes pour tous les sites, et alimente en continu trois destinations
sans jamais perdre ni dupliquer une lecture :

1. **`readings_raw`** (Postgres/TimescaleDB) — la donnée structurée.
2. **Bucket MinIO `bronze`** — le JSON brut de chaque lecture, tel que
   reçu de l'API, horodaté (`bronze/YYYY/MM/DD/HH/{site_id}_{timestamp}.json`).
3. **Redis Streams (`reading.ingested`)** — un événement par lecture
   *nouvellement* insérée (pas de republication sur doublon), consommé
   plus tard par le service d'alerting.

Une lecture `critical` (tous les capteurs en panne, tout est `null`) est
stockée comme n'importe quelle autre — rien n'est filtré ni corrigé (voir
[DATA-02 / issue #16](../packages/mockapi-client) pour cet invariant
lecture-seule).

## Démarrer l'infra nécessaire

Pas besoin de `core_api`/`prediction`/etc. pour ce worker :

```bash
docker compose up -d postgres minio minio-init redis
```

Si Postgres avait déjà été démarré **avant** ce ticket, la table
`readings_raw` n'existe pas encore (les scripts de `db/init/` ne
s'exécutent qu'une fois, sur un volume vide) :

```bash
docker compose down -v
docker compose up -d postgres minio minio-init redis
```

## Lancer le worker en local

```bash
cd apps/etl_worker
cp .env.example .env   # puis ajuster si besoin (adresse de l'API mock, etc.)
python -m pip install -r requirements.txt -r requirements-dev.txt
python main.py
```

Une ligne de log JSON s'affiche par site à chaque cycle :

```json
{"site": "SITE001", "status": "inserted", "data_quality": "good", "object_key": "2026/09/15/12/SITE001_20260915T124828887095.json"}
```

`status` vaut `"duplicate"` si la ligne existait déjà (idempotence), ou
`"error"` si l'API mock ou l'infra était indisponible à ce cycle-là (le
worker continue, il ne plante jamais sur une erreur ponctuelle).

## Lancer les tests unitaires

```bash
cd apps/etl_worker
python -m pytest -v
```

> Si `pytest` (sans `python -m`) dit "commande introuvable", c'est que le
> dossier `Scripts`/`bin` de ton interpréteur n'est pas sur le PATH —
> `python -m pytest` fonctionne toujours.

## Vérifier les critères d'acceptation

| Critère | Comment vérifier |
|---|---|
| ≈ 70 lignes après 10 min (7 sites × 10 cycles) | `docker compose exec postgres psql -U enervision -d enervision -c "SELECT count(*) FROM readings_raw;"` |
| Une lecture `critical` est stockée, pas ignorée | `docker compose exec postgres psql -U enervision -d enervision -c "SELECT site_id, timestamp FROM readings_raw WHERE data_quality = 'critical' LIMIT 5;"` (aléatoire côté API mock, peut prendre plusieurs minutes à apparaître) |
| Redémarrer ne crée aucun doublon | Noter le `count(*)`, `docker compose restart etl_worker`, laisser tourner un cycle, recompter : ne doit ni reculer ni sauter anormalement |
| Objets JSON visibles dans MinIO | Console web http://localhost:9001 (identifiants dans `.env`) → bucket `bronze` |

Le nombre de lignes Postgres et le nombre d'événements Redis doivent
toujours être égaux :

```bash
docker compose exec redis redis-cli XLEN reading.ingested
```

## Dépannage rapide

- **`docker compose up` échoue en construisant `prediction`/`recommendation`** :
  normal, ces apps n'ont pas encore de code ni de Dockerfile (autre
  ticket) — cible uniquement les services nécessaires, comme ci-dessus.
- **`.env` disparaît régulièrement** : vérifier qu'aucun script/outil ne
  fait de `git clean` ou ne le supprime explicitement — `.env` n'est
  jamais touché par les commandes git normales (il est dans
  `.gitignore`).
