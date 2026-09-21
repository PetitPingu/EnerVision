# Registry GHCR — images applicatives

Les images Docker des services EnerVision sont **construites et publiées en CI** (GitHub Actions) vers **GitHub Container Registry** (`ghcr.io`). Aucun push manuel n'est requis.

Workflow : [`.github/workflows/images-build-push.yml`](../.github/workflows/images-build-push.yml)

## Convention de nommage

| Élément | Valeur |
|---------|--------|
| Registry | `ghcr.io` |
| Owner GitHub | `petitpingu` (minuscules, requis par GHCR) |
| Préfixe | `ghcr.io/petitpingu/enervision` |
| Exemple | `ghcr.io/petitpingu/enervision/core_api:sha-abc123…` |

Services publiés (contexte de build = **racine du repo**) :

| Service | Dockerfile |
|---------|------------|
| `core_api` | `apps/core_api/Dockerfile` |
| `prediction` | `apps/prediction/Dockerfile` |
| `recommendation` | `apps/recommendation/Dockerfile` |
| `etl_worker` | `apps/etl_worker/Dockerfile` |
| `dashboard` | `apps/dashboard/Dockerfile` |
| `mlflow` | `mlflow/Dockerfile` |

Les images tierces (Postgres, Traefik, MinIO, etc.) restent tirées depuis leurs registries publiques.

## Tags produits par la CI

Sur **push** vers `dev` ou `main` :

| Tag | Exemple | Usage |
|-----|---------|--------|
| `sha-<commit>` | `sha-a1b2c3d4e5f6…` | Immutable, pour Terraform / rollback |
| `<branche>` | `dev`, `main` | Pointeur mobile par environnement |
| `latest` | — | Uniquement sur `main` |

Sur **pull request** (temporaire, pour tests) : push activé avec le tag `pr-<numéro>` (ex. `pr-168`). À retirer une fois GHCR validé.

## Authentification

### CI (push)

Le workflow utilise le `GITHUB_TOKEN` fourni automatiquement par GitHub Actions, avec :

```yaml
permissions:
  packages: write
```

Pas de PAT personnel ni de `gh auth refresh` côté développeur.

### VM (pull, étape deploy — à venir)

Sur le serveur on-premise, un PAT en **lecture seule** (`read:packages`) sera injecté via GitHub Secrets au moment du déploiement Terraform :

```bash
echo "$GHCR_READ_TOKEN" | docker login ghcr.io -u <username> --password-stdin
docker pull ghcr.io/petitpingu/enervision/core_api:sha-...
```

## Variable repository : dashboard

Le dashboard Next.js embarque `NEXT_PUBLIC_API_BFF_URL` au **build**. Définir la variable de dépôt GitHub :

- **Nom** : `DASHBOARD_API_BFF_URL`
- **Valeur** : URL publique de `core_api` pour l'environnement cible (ex. `http://<host-vm>:8000`)

Si absente, la CI utilise `http://localhost:8000` par défaut.

## Vérification après le premier push

1. Ouvrir [Packages — PetitPingu](https://github.com/orgs/PetitPingu/packages)
2. Confirmer l'apparition des packages `enervision/<service>`
3. **Package settings** → lier au dépôt `EnerVision` si nécessaire
4. **Manage Actions access** → autoriser le dépôt

## Dépannage CI

| Problème | Cause probable | Action |
|----------|----------------|--------|
| `permission_denied` sur push | `packages: write` manquant | Vérifier le bloc `permissions` du workflow |
| Package invisible | Permissions org | Lier le package au repo |
| Dashboard appelle la mauvaise API | Mauvaise URL au build | Définir `DASHBOARD_API_BFF_URL` |
| Build échoue sur `packages/` | Contexte incorrect | Le `context` doit rester `.` (racine) |

## Terraform

Variables dans `infra/variables.tf` :

| Variable | Défaut | Description |
|----------|--------|-------------|
| `build_images_locally` | `true` | `false` en CI/VM pour pull GHCR |
| `image_registry_prefix` | `ghcr.io/petitpingu/enervision` | Préfixe des images |
| `image_tag` | `dev` | Tag à déployer |

Exemple pull GHCR (tests PR sans merge sur `dev`) :

```bash
cd infra
terraform apply \
  -var="build_images_locally=false" \
  -var="image_tag=pr-168"
```

Exemple deploy après merge sur `dev` :

```bash
terraform apply \
  -var="build_images_locally=false" \
  -var="image_tag=sha-<commit>"
```

## Prochaine étape

1. Auth GHCR sur la VM (`docker login` via secret `GHCR_READ_TOKEN`)
2. Workflow deploy CI : `terraform apply` avec `image_tag=sha-<commit>`
3. Retirer le push sur PR du workflow une fois les tests terminés
