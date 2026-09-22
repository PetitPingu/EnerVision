# Diagramme de séquence de l'authentification et du token JWT

> **Statut : implémenté.** Route `/auth/login`, table `users` (+
> `user_sites` pour l'accès par site) et vérification JWT sur toutes les
> routes métier de `core_api` (sauf `/`, `/health`, `/auth/login` et le
> flux SSE `/api/v1/alerts/stream`, voir note en bas de page) — voir
> `apps/core_api/presentation/api.py` et
> `apps/core_api/infrastructure/{auth,login_throttle,password_policy}.py`.
> Synthèse des preuves dans [rapport_securisation.md](rapport_securisation.md).

Le hash du mot de passe utilise **bcrypt** (pas argon2). Le JWT (algorithme
**HS256**, expiration configurable via `JWT_EXPIRE_MINUTES`, 30 min par
défaut) embarque `role` et `uid` dans le payload en plus du `sub` (email),
pour que `core_api` connaisse le rôle et les sites autorisés de l'appelant
sans aller-retour base à chaque requête (voir `_permitted_site_ids` dans
`presentation/api.py`). Deux niveaux de contrôle après vérification du JWT :
un rôle (`admin` vs les autres, routes `/admin/users`) et un scoping par
site (`user_sites`, table de jointure) pour les routes qui exposent un
`site_id`. La route `/auth/login` est protégée par un throttle (5 tentatives
échouées / 15 min par email, voir `infrastructure/login_throttle.py`) et la
création de compte par une politique de mot de passe alignée sur
l'ANSSI-PG-078 (longueur ≥ 12, pas de mot de passe courant/séquence évidente,
voir `infrastructure/password_policy.py`).

#### Mermaid

```mermaid
sequenceDiagram
    autonumber
    participant Client as Dashboard (Next.js)
    participant Core as Core API (FastAPI)
    participant PG as PostgreSQL (users, user_sites)
    participant Pred as Service Prediction
    participant Reco as Service Recommandation
    participant ETL as Worker ETL

    Client->>Core: POST /auth/login {email, password}
    Core->>Core: Vérifie le throttle (max 5 échecs / 15 min pour cet email)
    alt Trop de tentatives récentes
        Core-->>Client: 429 Too Many Requests
    else
        Core->>PG: SELECT user WHERE email=...
        PG-->>Core: Utilisateur + hash du mot de passe (bcrypt)
        Core->>Core: Vérifie le hash bcrypt
        alt Identifiants valides
            Core->>Core: Génère un JWT (sub=email, role, uid, exp 30 min, HS256)
            Core-->>Client: 200 OK + JWT
            Client->>Client: Stocke le JWT (mémoire / cookie httpOnly)
        else Identifiants invalides
            Core->>Core: Enregistre l'échec (throttle)
            Core-->>Client: 401 Unauthorized
        end
    end

    Note over Client,Core: Sur chaque appel suivant
    Client->>Core: GET /... (Authorization: Bearer JWT)
    Core->>Core: Vérifie signature + expiration du JWT (require_auth)
    alt JWT valide
        Core->>Core: Vérifie rôle (require_admin sur /admin/users) et/ou<br/>accès au site_id demandé (user_sites, sauf rôle admin)
        Core->>Pred: Appel interne (réseau Docker privé, pas de JWT)
        Core->>Reco: Appel interne (réseau Docker privé, pas de JWT)
        Note over Core,ETL: Le Worker ETL n'expose aucune API,<br/>il n'est pas concerné par le JWT
    else JWT invalide / expiré / accès refusé
        Core-->>Client: 401 Unauthorized / 403 Forbidden
    end

    Note over Core,Reco: Seul le X-Request-Id (corrélation) circule entre services internes.<br/>Pas de JWT service-à-service en interne. Attention : prediction/recommendation<br/>n'ont pas non plus de JWT en propre — voir le risque réseau documenté<br/>dans rapport_securisation.md (ports directs restreints à 127.0.0.1)
```

**Note — flux SSE non authentifié** : `/api/v1/alerts/stream` ne passe pas
par `require_auth` (le front s'y connecte via `EventSource`, qui ne permet
pas de porter un header `Authorization`). C'est une limitation technique
documentée, pas un oubli — voir le risque résiduel #3 dans
[rapport_securisation.md](rapport_securisation.md).