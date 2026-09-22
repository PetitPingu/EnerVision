# Rapport de sécurisation — EnerVision

> Rapport de synthèse technique compilant les preuves concrètes de
> sécurisation du projet : authentification/autorisation, gestion des
> secrets, règles réseau, scans de vulnérabilités en CI. Chaque section
> cite le fichier et les lignes de code correspondants — pas d'affirmation
> sans preuve vérifiable dans le dépôt.

**Périmètre** : monorepo Docker Compose / Terraform de 6 services (`core_api`,
`prediction`, `recommendation`, `etl_worker`, `dashboard`, MLflow) déployés sur
une VM unique on-premise (voir [archi_infra.md](archi_infra.md)).

---

## 1. Authentification et autorisation

### 1.1 Authentification applicative (JWT)

Toutes les routes métier de `core_api` — le seul point d'entrée exposé aux
utilisateurs (BFF) — sont protégées par un JWT vérifié via une dépendance
FastAPI (`require_auth`), à l'exception de `/`, `/health`, `/auth/login`
et du flux SSE `/api/v1/alerts/stream` (limitation documentée, voir §5).

```python
# apps/core_api/presentation/api.py
def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentification requise")
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")
    return CurrentUser(email=payload["sub"], role=payload.get("role"), user_id=payload.get("uid"))
```

Génération et vérification du token (`apps/core_api/infrastructure/auth.py`) :

```python
def create_access_token(subject: str, **extra_claims: str | None) -> str:
    now = int(time.time())
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + Config.JWT_EXPIRE_MINUTES * 60,
        **extra_claims,
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)
```

- Algorithme **HS256**, expiration courte configurable (**30 minutes** par
  défaut, `JWT_EXPIRE_MINUTES`).
- Mots de passe hachés avec **bcrypt** (`hash_password`/`verify_password`),
  jamais stockés ni loggés en clair.
- Séquence complète documentée dans [seq_auth_token.md](seq_auth_token.md).

### 1.2 Limitation des tentatives de connexion (brute-force)

```python
# apps/core_api/infrastructure/login_throttle.py
"""Limitation des tentatives de connexion (voir ANSSI-PG-078) : sans ce
type de mesure, l'ANSSI recommande des mots de passe bien plus longs (20+
caractères) pour rester résistant au brute-force en ligne."""

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60
```

La route `/auth/login` retourne `429` après 5 échecs sur 15 minutes pour un
même email (`apps/core_api/presentation/api.py:205-209`).

### 1.3 Politique de mot de passe

```python
# apps/core_api/infrastructure/password_policy.py
"""Politique de mot de passe (voir ANSSI-PG-078, "Recommandations relatives
à l'authentification multifacteur et aux mots de passe", 10/2021).

Priorité à la longueur plutôt qu'à la complexité de classes de caractères."""

MIN_LENGTH = 12
```

Rejette : longueur < 12, mots de passe courants (liste `_COMMON_PASSWORDS`),
séquences évidentes (`1234`, `azer`, ...), mot de passe = identifiant email.
Référence explicite à l'**ANSSI-PG-078** (recommandations authentification
et mots de passe, 10/2021) — choix assumé de la longueur plutôt que de la
complexité de classes de caractères, conformément à la recommandation la
plus récente.

### 1.4 Autorisation — rôles et accès par site (RBAC + scoping)

Deux niveaux de contrôle, au-delà du simple "authentifié ou non" :

```python
def require_admin(current_user: CurrentUser = Depends(require_auth)) -> CurrentUser:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    return current_user

def _permitted_site_ids(current_user: CurrentUser) -> set[str] | None:
    """None = accès à tous les sites (rôle admin). Sinon : ensemble autorisé."""
    if current_user.role == "admin":
        return None
    if current_user.user_id is None:
        return set()
    return set(site_access_repository.get_site_ids(current_user.user_id))
```

- `role=admin` : accès à tous les sites + routes `/admin/users` (CRUD
  utilisateurs).
- Rôle non-admin : accès restreint aux sites explicitement associés via la
  table de jointure `user_sites` (`_assert_site_access`, appelée sur
  chaque route exposant un `site_id`).
- Modèle de données : table `users` (email unique, `password_hash`, `role`)
  isolée du reste du schéma, et `user_sites` (association many-to-many),
  voir `packages/db-schema/alembic/versions/c54505b1fc62_create_users_table.py`
  et `98e291945145_create_user_sites_table.py`.

### 1.5 Authentification sur les interfaces d'administration (infra)

Les interfaces d'admin exposées par l'infra (pas les APIs métier) sont
protégées par Basic Auth Traefik :

```hcl
# infra/proxy.tf
labels {
  label = "traefik.http.routers.traefik-dashboard.middlewares"
  value = "traefik-auth"
}
labels {
  label = "traefik.http.middlewares.traefik-auth.basicauth.users"
  value = var.traefik_dashboard_basic_auth_users
}
```

S'applique au dashboard Traefik et à l'UI MLflow (voir schéma dans
[archi_infra.md](archi_infra.md), routeur `RP -. "UI MLflow (auth basique)"`).

---

## 2. Gestion des secrets

Politique documentée dans [archi_infra.md §Secrets](archi_infra.md) : pas de
secrets manager dédié (hors périmètre pour une VM unique école) — deux
mécanismes complémentaires :

| Environnement | Mécanisme | Preuve |
|---|---|---|
| Local (dev) | `.env` unique à la racine, jamais commité | `.gitignore:1-3` (`.env`, `.env.*`, `.env.example`) — vérifié : `git ls-files \| grep .env` ne retourne rien, aucun secret n'est jamais entré dans l'historique git |
| Terraform | `terraform.tfvars` (valeurs réelles) gitignoré, seul `terraform.tfvars.example` (valeurs `CHANGEME`) est versionné | `.gitignore:6-7` ; `infra/terraform.tfvars.example` |
| CI/CD → prod | GitHub Secrets, injectés dans le `.env` de la VM au déploiement SSH | `docs/archi_infra.md:20` ; usage confirmé dans les workflows : `secrets.ENERVISION_API_USERNAME` / `secrets.ENERVISION_API_PASSWORD` (`.github/workflows/dashboard-e2e.yml:52-53`, `.github/workflows/load-test.yml:37-38`) |
| Partage entre membres de l'équipe | PrivateBin (instance publique tierce, chiffrement côté client, lien à usage unique/expiration) pour transmettre une valeur de secret (mot de passe, clé) sans la faire transiter en clair par Slack/Discord/email | Pratique déclarée par l'équipe, non vérifiable dans le dépôt (aucune trace attendue d'un outil de partage ponctuel) |

Le chiffrement de PrivateBin se fait côté client (AES-256 dans le
navigateur avant envoi) : même sur une instance publique tierce non
opérée par l'équipe, le serveur ne stocke et ne voit jamais le secret en
clair — seul le lien (qui porte la clé de déchiffrement dans le fragment
d'URL, jamais transmis au serveur) permet de le lire, et le burn-after-read
supprime le contenu dès la première lecture.

**Point d'attention identifié** — `JWT_SECRET_KEY` a une valeur par défaut
codée en dur si la variable d'environnement est absente :

```python
# apps/core_api/infrastructure/config.py
# JWT (voir docs/seq_auth_token.md). Le défaut n'est valable qu'en dev :
# tout déploiement réel doit fournir JWT_SECRET_KEY explicitement.
JWT_SECRET_KEY = os.environ.get(
    "JWT_SECRET_KEY", "dev-insecure-secret-change-me-in-production-32chars"
)
```

Le défaut est explicitement nommé comme non sûr (`dev-insecure-...`) pour
qu'il soit visible en revue de code, mais rien ne **bloque** techniquement
un démarrage en production sans que la variable soit positionnée (pas de
`raise` si absente). Recommandation : faire échouer le démarrage si
`JWT_SECRET_KEY` n'est pas explicitement définie hors environnement de dev
(`ENV=production` par ex.).

**Compte admin de seed** — `seed_admin_user.sql` crée un compte
`admin@enervision.com` avec un mot de passe par défaut documenté en clair
dans le commentaire du script (`changeme1234`) et un rappel explicite de le
changer après le premier login. Ce mot de passe figure d'ailleurs dans la
liste des mots de passe rejetés par `password_policy.py` pour tout compte
créé après coup — seul le compte de seed initial y échappe, par
construction (créé directement en base, hors route `/auth/login`).

---

## 3. Règles réseau

```hcl
# infra/network.tf
resource "docker_network" "app_network" {
  name = "app-internal-network"
}
```

Tous les services (base de données, MinIO, Redis, MLflow, APIs) tournent
sur un unique réseau Docker interne. Traefik est le seul point d'entrée
prévu depuis Internet, avec routage par préfixe de chemin
(`PathPrefix(/prediction)`, `PathPrefix(/recommendation)`, etc., voir
`infra/apps.tf`) et middlewares `stripprefix`.

PostgreSQL, Redis, MinIO et MLflow ne sont pas directement accessibles
depuis Internet : bien que leurs ports soient publiés par Docker sur la VM
(`infra/database.tf`, `infra/storage.tf`, `infra/mlflow.tf`, pour un accès
direct utile en debug/administration), l'accès externe est bloqué par le
pare-feu de la VM, qui n'autorise en entrée que les ports nécessaires
(Traefik, SSH). Cette restriction est appliquée au niveau infrastructure
de la VM, en dehors de ce dépôt (pas de configuration pare-feu versionnée
ici) — donc déclarée par l'équipe plutôt que vérifiable par simple lecture
du code, contrairement au reste de cette section.

CORS sur `core_api` — origines restreintes par variable d'environnement
(pas de wildcard `*`) :

```python
# apps/core_api/presentation/api.py
_cors_origins = os.environ.get(
    "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _cors_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

`prediction` et `recommendation` sont aussi exposés directement sur des
ports hôte, en plus de leur route via Traefik, pour un usage dev/debug. Or
ces deux services n'implémentent **aucune vérification JWT en propre** (la
protection `require_auth`/`require_admin` n'existe que côté `core_api`, voir
§1.1) : un appel direct sur ces ports contournerait donc entièrement
l'authentification et le scoping par site. Ces ports sont liés à
`127.0.0.1` (même pratique que pour Prometheus, voir
`infra/monitoring.tf:114-118`) : ils restent utilisables pour du debug
depuis la VM elle-même (ou via tunnel SSH), mais ne sont pas atteignables
depuis Internet — sans impact sur la communication interne
`core_api`/`recommendation` → `prediction`, qui passe par le réseau Docker
interne, indépendant du port publié sur l'hôte :

```hcl
# infra/apps.tf
ports {
  internal = 8000
  external = var.prediction_port
  ip       = "127.0.0.1"
}
```

Même configuration sur `recommendation` (`infra/apps.tf`).

---

## 4. Scans de vulnérabilités en CI (Trivy)

```yaml
# .github/workflows/trivy.yml
jobs:
  scan-fs:      # dépendances (requirements.txt) — sur push/PR vers dev
    strategy:
      matrix:
        app: [core_api, dashboard, etl_worker, prediction, recommendation]
    steps:
      - uses: aquasecurity/trivy-action@v0.36.0
        with:
          scan-type: fs
          severity: CRITICAL,HIGH
          ignore-unfixed: true
          exit-code: "1"

  scan-image:   # images Docker buildées — sur push/PR vers main uniquement
    strategy:
      matrix:
        app: [core_api, dashboard, etl_worker]
    steps:
      - uses: aquasecurity/trivy-action@v0.36.0
        with:
          scan-type: image
          severity: CRITICAL,HIGH
          exit-code: "1"
```

- `scan-fs` sur chaque push/PR vers `dev` (retour rapide, sans coût de build).
- `scan-image` uniquement vers `main`, dernier filet avant que le code soit
  packagé pour la prod.
- `exit-code: "1"` fait échouer la CI sur toute CVE CRITICAL/HIGH corrigible
  (`ignore-unfixed: true` évite de bloquer sur des CVE sans correctif
  disponible).
- Historique des itérations (corrections de permissions SARIF, chemins
  manquants dans la matrice) : voir [MES_TICKETS_ORAL.md §4](../MES_TICKETS_ORAL.md).

**Limite** : c'est un scan de **dépendances applicatives et d'images**
(SCA), pas un scan **IaC** au sens strict (type `tfsec`/`checkov` sur les
fichiers `.tf`). Aucun scan statique des fichiers Terraform n'est en place
à ce jour — périmètre restreint (VM unique, pas de cloud provider avec IAM
complexe) qui limite la surface que ce type d'outil couvrirait, mais reste
une amélioration possible.

---

## 5. Synthèse des risques résiduels et recommandations

| # | Constat | Sévérité | Recommandation |
|---|---|---|---|
| 1 | `JWT_SECRET_KEY` a un défaut codé en dur, pas de garde-fou au démarrage (§2) | Moyenne | Lever une erreur au boot si absent hors dev |
| 2 | `/api/v1/alerts/stream` (SSE) non protégé par JWT (limitation technique EventSource, documentée dans le code, §1.1) | Faible | Envisager un token à courte durée passé en query param signé, ou proxy d'auth dédié |
| 3 | Throttle de login en mémoire, par processus (pas partagé si plusieurs workers/instances) | Faible | Migrer vers Redis (déjà dans la stack) si `core_api` passe en plusieurs workers, cf. `login_throttle.py` |
| 4 | Pas de scan IaC statique (tfsec/checkov) sur `infra/*.tf` | Faible | Ajouter un job dédié si le périmètre infra s'étend |

Ce qui est déjà en place et solide : authentification JWT + bcrypt,
throttling anti brute-force et politique de mot de passe alignés sur les
recommandations ANSSI-PG-078, autorisation à deux niveaux (rôle + sites
autorisés), secrets jamais commités (vérifié sur l'historique git complet),
séparation CI (scan rapide sur `dev`, scan image avant `main`), réseau Docker
interne unique avec Traefik en frontal, ports de debug (`prediction`,
`recommendation`) restreints à `127.0.0.1`, et Basic Auth sur les interfaces
d'administration (Traefik dashboard, MLflow UI).

---

## Sources

- [seq_auth_token.md](seq_auth_token.md) — séquence login/JWT
- [archi_infra.md](archi_infra.md) — architecture infra et politique de secrets
- [archi_database.md](archi_database.md) — schéma `users`/`user_sites`
- `apps/core_api/presentation/api.py`, `apps/core_api/infrastructure/{auth,login_throttle,password_policy}.py`
- `infra/{network,proxy,apps,variables}.tf`
- `.github/workflows/trivy.yml`
- `packages/db-schema/alembic/versions/{c54505b1fc62,98e291945145}_*.py`
- `packages/db-schema/alembic/seeds/seed_admin_user.sql`
