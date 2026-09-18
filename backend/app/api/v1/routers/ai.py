"""Team-scoped Q&A over own incident history (Phase 6).

POST /ai/ask {question} — keyword search over the caller's team incidents
(never other teams'), then 1 Gemini call grounded on the top matches.
Rate-limited 10/min/user like all generating endpoints. No cache in v1
(questions are free-form; answers stay cheap at ~1 call each).
"""

import re

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DBDep, MemberUser, RedisDep
from app.core.rate_limit import check_rate_limit
from app.models.monitor import Monitor
from app.repositories import incident_repository
from app.schemas.ai import AskIn, AskOut
from app.schemas.common import ApiResponse
from app.services import ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


def _keywords(question: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", question.lower())
    return [w for w in words if len(w) >= 4]


def _score(text: str, keywords: list[str]) -> int:
    text = text.lower()
    return sum(1 for kw in keywords if kw in text)


@router.post("/ask", response_model=ApiResponse[AskOut])
async def ask_about_incidents(user: MemberUser, body: AskIn, db: DBDep, redis: RedisDep):
    await check_rate_limit(redis, key=f"rl:ai:{user.id}", limit=10, window_sec=60)

    incidents = await incident_repository.list_for_team(db, user.team_id)
    if not incidents:
        return ApiResponse(data=AskOut(answer="No incidents recorded for your team yet."))

    result = await db.execute(select(Monitor).where(Monitor.team_id == user.team_id))
    names = {m.id: m.name for m in result.scalars().all()}

    keywords = _keywords(body.question)
    scored = []
    for inc in incidents:
        haystack = f"{names.get(inc.monitor_id, '')} {inc.status} {inc.ai_summary or ''}"
        scored.append((_score(haystack, keywords), inc))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    top = [
        {
            "monitor_name": names.get(inc.monitor_id, "Monitor"),
            "status": inc.status,
            "started_at": inc.started_at.isoformat() if inc.started_at else "-",
            "ai_summary": inc.ai_summary,
            "error": None,
        }
        for _, inc in scored[:5]
    ]
    text, error, _usage = await ai_service.call_gemini(
        ai_service.build_ask_prompt(body.question, top)
    )
    if text:
        return ApiResponse(data=AskOut(answer=text))
    if error == "quota":
        error = "AI quota is busy right now (free tier) — retry in a minute"
    if error and "not configured" in error:
        from fastapi import status as http_status

        from app.core.exceptions import AppError

        raise AppError(http_status.HTTP_503_SERVICE_UNAVAILABLE, "AI_NOT_CONFIGURED", error)
    from fastapi import status as http_status

    from app.core.exceptions import AppError

    raise AppError(
        http_status.HTTP_502_BAD_GATEWAY, "AI_FAILED", error or "AI failed — retry shortly"
    )
