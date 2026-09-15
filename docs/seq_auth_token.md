# Diagramme de séquence de l'authentification et du token JWT

#### Mermaid

```mermaid
sequenceDiagram
    autonumber
    participant Client as Dashboard (Next.js)
    participant BFF as API BFF (FastAPI)
    participant PG as PostgreSQL (users)
    participant Pred as Service Prediction
    participant Reco as Service Recommandation
    participant ETL as Worker ETL

    Client->>BFF: POST /auth/login {email, password}
    BFF->>PG: SELECT user WHERE email=...
    PG-->>BFF: Utilisateur + hash du mot de passe
    BFF->>BFF: Vérifie le hash (bcrypt/argon2)
    alt Identifiants valides
        BFF->>BFF: Génère un JWT (exp courte, signé)
        BFF-->>Client: 200 OK + JWT
        Client->>Client: Stocke le JWT (mémoire / cookie httpOnly)
    else Identifiants invalides
        BFF-->>Client: 401 Unauthorized
    end

    Note over Client,BFF: Sur chaque appel suivant
    Client->>BFF: GET /... (Authorization: Bearer JWT)
    BFF->>BFF: Vérifie signature + expiration du JWT
    alt JWT valide
        BFF->>Pred: Appel interne (réseau Docker privé, pas de JWT)
        BFF->>Reco: Appel interne (réseau Docker privé, pas de JWT)
        Note over BFF,ETL: Le Worker ETL n'expose aucune API,<br/>il n'est pas concerné par le JWT
    else JWT invalide / expiré
        BFF-->>Client: 401 Unauthorized
    end

    Note over BFF,Reco: Seul le X-Request-Id (corrélation) circule entre services internes.<br/>Pas de JWT service-à-service : ils ne sont pas exposés publiquement<br/>(seul le BFF est derrière Traefik)
```

#### Diagramme

![image](images/seq_auth_token.png)