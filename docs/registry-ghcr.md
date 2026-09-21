# Registry GHCR — images applicatives

Les images Docker des services EnerVision sont **construites et publiées en CI** (GitHub Actions) vers **GitHub Container Registry** (`ghcr.io`).

| Workflow | Rôle |
|----------|------|
| [images-build-push.yml](../.github/workflows/images-build-push.yml) | Build + push GHCR |
| [deploy.yml](../.github/workflows/deploy.yml) | `terraform apply` sur la VM (pull GHCR) |

## Convention de nommage

| Élément | Valeur |
|---------|--------|
| Registry | `ghcr.io` |
| Owner GitHub | `petitpingu` (minuscules) |
| Préfixe | `ghcr.io/petitpingu/enervision` |
| Exemple | `ghcr.io/petitpingu/enervision/core_api:sha-abc123…` |

## Tags produits par la CI

| Tag | Usage |
|-----|--------|
| `sha-<commit>` | Immutable — utilisé par le deploy automatique |
| `dev` / `main` | Pointeur par branche |
| `pr-<numéro>` | Tests PR (temporaire, push activé sur PR) |
| `latest` | Uniquement sur `main` |

## Secrets GitHub (Settings → Secrets and variables → Actions)

Configurer avant le premier deploy :

| Secret | Description |
|--------|-------------|
| `VM_HOST` | IP ou hostname de la VM |
| `SSH_USER` | Utilisateur SSH |
| `SSH_PRIVATE_KEY` | Clé privée SSH (PEM, accès à la VM) |
| `SSH_PORT` | (optionnel) Port SSH, défaut `22` |
| `GHCR_USERNAME` | Compte GitHub avec `read:packages` |
| `GHCR_READ_TOKEN` | PAT classic avec `read:packages` |
| `DB_PASSWORD` | Mot de passe Postgres |
| `MINIO_ROOT_PASSWORD` | Mot de passe MinIO |
| `ENERVISION_API_USERNAME` | Identifiant API mock |
| `ENERVISION_API_PASSWORD` | Mot de passe API mock |
| `GRAFANA_ADMIN_PASSWORD` | Mot de passe Grafana |
| `DEPLOY_HOST` | (optionnel) Hostname public pour les outputs Terraform (sinon `VM_HOST`) |

**Variable** (non secrète) :

| Variable | Description |
|----------|-------------|
| `DASHBOARD_API_BFF_URL` | URL publique de `core_api` au build dashboard |

### Créer le PAT `GHCR_READ_TOKEN`

1. GitHub → Settings → Developer settings → Personal access tokens (classic)
2. Scopes : `read:packages` (+ `repo` si packages privés)
3. Coller la valeur dans le secret `GHCR_READ_TOKEN`

## Prérequis VM

- Docker installé et démarré
- Terraform `>= 1.5` installé
- Utilisateur SSH membre du groupe `docker`
- Port SSH accessible depuis les runners GitHub Actions

## Déploiement

### Automatique (après merge sur `dev` / `main`)

1. `Build and push images` termine avec succès
2. `Deploy (Terraform + GHCR)` se déclenche (`workflow_run`)
3. Tag déployé : `sha-<commit>` du push

### Manuel (tests PR sans merge)

Actions → **Deploy (Terraform + GHCR)** → **Run workflow** → tag `pr-168` (ou autre).

### Ce que fait le deploy

1. `rsync` du dossier `infra/` vers `~/enervision-deploy/infra/` sur la VM
2. `docker login ghcr.io` sur la VM
3. `terraform apply` avec `build_images_locally=false` et le tag choisi
4. État Terraform conservé sur la VM (`terraform.tfstate` local)

## Terraform (variables)

| Variable | Défaut | CI / VM |
|----------|--------|---------|
| `build_images_locally` | `true` | `false` |
| `image_tag` | `dev` | `sha-<commit>` ou `pr-<n>` |
| `ghcr_username` / `ghcr_read_token` | vide | depuis secrets |
| `vm_host` / `ssh_user` | vide | optionnel (apply local via SSH Docker) |

Apply local depuis un poste (sans workflow) :

```bash
cd infra
terraform apply \
  -var="build_images_locally=false" \
  -var="image_tag=pr-168" \
  -var="ghcr_username=VOTRE_USER" \
  -var="ghcr_read_token=ghp_..."
```

## Dépannage

| Problème | Action |
|----------|--------|
| `permission_denied` sur push CI | `packages: write` dans le workflow build |
| `unauthorized` sur pull VM | Vérifier `GHCR_READ_TOKEN` + `docker login` |
| Terraform ne trouve pas l'image | Vérifier que le tag existe (build CI terminé) |
| SSH échoue | Vérifier `SSH_PRIVATE_KEY`, firewall, `known_hosts` |
| `terraform: command not found` sur VM | Installer Terraform sur la VM |

## À faire plus tard

- Retirer le push sur PR du workflow build (une fois les tests terminés)
- Backend Terraform distant (optionnel, si plusieurs opérateurs)
