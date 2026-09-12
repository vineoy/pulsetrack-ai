from fastapi import APIRouter, Request, status

from app.api.deps import CurrentUser, DBDep, RedisDep, TokenPayloadDep, client_ip
from app.schemas.auth import (
    AuthOut,
    LoginIn,
    LogoutIn,
    MeOut,
    RefreshIn,
    RegisterIn,
    TeamOut,
    TokenPairOut,
    UserOut,
)
from app.schemas.common import ApiResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[AuthOut])
async def register(body: RegisterIn, request: Request, db: DBDep, redis: RedisDep):
    user, tokens = await auth_service.register(db, redis, body, client_ip(request))
    return ApiResponse(data=AuthOut(**tokens.model_dump(), user=UserOut.model_validate(user)))


@router.post("/login", response_model=ApiResponse[AuthOut])
async def login(body: LoginIn, request: Request, db: DBDep, redis: RedisDep):
    user, tokens = await auth_service.login(
        db, redis, body.email, body.password, client_ip(request)
    )
    return ApiResponse(data=AuthOut(**tokens.model_dump(), user=UserOut.model_validate(user)))


@router.post("/refresh", response_model=ApiResponse[TokenPairOut])
async def refresh(body: RefreshIn, request: Request, db: DBDep, redis: RedisDep):
    tokens = await auth_service.refresh(db, redis, body.refresh_token, client_ip(request))
    return ApiResponse(data=tokens)


@router.post("/logout", response_model=ApiResponse[dict])
async def logout(
    user: CurrentUser,
    payload: TokenPayloadDep,
    request: Request,
    db: DBDep,
    redis: RedisDep,
    body: LogoutIn | None = None,
):
    refresh_token = body.refresh_token if body else None
    await auth_service.logout(db, redis, user, payload, refresh_token, client_ip(request))
    return ApiResponse(data={"revoked": True})


@router.get("/me", response_model=ApiResponse[MeOut])
async def me(user: CurrentUser):
    return ApiResponse(
        data=MeOut(user=UserOut.model_validate(user), team=TeamOut.model_validate(user.team))
    )
