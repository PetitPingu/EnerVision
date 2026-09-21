# Monitoring — Prometheus + Grafana

## Objectif

Disposer d'indicateurs de performance sur le socle d'infrastructure
(TimescaleDB, Redis, MinIO, Traefik) pour détecter une dérive ou une panne
avant qu'elle n'impacte l'ETL ou l'API. C'est un monitoring **infra**, pas
applicatif : il ne couvre pas encore les métriques métier de `core_api` ou
`etl_worker`.

## Architecture

```
[postgres] --\
[redis]     --+--> exporters Prometheus --> [prometheus] --> [grafana]
[minio]     --/ (métriques natives)
[traefik]  --/  (métriques natives)
```

- **Prometheus** scrape toutes les 15s les cibles définies dans
  [monitoring/prometheus/prometheus.yml](../monitoring/prometheus/prometheus.yml).
- **postgres-exporter** et **redis-exporter** traduisent l'état de
  TimescaleDB et Redis en métriques Prometheus (ni Postgres ni Redis
  n'exposent nativement un endpoint `/metrics`).
- **MinIO** et **Traefik** exposent nativement un endpoint Prometheus — pas
  d'exporter tiers nécessaire. Côté MinIO, l'endpoint reste protégé par JWT
  (comportement par défaut) : le service `minio-metrics-token` génère ce
  token au démarrage (`mc admin prometheus generate`) dans un volume partagé,
  que Prometheus monte en lecture seule et référence via `bearer_token_file`.
- **Grafana** lit Prometheus comme datasource unique et charge
  automatiquement un dashboard unique versionné dans le repo
  ([monitoring/grafana/dashboards/overview.json](../monitoring/grafana/dashboards/overview.json))
  via le provisioning as-code
  ([monitoring/grafana/provisioning](../monitoring/grafana/provisioning)) :
  aucune configuration manuelle requise, reproductible pour toute l'équipe.

## Accès

Une fois `docker compose up -d` lancé :

| Service | URL |
|---|---|
| Grafana | http://localhost:${GRAFANA_PORT:-3001} (login: `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD`, voir `.env`) |
| Prometheus | http://localhost:${PROMETHEUS_PORT:-9090} |

Le dashboard **EnerVision - Vue d'ensemble infra** est dans le dossier
**EnerVision** de Grafana, organisé en 4 sections repliables (une rangée
Grafana par service) : PostgreSQL/TimescaleDB, Redis, MinIO, Traefik.

## Sécurité du port MinIO et des métriques

Deux protections en place pour l'endpoint metrics MinIO (déploiement prévu
prochainement, donc traité comme un vrai risque et pas seulement théorique) :

- **Port 9000 bindé sur `127.0.0.1` uniquement**
  (`"127.0.0.1:${MINIO_PORT:-9000}:9000"` dans `docker-compose.yml`) : les
  autres containers du réseau `enervision-net` continuent d'accéder à MinIO
  normalement (le binding host n'affecte pas le réseau docker interne), et
  le workflow dev où `etl_worker` tourne hors docker-compose
  (`MINIO_ENDPOINT=localhost:9000`, voir `apps/etl_worker/.env.example`)
  continue de fonctionner. Seul l'accès depuis le réseau externe est coupé.
- **Endpoint `/minio/v2/metrics/cluster` protégé par JWT** (comportement
  par défaut de MinIO, pas de `MINIO_PROMETHEUS_AUTH_TYPE=public`) : sans le
  token généré par `minio-metrics-token`, l'endpoint renvoie `403`. Vérifié
  en pratique (`curl` sans token → 403, avec le token → 200).

Reste à changer avant un déploiement réel : les mots de passe par défaut
(`POSTGRES_PASSWORD`, `MINIO_ROOT_PASSWORD`, `GRAFANA_ADMIN_PASSWORD`...)
qui valent tous `changeme*` dans `.env.example`, cohérent avec le reste du
projet mais à ne jamais garder en prod.

## Indicateurs suivis

| Section | Indicateurs | Pourquoi |
|---|---|---|
| PostgreSQL / TimescaleDB | up, connexions actives, cache hit ratio, commit/rollback par seconde, lignes lues/écrites | Détecter une saturation de connexions, un cache inefficace (I/O disque en hausse) ou un taux de rollback anormal signalant des requêtes en échec |
| Redis | up, clients connectés, mémoire utilisée, commandes/s, hit/miss ratio | Redis porte le stream `alert.detected` (transitions data_quality de l'ETL, lu par `core_api` en SSE) : une dérive mémoire ou un up=0 casse la détection d'alerte en temps réel |
| MinIO | noeuds en ligne, usage vs capacité, espace libre, requêtes S3/s | Le bucket raw reçoit en continu les lectures de l'ETL ; surveiller l'espace évite une panne d'écriture silencieuse |
| Traefik | requêtes/s par entrypoint et code HTTP, connexions ouvertes, latence p95 par service, taux d'erreurs 5xx | Vue de bout en bout du trafic entrant vers `core_api` : latence et taux d'erreur sont les deux signaux qui remontent le plus vite un incident |

## Étendre le monitoring

Pour ajouter des métriques applicatives (`core_api`, `etl_worker`) plus tard :

1. Instrumenter le service (ex. `prometheus-fastapi-instrumentator` pour
   FastAPI, ou un `prometheus_client` custom pour l'ETL).
2. Ajouter une cible `scrape_configs` dans
   `monitoring/prometheus/prometheus.yml`.
3. Ajouter une nouvelle rangée (`type: row`) et ses panels dans
   `monitoring/grafana/dashboards/overview.json` — rechargé automatiquement
   au prochain redémarrage de Grafana (pas de manipulation UI requise).
