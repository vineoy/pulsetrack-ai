"""Outbound incident webhooks (Phase 7): CRUD + instant Test delivery.

POST   /webhooks/outbound            Member+  {url, secret?} (secret auto-made)
GET    /webhooks/outbound            Bearer   list (secrets never returned)
POST   /webhooks/outbound/{id}/test  Member+  sample payload, live result
DELETE /webhooks/outbound/{id}       Member+  remove

Real OPEN/RECOVERY deliveries run as ARQ `webhook_delivery_job` (see workers),
enqueued next to the Telegram alert in checker.py.
"""

import secrets
import uuid

from fastapi import APIRouter, Request, status
from pydantic import HttpUrl, TypeAdapter

from app.api.deps import DBDep, MemberUser, client_ip
from app.core.exceptions import AppError
from app.repositories import audit_repository, webhook_repository
from app.schemas.common import ApiResponse
from app.schemas.webhook import WebhookCreatedOut, WebhookIn, WebhookOut, WebhookTestOut
from app.services import webhook_service

router = APIRouter(prefix="/webhooks/outbound", tags=["webhooks"])

_url_check = TypeAdapter(HttpUrl)


def _validate_url(url: str) -> str:
    url = url.strip()
    try:
        parsed = _url_check.validate_python(url)
    except Exception:
        raise AppError(422, "VALIDATION_ERROR", "url must be a valid http(s) URL") from None
    if str(parsed.scheme) not in ("http", "https"):
        raise AppError(422, "VALIDATION_ERROR", "url must be a valid http(s) URL")
    return str(parsed)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[WebhookCreatedOut])
async def create_webhook(user: MemberUser, body: WebhookIn, request: Request, db: DBDep):
    url = _validate_url(body.url)
    secret = (body.secret or "").strip() or f"whsec_{secrets.token_urlsafe(24)}"
    hook = await webhook_repository.create(
        db, team_id=user.team_id, url=url, secret=secret, is_active=True
    )
    await audit_repository.log(
        db,
        action="webhook.created",
        team_id=user.team_id,
        user_id=user.id,
        target_type="outbound_webhook",
        target_id=str(hook.id),
        detail={"url": url},
        ip=client_ip(request),
    )
    await db.commit()
    return ApiResponse(
        data=WebhookCreatedOut(
            id=hook.id,
            team_id=hook.team_id,
            url=hook.url,
            is_active=hook.is_active,
            created_at=hook.created_at,
            secret=secret if not (body.secret or "").strip() else "••••••••",
        )
    )


@router.get("", response_model=ApiResponse[list[WebhookOut]])
async def list_webhooks(user: MemberUser, db: DBDep):
    rows = await webhook_repository.list_for_team(db, user.team_id)
    return ApiResponse(data=[WebhookOut.model_validate(r) for r in rows])


@router.post("/{webhook_id}/test", response_model=ApiResponse[WebhookTestOut])
async def test_webhook(user: MemberUser, webhook_id: uuid.UUID, db: DBDep):
    hook = await webhook_repository.get_by_id(db, webhook_id)
    if hook is None or hook.team_id != user.team_id:
        raise AppError(404, "NOT_FOUND", "Webhook not found")
    payload = webhook_service.build_event(
        "incident.opened",
        team_slug="test",
        monitor_name="Test monitor",
        monitor_url="https://example.com",
        incident={"id": "test", "status": "OPEN", "test": True},
    )
    ok, error, status_code = await webhook_service.deliver(hook.url, hook.secret, payload)
    await audit_repository.log(
        db,
        action="webhook.tested",
        team_id=user.team_id,
        user_id=user.id,
        target_type="outbound_webhook",
        target_id=str(hook.id),
        detail={"ok": ok, "status_code": status_code, "error": error},
    )
    await db.commit()
    return ApiResponse(data=WebhookTestOut(ok=ok, status_code=status_code, error=error))


@router.delete("/{webhook_id}", response_model=ApiResponse[dict])
async def delete_webhook(user: MemberUser, webhook_id: uuid.UUID, request: Request, db: DBDep):
    hook = await webhook_repository.get_by_id(db, webhook_id)
    if hook is None or hook.team_id != user.team_id:
        raise AppError(404, "NOT_FOUND", "Webhook not found")
    await audit_repository.log(
        db,
        action="webhook.deleted",
        team_id=user.team_id,
        user_id=user.id,
        target_type="outbound_webhook",
        target_id=str(hook.id),
        detail={"url": hook.url},
        ip=client_ip(request),
    )
    await webhook_repository.delete(db, hook)
    await db.commit()
    return ApiResponse(data={"deleted": True})
