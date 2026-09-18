"""Authenticated WebSocket for live monitor updates (Phase 5).

Connect: WS /ws/monitors?token=<JWT access token>
Auth: browsers can't set Authorization headers on WS, so the access token
rides in the query string. Validated once at connect (type=access,
not blacklisted, user active). Closed with 4401/4403 on failure.

Fan-out: subscribes to Redis pub/sub "live", forwards only messages whose
team_id matches the connected user. Heartbeat: server sends
{"type":"hello"} on connect; client should reconnect with backoff on drop
(Dashboard keeps 30s polling as fallback).
"""

from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.db import async_session_factory
from app.core.redis import redis_client
from app.core.security import decode_token
from app.repositories import user_repository
from app.services.live_service import LIVE_CHANNEL

router = APIRouter()


async def _auth_ws(token: str | None):
    if not token:
        return None, "missing token"
    try:
        payload = decode_token(token)
    except Exception:
        return None, "invalid token"
    if payload.type != "access":
        return None, "wrong token type"
    try:
        if await redis_client.exists(f"jwt:black:{payload.jti}"):
            return None, "revoked"
    except Exception:  # noqa: BLE001
        return None, "redis unavailable"
    try:
        user_id = uuid.UUID(payload.sub)
    except ValueError:
        return None, "malformed sub"
    async with async_session_factory() as db:
        user = await user_repository.get_by_id(db, user_id)
    if user is None or not user.is_active:
        return None, "user gone"
    return user, None


@router.websocket("/ws/monitors")
async def ws_monitors(websocket: WebSocket):
    token = websocket.query_params.get("token")
    user, error = await _auth_ws(token)
    if user is None:
        await websocket.close(code=4401)
        return
    team_id = str(user.team_id)
    await websocket.accept()
    await websocket.send_json({"type": "hello", "team_id": team_id})

    pubsub = redis_client.pubsub()
    await pubsub.subscribe(LIVE_CHANNEL)
    try:
        while True:
            # Redis side (non-blocking poll) + client side (detect close).
            try:
                raw = await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda: pubsub.get_message(
                            ignore_subscribe_messages=True, timeout=1.0
                        )
                    ),
                    timeout=1.2,
                )
            except TimeoutError:
                raw = None
            if raw and raw.get("data"):
                try:
                    data = raw["data"]
                    msg = json.loads(data) if isinstance(data, str) else {}
                except (json.JSONDecodeError, TypeError):
                    msg = {}
                if isinstance(msg, dict) and str(msg.get("team_id")) == team_id:
                    try:
                        await websocket.send_json(msg)
                    except Exception:  # noqa: BLE001
                        break
            # Detect client disconnect without blocking the loop.
            try:
                incoming = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
                # Clients may send "ping" — answer so proxies keep us alive.
                if incoming == "ping":
                    try:
                        await websocket.send_text("pong")
                    except Exception:  # noqa: BLE001
                        break
            except TimeoutError:
                pass
            except (WebSocketDisconnect, RuntimeError):
                break
            except Exception:  # noqa: BLE001
                break
    finally:
        try:
            await pubsub.unsubscribe(LIVE_CHANNEL)
            await pubsub.aclose()
        except Exception:  # noqa: BLE001
            pass
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass
