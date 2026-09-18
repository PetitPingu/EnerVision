"""API core_api : relaie (proxy) l'API mock EnerVision.

Couche présentation : traduit les requêtes HTTP en appels au port
SensorApiPort et sérialise les entités du domaine en JSON. Ne contient
aucune logique métier.

Lancer en local (depuis apps/core_api) :
    python -m uvicorn presentation.api:app --reload --port 8001

Puis ouvrir http://127.0.0.1:8001/docs pour explorer les endpoints.
"""

import os
from dataclasses import asdict
from typing import NamedTuple

import jwt
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from infrastructure.api_client import ApiMockClient
from infrastructure.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from infrastructure.login_throttle import is_locked_out, record_failed_attempt, reset_attempts
from infrastructure.password_policy import WeakPasswordError, validate_password_strength
from infrastructure.prediction_client import PredictionApiClient
from infrastructure.recommendation_client import RecommendationApiClient
from infrastructure.site_access_repository import SqlSiteAccessRepository
from infrastructure.user_repository import SqlUserRepository
from pydantic import BaseModel

app = FastAPI(
    title="EnerVision core_api",
    description="Relaie les endpoints de l'API mock EnerVision.",
    version="1.0.0",
)

_cors_origins = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _cors_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sensor_api = ApiMockClient()
prediction_api = PredictionApiClient()
recommendation_api = RecommendationApiClient()
user_repository = SqlUserRepository()
site_access_repository = SqlSiteAccessRepository()

_bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser(NamedTuple):
    email: str
    role: str | None
    user_id: str | None


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser:
    """Dépendance FastAPI : vérifie le JWT, retourne l'appelant (email/rôle/id).

    Voir docs/seq_auth_token.md : chaque appel après /auth/login doit porter
    un `Authorization: Bearer <JWT>` valide. role/uid viennent du token
    (ajoutés au login, voir create_access_token) pour éviter un aller-retour
    base à chaque requête.
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentification requise")
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")
    return CurrentUser(email=payload["sub"], role=payload.get("role"), user_id=payload.get("uid"))


def require_admin(current_user: CurrentUser = Depends(require_auth)) -> CurrentUser:
    """Dépendance FastAPI : comme require_auth, mais exige le rôle admin."""
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


def _assert_site_access(current_user: CurrentUser, site_id: str) -> None:
    permitted = _permitted_site_ids(current_user)
    if permitted is not None and site_id not in permitted:
        raise HTTPException(status_code=403, detail=f"Accès non autorisé au site {site_id}")


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminUserResponse(BaseModel):
    id: str
    email: str
    role: str | None
    site_ids: list[str]


class CreateUserRequest(BaseModel):
    email: str
    password: str
    role: str | None = None
    site_ids: list[str] = []


class UpdateUserRequest(BaseModel):
    role: str | None = None
    site_ids: list[str] | None = None


@app.get("/", tags=["Root"], summary="Root")
def root() -> dict:
    """Point d'entrée : liste les endpoints disponibles."""
    return {
        "endpoints": [
            "/docs",
            "/health",
            "/auth/login",
            "/admin/users",
            "/api/v1/sites",
            "/api/v1/sites/{site_id}/current",
            "/api/v1/readings",
            "/api/v1/alerts",
            "/api/v1/sensors/status",
            "/api/v1/predictions/range",
            "/api/v1/recommendations",
        ]
    }


@app.get("/health", tags=["Health"], summary="Vérifie que l'API répond")
def health() -> dict:
    return {"status": "ok"}


@app.post("/auth/login", tags=["Auth"], summary="Authentification, retourne un JWT")
def login(credentials: LoginRequest) -> TokenResponse:
    """Vérifie email/mot de passe, retourne un JWT (voir docs/seq_auth_token.md).

    Limite les tentatives (voir infrastructure/login_throttle.py, recommandé
    par l'ANSSI en complément/alternative à un mot de passe très long).
    """
    if is_locked_out(credentials.email):
        raise HTTPException(
            status_code=429,
            detail="Trop de tentatives échouées. Réessayez dans quelques minutes.",
        )

    user = user_repository.get_by_email(credentials.email)
    if user is None or not verify_password(credentials.password, user.password_hash):
        record_failed_attempt(credentials.email)
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    reset_attempts(credentials.email)
    token = create_access_token(user.email, role=user.role, uid=user.id)
    return TokenResponse(access_token=token)


@app.get("/api/v1/sites", tags=["Sites"], summary="Lister tous les sites")
def list_sites(current_user: CurrentUser = Depends(require_auth)) -> list:
    """Relaie la liste des sites depuis l'API mock, filtrée selon les sites
    autorisés pour l'utilisateur connecté (voir _permitted_site_ids)."""
    permitted = _permitted_site_ids(current_user)
    sites = sensor_api.get_sites()
    if permitted is not None:
        sites = [site for site in sites if site.site_id in permitted]
    return [asdict(site) for site in sites]


@app.get(
    "/api/v1/sites/{site_id}/current",
    tags=["Readings"],
    summary="Lecture temps réel d'un site",
)
def get_current_reading(
    site_id: str, current_user: CurrentUser = Depends(require_auth)
) -> dict:
    """Relaie la mesure instantanée d'un site depuis l'API mock."""
    _assert_site_access(current_user, site_id)
    reading = sensor_api.get_current_reading(site_id)
    if reading is None:
        raise HTTPException(status_code=404, detail=f"Aucune lecture disponible pour {site_id}")
    return asdict(reading)


@app.get(
    "/api/v1/readings",
    tags=["Readings"],
    summary="Historique des lectures",
)
def list_readings(
    site_id: str | None = Query(
        None, description="Filtrer par site (ex: SITE001). Si absent, retourne tous les sites."
    ),
    start_time: str | None = Query(
        None, description="Début de la période (ISO 8601). Défaut : 24h avant end_time."
    ),
    end_time: str | None = Query(
        None, description="Fin de la période (ISO 8601). Défaut : maintenant."
    ),
    limit: int = Query(
        100, ge=1, le=1000, description="Nombre maximum de résultats retournés (1-1000)."
    ),
    current_user: CurrentUser = Depends(require_auth),
) -> list:
    """Relaie l'historique des lectures depuis l'API mock (mêmes paramètres que la source)."""
    permitted = _permitted_site_ids(current_user)
    if site_id is not None:
        _assert_site_access(current_user, site_id)
    readings = sensor_api.get_readings(
        site_id=site_id, start_time=start_time, end_time=end_time, limit=limit
    )
    if permitted is not None:
        readings = [r for r in readings if r.site_id in permitted]
    return [asdict(r) for r in readings]


@app.get(
    "/api/v1/alerts",
    tags=["Alerts"],
    summary="Alertes actives",
)
def list_alerts(
    site_id: str | None = Query(None, description="Filtrer par site"),
    severity: str | None = Query(
        None, description="Filtrer par sévérité : low | medium | high | critical"
    ),
    current_user: CurrentUser = Depends(require_auth),
) -> list:
    """Relaie les alertes de consommation actives depuis l'API mock."""
    permitted = _permitted_site_ids(current_user)
    if site_id is not None:
        _assert_site_access(current_user, site_id)
    alerts = sensor_api.get_alerts(site_id=site_id, severity=severity)
    if permitted is not None:
        alerts = [a for a in alerts if a.site_id in permitted]
    return [asdict(a) for a in alerts]


@app.get(
    "/api/v1/sensors/status",
    tags=["Sensors"],
    summary="État des capteurs par site",
)
def sensors_status(current_user: CurrentUser = Depends(require_auth)) -> dict:
    """Relaie l'état de santé des capteurs par site depuis l'API mock."""
    permitted = _permitted_site_ids(current_user)
    status = sensor_api.get_sensors_status()
    if permitted is not None:
        status = {site_id: v for site_id, v in status.items() if site_id in permitted}
    return status


@app.get(
    "/api/v1/predictions/range",
    tags=["Predictions"],
    summary="Prévision de consommation sur une plage",
)
def list_predictions_range(
    site_id: str = Query(..., min_length=1, description="Site à prédire, ex: SITE001"),
    start_time: str = Query(
        ...,
        description="Début de la période au format ISO 8601, ex: 2026-09-17T08:00:00Z",
    ),
    end_time: str = Query(
        ...,
        description="Fin de la période au format ISO 8601, ex: 2026-09-17T12:00:00Z",
    ),
    interval: str = Query(
        "minute",
        description="Pas de la série retournée : 'minute' (défaut) ou 'hour'",
    ),
    current_user: CurrentUser = Depends(require_auth),
) -> dict:
    """Relaie GET /predict/range du service prediction."""
    _assert_site_access(current_user, site_id)
    result = prediction_api.get_prediction_range(
        site_id=site_id, start_time=start_time, end_time=end_time, interval=interval
    )
    if result is None:
        raise HTTPException(status_code=502, detail="Service de prédiction indisponible")
    return result


@app.get(
    "/api/v1/recommendations",
    tags=["Recommendations"],
    summary="Recommandations d'un site",
)
def list_recommendations(
    site_id: str = Query(..., min_length=1, description="Site à recommander, ex: SITE001"),
    current_user: CurrentUser = Depends(require_auth),
) -> list:
    """Relaie GET /api/v1/recommendations du service recommendation."""
    _assert_site_access(current_user, site_id)
    result = recommendation_api.get_recommendations(site_id=site_id)
    if result is None:
        raise HTTPException(status_code=502, detail="Service de recommandation indisponible")
    return result


def _to_admin_response(user, site_ids: list[str] | None = None) -> AdminUserResponse:
    if site_ids is None:
        site_ids = [] if user.role == "admin" else site_access_repository.get_site_ids(user.id)
    return AdminUserResponse(id=user.id, email=user.email, role=user.role, site_ids=site_ids)


@app.get("/admin/users", tags=["Admin"], summary="Lister les utilisateurs")
def admin_list_users(
    _current_user: CurrentUser = Depends(require_admin),
) -> list[AdminUserResponse]:
    return [_to_admin_response(user) for user in user_repository.list_all()]


@app.post("/admin/users", tags=["Admin"], summary="Créer un utilisateur")
def admin_create_user(
    body: CreateUserRequest, _current_user: CurrentUser = Depends(require_admin)
) -> AdminUserResponse:
    try:
        validate_password_strength(body.password, email=body.email)
    except WeakPasswordError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        user = user_repository.create(body.email, hash_password(body.password), body.role)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    site_ids = body.site_ids if user.role != "admin" else []
    if site_ids:
        site_access_repository.set_site_ids(user.id, site_ids)
    return _to_admin_response(user, site_ids=site_ids)


@app.patch("/admin/users/{user_id}", tags=["Admin"], summary="Modifier le rôle/les sites d'un utilisateur")
def admin_update_user(
    user_id: str,
    body: UpdateUserRequest,
    current_user: CurrentUser = Depends(require_admin),
) -> AdminUserResponse:
    user = user_repository.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if body.role is not None:
        if user.email == current_user.email and body.role != "admin":
            raise HTTPException(
                status_code=400, detail="Vous ne pouvez pas retirer votre propre rôle admin"
            )
        user = user_repository.update_role(user_id, body.role)

    if body.site_ids is not None:
        site_access_repository.set_site_ids(user_id, body.site_ids)

    return _to_admin_response(user)


@app.delete("/admin/users/{user_id}", tags=["Admin"], summary="Supprimer un utilisateur")
def admin_delete_user(
    user_id: str, current_user: CurrentUser = Depends(require_admin)
) -> dict:
    target = user_repository.get_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if target.email == current_user.email:
        raise HTTPException(
            status_code=400, detail="Vous ne pouvez pas supprimer votre propre compte"
        )
    user_repository.delete(user_id)
    return {"status": "deleted"}
