# Socle de stockage — TimescaleDB + MinIO

Fondation de stockage du projet EnerVision, définie dans le `docker-compose.yml`
à la racine avec le reste des services applicatifs : le service `postgres`
tourne sur l'image TimescaleDB pour les séries temporelles, et `minio` fournit
le stockage objet (compatible S3) pour les données brutes, fichiers exportés,
modèles, etc.

## Prérequis

- Docker
- Docker Compose (plugin `docker compose`)

## Démarrage

```bash
cp .env.example .env
# ajuster les identifiants dans .env si besoin
docker compose up -d
```

Vérifier que les services sont sains :

```bash
docker compose ps
```

## Services

| Service      | Rôle                                     | Port hôte (défaut) |
|--------------|-------------------------------------------|---------------------|
| postgres     | Base PostgreSQL + extension TimescaleDB   | 5432 |
| minio        | API S3                                    | 9000 |
| minio        | Console web                               | 9001 |
| minio-init   | Job ponctuel qui crée les buckets         | — |

Les identifiants (utilisateur/mot de passe PostgreSQL, clés MinIO) et les
ports sont configurables via le fichier `.env` (voir `.env.example`).

## TimescaleDB

- Le service `postgres` utilise l'image `timescale/timescaledb` (et non
  `postgres:16-alpine`) pour que l'extension `timescaledb` soit disponible ;
  le nom du service reste `postgres` pour ne pas casser les références des
  autres services (`core_api`, `prediction`, `recommendation`, `etl_worker`).
- L'extension `timescaledb` et le schéma `enervision`, ainsi que toutes
  les tables applicatives, sont créés par les migrations Alembic du
  package partagé `packages/db-schema/` (indépendant de toute app),
  appliquées automatiquement au démarrage de `core_api`
  (`alembic -c /packages/db-schema/alembic.ini upgrade head`) — mais
  applicables par n'importe quel autre service de la même façon.
- Connexion : `psql postgresql://<POSTGRES_USER>:<POSTGRES_PASSWORD>@localhost:<POSTGRES_PORT>/<POSTGRES_DB>`

## MinIO

- Au démarrage, le service `minio-init` crée automatiquement les buckets
  listés dans la variable `MINIO_BUCKETS` du `.env` (par défaut : `raw`,
  `processed`, `models`, `backups`).
- Console web : http://localhost:9001 (identifiants `MINIO_ROOT_USER` /
  `MINIO_ROOT_PASSWORD`).

## Persistance

Les données sont conservées dans des volumes Docker nommés (`postgres-data`,
`minio-data`), donc elles survivent à un `docker compose down`.

Pour repartir de zéro (⚠️ supprime les données) :

```bash
docker compose down -v
```
