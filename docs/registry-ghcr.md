# Registry GHCR — images applicatives

Les images Docker des services EnerVision sont **construites et publiées en CI** (GitHub Actions cloud) vers **GitHub Container Registry** (`ghcr.io`). Le **déploiement Terraform** s'exécute sur la **VM via un self-hosted runner** (la VM n'est pas accessible depuis Internet).

| Workflow | Runner | Rôle |
|----------|--------|------|
| [images-build-push.yml](../.github/workflows/images-build-push.yml) | `ubuntu-latest` | Build + push GHCR |
| [deploy.yml](../.github/workflows/deploy.yml) | `self-hosted` (`enervision-vm`) | `terraform apply` sur la VM |
| [runner-check.yml](../.github/workflows/runner-check.yml) | `self-hosted` | Vérifier Docker/Terraform/réseau |

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
| `sha-<commit>` | Immutable — deploy auto après merge |
| `dev` / `main` | Pointeur par branche |
| `pr-<numéro>` | Tests PR (temporaire, push activé sur PR) |
| `latest` | Uniquement sur `main` |

## Self-hosted runner (VM)

La VM initie les connexions **sortantes** vers GitHub — pas besoin d'ouvrir SSH depuis Internet.

### Prérequis VM

- Docker installé, utilisateur runner dans le groupe `docker`
- Terraform `>= 1.5`
- Accès sortant vers `github.com` et `ghcr.io`

### Installation

1. Repo → **Settings** → **Actions** → **Runners** → **New self-hosted runner**
2. Sur la VM (via SSH interne) :

```bash
mkdir -p ~/actions-runner && cd ~/actions-runner

# URL et version : celles affichées par GitHub
curl -o actions-runner-linux-x64.tar.gz -L https://github.com/actions/runner/releases/download/vX.XXX.X/actions-runner-linux-x64-X.XXX.X.tar.gz
tar xzf actions-runner-linux-x64.tar.gz

./config.sh --url https://github.com/PetitPingu/EnerVision \
  --token <TOKEN_AFFICHE_PAR_GITHUB> \
  --name enervision-vm \
  --labels enervision-vm,self-hosted,linux \
  --unattended

sudo ./svc.sh install
sudo ./svc.sh start
```

3. Vérifier : runner **Idle** dans Settings → Actions → Runners
4. Tester : Actions → **Self-hosted runner check** → Run workflow

Label attendu par les workflows : **`enervision-vm`**

### État Terraform persistant

Le workflow sauvegarde `terraform.tfstate` dans `~/enervision-deploy/state/` sur la VM (hors répertoire de travail éphémère du runner).

Variable repo optionnelle : `TF_STATE_DIR` (chemin absolu alternatif).

## Secrets GitHub

| Secret | Description |
|--------|-------------|
| `GHCR_USERNAME` | Compte GitHub avec `read:packages` |
| `GHCR_READ_TOKEN` | PAT classic `read:packages` |
| `DB_PASSWORD` | Mot de passe Postgres |
| `MINIO_ROOT_PASSWORD` | Mot de passe MinIO |
| `ENERVISION_API_USERNAME` | Identifiant API mock |
| `ENERVISION_API_PASSWORD` | Mot de passe API mock |
| `GRAFANA_ADMIN_PASSWORD` | Mot de passe Grafana |
| `DEPLOY_HOST` | Hostname/IP affiché dans les outputs (URL d'accès à l'app) |

**Variable** : `DASHBOARD_API_BFF_URL` (URL `core_api` au build dashboard)

Les secrets `VM_HOST`, `SSH_*` ne sont **plus nécessaires** pour le deploy (runner local).

### Créer `GHCR_READ_TOKEN`

GitHub → Settings → Developer settings → PAT (classic) → scopes `read:packages` (+ `repo` si privé).

## Déploiement

### Automatique (merge sur `dev` / `main`)

1. Build + push images (`sha-<commit>`)
2. Deploy déclenché (`workflow_run`) sur le runner VM
3. `terraform apply` avec `image_tag=sha-<commit>`

### Manuel (tests PR)

Actions → **Deploy (Terraform + GHCR)** → Run workflow → tag `pr-168`.

### Étapes du job deploy

1. Checkout du repo sur la VM
2. Restauration de `terraform.tfstate` depuis `~/enervision-deploy/state/`
3. `docker login ghcr.io`
4. `terraform apply` (`build_images_locally=false`)
5. Sauvegarde du state

## Terraform (variables)

| Variable | Deploy CI |
|----------|-----------|
| `build_images_locally` | `false` |
| `image_tag` | `sha-<commit>` ou `pr-<n>` |
| `docker_host` | `unix:///var/run/docker.sock` |
| `ghcr_username` / `ghcr_read_token` | depuis secrets |

## Dépannage

| Problème | Action |
|----------|--------|
| Job en attente indéfiniment | Runner offline — `sudo ./svc.sh status` sur la VM |
| `No runner matching...` | Vérifier le label `enervision-vm` |
| `unauthorized` pull GHCR | `GHCR_READ_TOKEN` / `docker login` |
| Image introuvable | Tag inexistant — lancer le build CI d'abord |
| State perdu | Vérifier `~/enervision-deploy/state/terraform.tfstate` |

## À faire plus tard

- Retirer le push sur PR du workflow build
- Backend Terraform distant (optionnel)
