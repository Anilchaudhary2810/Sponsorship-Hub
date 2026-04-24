from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import exceptions, models, schemas
from ..auth import get_current_user
from ..config import settings
from ..core.limiter import limiter
from ..core.pagination import clamp_limit
from ..database import get_db
from ..logger import logger

router = APIRouter(prefix="/ai-assistant", tags=["AI Assistant"])

ACTIVE_DEAL_STATES = ["proposed", "payment_pending", "signing_pending"]
BLOCKED_TOPIC_KEYWORDS = {
    "movie",
    "songs",
    "recipe",
    "astrology",
    "horoscope",
    "lottery",
    "bet",
    "gambling",
    "crypto price",
    "stock tips",
    "cricket score",
    "football score",
    "politics",
    "election",
    "adult",
}
ALLOWED_TOPIC_KEYWORDS = {
    "sponsor",
    "sponsorship",
    "event",
    "deal",
    "campaign",
    "pipeline",
    "dashboard",
    "marketplace",
    "analytics",
    "invoice",
    "agreement",
    "review",
    "payment",
    "stats",
    "profile",
    "notification",
    "business",
    "platform",
    "brand",
    "influencer",
    "organizer",
    "proposal",
    "partnership",
    "page",
    "application",
    "app",
    "kyc",
    "trust",
    "workspace",
    "report",
    "plan",
    "revenue",
    "spend",
    "earning",
    "income",
    "create",
    "new",
    "steps",
    "guide",
    "help",
}

APP_CAPABILITIES = [
    "Event and campaign management for sponsors, organizers, and influencers",
    "Deal lifecycle workflow: proposal, acceptance, payment, signing, closure",
    "Discovery marketplaces and activity pipelines",
    "KYC, trust scoring, verification workflows",
    "Retention nudges, reporting, and integrations",
]

TOPIC_GUARDRAIL_MESSAGE = (
    "I can help only with Sponsorship Hub workflows, sponsorship/business questions, "
    "and general product usage. Ask me about dashboards, deals, events, analytics, "
    "payments, or your page actions."
)


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_str(value: Any, default: str = "") -> str:
    if isinstance(value, str):
        return value
    return default


def _as_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_path(path: str | None) -> str:
    raw = _as_str(path, default="/").strip()
    if not raw:
        return "/"
    if not raw.startswith("/"):
        return f"/{raw}"
    return raw


def _is_confidential_key(key: str) -> bool:
    low = key.lower()
    return any(token in low for token in ("password", "secret", "token", "email", "phone", "cookie", "csrf", "key"))


def _sanitize_page_data(value: Any, depth: int = 0) -> Any:
    if depth > 3:
        return None
    if isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        text = value.strip()
        return text[:280] if len(text) > 280 else text
    if isinstance(value, list):
        cleaned_items: list[Any] = []
        for item in value[:12]:
            cleaned = _sanitize_page_data(item, depth + 1)
            if cleaned is not None:
                cleaned_items.append(cleaned)
        return cleaned_items
    if isinstance(value, dict):
        cleaned_dict: dict[str, Any] = {}
        for idx, (key, item) in enumerate(value.items()):
            if idx >= 20:
                break
            key_str = _as_str(key, "")
            if not key_str or _is_confidential_key(key_str):
                continue
            cleaned = _sanitize_page_data(item, depth + 1)
            if cleaned is not None:
                cleaned_dict[key_str[:80]] = cleaned
        return cleaned_dict
    return None


def _normalize_query_text(message: str) -> str:
    text = _as_str(message, "").lower().strip()
    replacements = {
        "revinue": "revenue",
        "revnue": "revenue",
        "reveneu": "revenue",
        "sponsership": "sponsorship",
        "analitics": "analytics",
        "analtyics": "analytics",
        "stast": "stats",
    }
    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)
    return text


def _is_allowed_topic(message: str) -> bool:
    text = _normalize_query_text(message)
    if not text:
        return False

    if text in {"hi", "hello", "hey"}:
        return True

    if any(word in text for word in BLOCKED_TOPIC_KEYWORDS):
        return False

    if any(word in text for word in ALLOWED_TOPIC_KEYWORDS):
        return True

    # Short generic follow-ups can be accepted in an ongoing product conversation.
    if len(text.split()) <= 4:
        return True
    return False


def _page_profile(path: str) -> tuple[str, list[str]]:
    lower = path.lower()
    if "sponsor-dashboard" in lower:
        return (
            "Sponsor Dashboard",
            [
                "Review active sponsorship deals",
                "Track payment and signing stages",
                "Open event details from pipeline cards",
                "Explore Brand Opportunities and Discovery Marketplace",
            ],
        )
    if "organizer-dashboard" in lower:
        return (
            "Organizer Dashboard",
            [
                "Manage events and sponsor proposals",
                "Track deal closures and payouts",
                "Open pipeline activities and complete pending steps",
                "Publish events to the marketplace",
            ],
        )
    if "influencer-dashboard" in lower:
        return (
            "Influencer Dashboard",
            [
                "Monitor campaign/promotion deals",
                "Check agreement, invoice, and review steps",
                "Open pipeline activities and complete pending actions",
                "Explore sponsor discovery cards",
            ],
        )
    if "analytics" in lower:
        return (
            "Analytics",
            [
                "Understand KPI trends and conversion flow",
                "Compare closed deals and active pipeline",
                "Use insights for next campaign decisions",
            ],
        )
    if "activity-center" in lower:
        return (
            "Activity Center",
            [
                "Browse latest activities across modules",
                "Search specific pipeline activities",
                "Open the related event or deal details",
            ],
        )
    if "scale-ops" in lower:
        return (
            "Scale Ops",
            [
                "Review operational metrics and audits",
                "Track plan distribution and trust workflows",
                "Monitor platform health indicators",
            ],
        )
    if path == "/":
        return (
            "Landing Page",
            [
                "Explore Sponsorship Hub capabilities",
                "Understand platform value and workflows",
                "Navigate to login/register and role dashboards",
            ],
        )
    return (
        "Sponsorship Hub",
        [
            "Navigate module workflows",
            "Track deals, events, and campaigns",
            "Review platform insights and operational progress",
        ],
    )


def _deal_scope_filter(role: str, user_id: int):
    if role == "sponsor":
        return models.Deal.sponsor_id == user_id
    if role == "organizer":
        return models.Deal.organizer_id == user_id
    return models.Deal.influencer_id == user_id


def _build_global_stats(db: Session) -> dict[str, Any]:
    return {
        "total_users": db.query(models.User).count(),
        "total_events": db.query(models.Event).count(),
        "total_campaigns": db.query(models.Campaign).count(),
        "active_deals": db.query(models.Deal).filter(models.Deal.status.in_(ACTIVE_DEAL_STATES)).count(),
        "closed_deals": db.query(models.Deal).filter(models.Deal.status == "closed").count(),
    }


def _build_user_stats(db: Session, user: models.User) -> dict[str, Any]:
    user_id = _as_int(getattr(user, "id", 0))
    role = _as_str(getattr(user, "role", "")).lower()
    deal_filter = _deal_scope_filter(role, user_id)

    total_deals = db.query(models.Deal).filter(deal_filter).count()
    active_deals = db.query(models.Deal).filter(deal_filter, models.Deal.status.in_(ACTIVE_DEAL_STATES)).count()
    closed_deals = db.query(models.Deal).filter(deal_filter, models.Deal.status == "closed").count()
    total_value = _as_float(
        db.query(func.coalesce(func.sum(models.Deal.payment_amount), 0))
        .filter(deal_filter, models.Deal.payment_done == True)
        .scalar()
    )

    pending_signatures = 0
    if role == "sponsor":
        pending_signatures = db.query(models.Deal).filter(
            models.Deal.sponsor_id == user_id,
            models.Deal.payment_done == True,
            models.Deal.sponsor_signed == False,
            models.Deal.status.in_(ACTIVE_DEAL_STATES),
        ).count()
    elif role == "organizer":
        pending_signatures = db.query(models.Deal).filter(
            models.Deal.organizer_id == user_id,
            models.Deal.payment_done == True,
            models.Deal.organizer_signed == False,
            models.Deal.status.in_(ACTIVE_DEAL_STATES),
        ).count()
    elif role == "influencer":
        pending_signatures = db.query(models.Deal).filter(
            models.Deal.influencer_id == user_id,
            models.Deal.payment_done == True,
            models.Deal.influencer_signed == False,
            models.Deal.status.in_(ACTIVE_DEAL_STATES),
        ).count()

    stats = {
        "role": role or "user",
        "total_deals": total_deals,
        "active_deals": active_deals,
        "closed_deals": closed_deals,
        "pending_signatures": pending_signatures,
    }
    if role == "organizer":
        stats["events_created"] = db.query(models.Event).filter(models.Event.organizer_id == user_id).count()
        stats["total_revenue"] = total_value
    elif role == "sponsor":
        stats["campaigns_created"] = db.query(models.Campaign).filter(models.Campaign.creator_id == user_id).count()
        stats["total_spend"] = total_value
    elif role == "influencer":
        stats["campaigns_created"] = db.query(models.Campaign).filter(models.Campaign.creator_id == user_id).count()
        stats["total_revenue"] = total_value
    return stats


def _user_name_map(db: Session, user_ids: list[int]) -> dict[int, str]:
    if not user_ids:
        return {}
    rows = db.query(models.User).filter(models.User.id.in_(user_ids)).all()
    return {int(getattr(row, "id", 0)): _as_str(getattr(row, "full_name", ""), "User") for row in rows}


def _build_recent_items(db: Session, user: models.User) -> list[dict[str, Any]]:
    user_id = _as_int(getattr(user, "id", 0))
    role = _as_str(getattr(user, "role", "")).lower()
    deal_filter = _deal_scope_filter(role, user_id)

    deals = (
        db.query(models.Deal)
        .filter(deal_filter)
        .order_by(models.Deal.updated_at.desc())
        .limit(6)
        .all()
    )
    counterparty_ids: list[int] = []
    for deal in deals:
        sponsor_id = _as_int(getattr(deal, "sponsor_id", 0))
        organizer_id = _as_int(getattr(deal, "organizer_id", 0))
        influencer_id = _as_int(getattr(deal, "influencer_id", 0))
        if role == "sponsor":
            if organizer_id:
                counterparty_ids.append(organizer_id)
            if influencer_id:
                counterparty_ids.append(influencer_id)
        elif role == "organizer":
            if sponsor_id:
                counterparty_ids.append(sponsor_id)
            if influencer_id:
                counterparty_ids.append(influencer_id)
        else:
            if sponsor_id:
                counterparty_ids.append(sponsor_id)
            if organizer_id:
                counterparty_ids.append(organizer_id)

    names = _user_name_map(db, list(set(counterparty_ids)))
    items: list[dict[str, Any]] = []
    for deal in deals:
        sponsor_id = _as_int(getattr(deal, "sponsor_id", 0))
        organizer_id = _as_int(getattr(deal, "organizer_id", 0))
        influencer_id = _as_int(getattr(deal, "influencer_id", 0))

        counterparty_name = "Counterparty"
        if role == "sponsor":
            counterparty_name = names.get(organizer_id) or names.get(influencer_id) or counterparty_name
        elif role == "organizer":
            counterparty_name = names.get(sponsor_id) or names.get(influencer_id) or counterparty_name
        elif role == "influencer":
            counterparty_name = names.get(sponsor_id) or names.get(organizer_id) or counterparty_name

        items.append(
            {
                "type": "deal",
                "deal_id": _as_int(getattr(deal, "id", 0)),
                "deal_type": _as_str(getattr(deal, "deal_type", "")),
                "status": _as_str(getattr(deal, "status", "")),
                "payment_status": _as_str(getattr(deal, "payment_status", "")),
                "amount": _as_float(getattr(deal, "payment_amount", 0)),
                "counterparty": counterparty_name,
            }
        )

    if role == "organizer":
        events = (
            db.query(models.Event)
            .filter(models.Event.organizer_id == user_id)
            .order_by(models.Event.updated_at.desc())
            .limit(3)
            .all()
        )
        for event in events:
            items.append(
                {
                    "type": "event",
                    "event_id": _as_int(getattr(event, "id", 0)),
                    "title": _as_str(getattr(event, "title", "")),
                    "city": _as_str(getattr(event, "city", "")),
                    "state": _as_str(getattr(event, "state", "")),
                }
            )
    return items[:8]


def _build_private_context(
    db: Session,
    user: models.User,
    path: str,
    page_title: str | None,
    page_data: dict[str, Any],
) -> schemas.AIContextResponse:
    normalized_path = _normalize_path(path)
    default_title, capabilities = _page_profile(normalized_path)
    title = _as_str(page_title, "").strip() or default_title
    cleaned_page_data = _sanitize_page_data(page_data) if isinstance(page_data, dict) else {}
    if not isinstance(cleaned_page_data, dict):
        cleaned_page_data = {}

    return schemas.AIContextResponse(
        path=normalized_path,
        title=title,
        role=_as_str(getattr(user, "role", ""), "user"),
        capabilities=capabilities,
        user_stats=_build_user_stats(db, user),
        global_stats=_build_global_stats(db),
        recent_items=_build_recent_items(db, user),
        page_data=cleaned_page_data,
        confidentiality_note="Responses must avoid confidential data (passwords, tokens, private PII).",
    )


def _build_public_context(
    db: Session,
    path: str,
    page_title: str | None,
    page_data: dict[str, Any],
) -> schemas.AIContextResponse:
    normalized_path = _normalize_path(path)
    default_title, capabilities = _page_profile(normalized_path)
    title = _as_str(page_title, "").strip() or default_title
    cleaned_page_data = _sanitize_page_data(page_data) if isinstance(page_data, dict) else {}
    if not isinstance(cleaned_page_data, dict):
        cleaned_page_data = {}

    public_events = (
        db.query(models.Event)
        .order_by(models.Event.created_at.desc())
        .limit(4)
        .all()
    )
    recent_items = [
        {
            "type": "event",
            "event_id": _as_int(getattr(event, "id", 0)),
            "title": _as_str(getattr(event, "title", "")),
            "city": _as_str(getattr(event, "city", "")),
            "state": _as_str(getattr(event, "state", "")),
        }
        for event in public_events
    ]

    return schemas.AIContextResponse(
        path=normalized_path,
        title=title,
        role="guest",
        capabilities=capabilities,
        user_stats={},
        global_stats=_build_global_stats(db),
        recent_items=recent_items,
        page_data=cleaned_page_data,
        confidentiality_note="Public mode does not include private user account data.",
    )


def _system_prompt() -> str:
    return (
        "You are HubBot for Sponsorship Hub.\n"
        "Rules:\n"
        "1) Answer only product/business/sponsorship-related questions.\n"
        "2) If asked unrelated topics, decline and redirect to Sponsorship Hub help.\n"
        "3) Use provided context and page data to give actionable, concrete guidance.\n"
        "4) Never reveal confidential data, credentials, or private PII.\n"
        "5) If user asks what they can do on this page, list page actions from context capabilities.\n"
        f"Platform capabilities: {', '.join(APP_CAPABILITIES)}"
    )


def _format_inr(value: Any) -> str:
    amount = _as_float(value, 0.0)
    return f"₹{amount:,.2f}"


def _create_deal_steps(role: str) -> list[str]:
    if role == "sponsor":
        return [
            "Open Discovery Marketplace or Event Marketplace from your sponsor dashboard.",
            "Open an event/campaign card you want to partner with.",
            "Click `Propose Partnership` (or create deal action) and enter amount, terms, and notes.",
            "Submit the proposal and track progress in My Brand Pipeline / Activity Center.",
        ]
    if role == "organizer":
        return [
            "Create/publish your event from Organizer Dashboard.",
            "Open sponsor discovery and select the sponsor you want to approach.",
            "Click proposal action, add deal amount + deliverables + timeline, and send.",
            "Track acceptance/payment/signing in Active Deal Pipeline.",
        ]
    if role == "influencer":
        return [
            "Open Brand Opportunities / sponsor cards on your dashboard.",
            "Pick an opportunity and start a proposal/deal request.",
            "Share your deliverables, timeline, and expected amount.",
            "Track the deal through payment and agreement steps in your pipeline.",
        ]
    return [
        "Open your dashboard marketplace section.",
        "Choose a relevant opportunity.",
        "Create/send proposal with amount and terms.",
        "Track it in pipeline.",
    ]


def _rule_based_reply(
    message: str,
    context: schemas.AIContextResponse,
    status_hint: str | None = None,
) -> str:
    text = _normalize_query_text(message)
    role = _as_str(context.role, "user").lower()
    role_title = role.capitalize() if role else "User"
    capabilities = context.capabilities[:4]
    user_stats = context.user_stats or {}
    active_deals = _as_int(user_stats.get("active_deals"), 0)
    closed_deals = _as_int(user_stats.get("closed_deals"), 0)
    pending_signatures = _as_int(user_stats.get("pending_signatures"), 0)
    total_spend = _format_inr(user_stats.get("total_spend", 0))
    total_revenue = _format_inr(user_stats.get("total_revenue", 0))

    lines: list[str] = []
    if status_hint:
        lines.append(status_hint)
        lines.append("")

    ask_page_actions = ("what can i do" in text and "page" in text) or ("help on this page" in text)
    ask_revenue = any(word in text for word in {"revenue", "spend", "earning", "income", "money"})
    ask_create_deal = ("create" in text and "deal" in text) or ("new deal" in text) or ("propose" in text and "deal" in text)
    ask_stats = any(word in text for word in {"stats", "status", "summary", "pipeline"})

    if ask_page_actions:
        lines.append(f"On this page ({context.title}), you can:")
        for item in capabilities:
            lines.append(f"- {item}")
        lines.append("")
        lines.append("Want me to guide you step-by-step for one action?")
        return "\n".join(lines)

    if ask_revenue:
        lines.append(f"{role_title} financial snapshot:")
        if role == "sponsor":
            lines.append(f"- Total spend: {total_spend}")
            lines.append("- Sponsors track spend/investment (not revenue) on this role view.")
        else:
            lines.append(f"- Total revenue: {total_revenue}")
        lines.append(f"- Active deals: {active_deals}")
        lines.append(f"- Closed deals: {closed_deals}")
        lines.append(f"- Pending signatures: {pending_signatures}")
        return "\n".join(lines)

    if ask_create_deal:
        lines.append(f"How to create a new deal ({role_title} flow):")
        for idx, step in enumerate(_create_deal_steps(role), start=1):
            lines.append(f"{idx}. {step}")
        return "\n".join(lines)

    if ask_stats:
        lines.append(f"{role_title} pipeline snapshot:")
        lines.append(f"- Active deals: {active_deals}")
        lines.append(f"- Closed deals: {closed_deals}")
        lines.append(f"- Pending signatures: {pending_signatures}")
        if role == "sponsor":
            lines.append(f"- Total spend: {total_spend}")
        else:
            lines.append(f"- Total revenue: {total_revenue}")
        return "\n".join(lines)

    top_capability_text = "\n".join([f"- {item}" for item in capabilities]) if capabilities else "- Manage deals, events, and analytics."
    lines.append(f"I can help with your {role_title} workflow on {context.title}.")
    lines.append("Suggested actions:")
    lines.append(top_capability_text)
    lines.append("Ask me for: `create new deal`, `my revenue/spend`, `pipeline summary`, or `what can I do on this page`.")
    return "\n".join(lines)


def _fallback_reply(message: str, context: schemas.AIContextResponse) -> str:
    return _rule_based_reply(message=message, context=context, status_hint=None)


def _llm_failure_hint(status_code: int | None) -> str:
    if status_code in {401, 403}:
        return "Live AI is temporarily unavailable due to API authentication/configuration issue."
    if status_code in {400, 404}:
        return "Live AI request was rejected by provider. Check `AI_MODEL` and API endpoint compatibility."
    if status_code == 429:
        return "Live AI is temporarily rate-limited. You can try again in a few seconds."
    if status_code is not None and status_code >= 500:
        return "Live AI provider is temporarily unavailable."
    return "Live AI is temporarily unavailable, but I can still help from your app context."


def _extract_status_code(exc: Exception) -> int | None:
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            return int(exc.response.status_code)
        except Exception:
            return None
    return None


def _extract_llm_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            collected: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        collected.append(text.strip())
            if collected:
                return "\n".join([text for text in collected if text])
    return ""


def _extract_responses_content(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    output = payload.get("output")
    if not isinstance(output, list):
        return ""

    collected: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                collected.append(text.strip())
    return "\n".join(collected).strip()


async def _generate_ai_reply(
    message: str,
    context: schemas.AIContextResponse,
    history: list[models.AIChatMessage],
) -> str:
    api_key = _as_str(getattr(settings, "AI_API_KEY", ""), "").strip()
    model = _as_str(getattr(settings, "AI_MODEL", ""), "gpt-4o-mini").strip()
    base_url = _as_str(getattr(settings, "AI_API_BASE_URL", ""), "https://api.openai.com/v1").strip().rstrip("/")
    timeout_seconds = max(_as_int(getattr(settings, "AI_TIMEOUT_SECONDS", 25), 25), 8)

    if not api_key:
        return _rule_based_reply(
            message=message,
            context=context,
            status_hint="Live AI is not configured yet (`AI_API_KEY` missing).",
        )

    messages: list[dict[str, str]] = [{"role": "system", "content": _system_prompt()}]
    messages.append(
        {
            "role": "system",
            "content": "Context:\n" + json.dumps(context.model_dump(), default=str),
        }
    )

    for row in history[-10:]:
        row_role = _as_str(getattr(row, "role", "user"), "user")
        if row_role not in {"user", "assistant"}:
            continue
        row_content = _as_str(getattr(row, "content", ""), "")
        if not row_content:
            continue
        messages.append({"role": row_role, "content": row_content[:1200]})

    messages.append({"role": "user", "content": message[:1200]})

    chat_url = f"{base_url}/chat/completions"
    responses_url = f"{base_url}/responses"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    chat_payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 480,
    }
    responses_input = [
        {
            "role": row["role"],
            "content": [{"type": "input_text", "text": row["content"]}],
        }
        for row in messages
    ]
    responses_payload = {
        "model": model,
        "input": responses_input,
        "temperature": 0.2,
        "max_output_tokens": 480,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            try:
                response = await client.post(chat_url, headers=headers, json=chat_payload)
                response.raise_for_status()
                content = _extract_llm_content(response.json())
                if content:
                    return content
            except Exception as chat_exc:
                chat_status_code = _extract_status_code(chat_exc)
                should_try_responses = chat_status_code in {400, 404}
                if should_try_responses:
                    try:
                        response = await client.post(responses_url, headers=headers, json=responses_payload)
                        response.raise_for_status()
                        content = _extract_responses_content(response.json())
                        if content:
                            return content
                    except Exception as responses_exc:
                        status_code = _extract_status_code(responses_exc)
                        logger.warning(
                            f"AI assistant responses API failed (status={status_code}), using contextual fallback: {responses_exc}"
                        )
                        return _rule_based_reply(
                            message=message,
                            context=context,
                            status_hint=_llm_failure_hint(status_code),
                        )
                status_code = _extract_status_code(chat_exc)
                logger.warning(f"AI assistant API failed (status={status_code}), using contextual fallback: {chat_exc}")
                return _rule_based_reply(
                    message=message,
                    context=context,
                    status_hint=_llm_failure_hint(status_code),
                )
    except Exception as exc:
        status_code = _extract_status_code(exc)
        logger.warning(f"AI assistant API failed (status={status_code}), using contextual fallback: {exc}")
        return _rule_based_reply(
            message=message,
            context=context,
            status_hint=_llm_failure_hint(status_code),
        )

    return _fallback_reply(message, context)


def _serialize_history_rows(rows: list[models.AIChatMessage]) -> list[schemas.AIChatHistoryItem]:
    result: list[schemas.AIChatHistoryItem] = []
    for row in rows:
        role = _as_str(getattr(row, "role", ""), "")
        if role not in {"user", "assistant"}:
            continue
        result.append(
            schemas.AIChatHistoryItem(
                id=_as_int(getattr(row, "id", 0)),
                role=role,
                content=_as_str(getattr(row, "content", ""), ""),
                route_path=getattr(row, "route_path", None),
                page_title=getattr(row, "page_title", None),
                created_at=getattr(row, "created_at", datetime.utcnow()),
            )
        )
    return result


def _history_query(db: Session, user_id: int, limit: int) -> list[models.AIChatMessage]:
    rows = (
        db.query(models.AIChatMessage)
        .filter(models.AIChatMessage.user_id == user_id)
        .order_by(models.AIChatMessage.id.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()
    return rows


@router.get("/context", response_model=schemas.AIContextResponse)
@limiter.limit("90/minute")
def get_ai_context(
    request: Request,
    path: str = "/",
    page_title: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    return _build_private_context(db, current_user, path, page_title, page_data={})


@router.get("/public-context", response_model=schemas.AIContextResponse)
@limiter.limit("120/minute")
def get_public_ai_context(
    request: Request,
    path: str = "/",
    page_title: str | None = None,
    db: Session = Depends(get_db),
):
    del request
    return _build_public_context(db, path, page_title, page_data={})


@router.get("/history", response_model=list[schemas.AIChatHistoryItem])
@limiter.limit("120/minute")
def get_ai_history(
    request: Request,
    limit: int = 80,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    safe_limit = clamp_limit(limit, default=80, maximum=200)
    user_id = _as_int(getattr(current_user, "id", 0))
    rows = _history_query(db, user_id, safe_limit)
    return _serialize_history_rows(rows)


@router.delete("/history")
@limiter.limit("20/minute")
def clear_ai_history(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    user_id = _as_int(getattr(current_user, "id", 0))
    deleted = (
        db.query(models.AIChatMessage)
        .filter(models.AIChatMessage.user_id == user_id)
        .delete(synchronize_session=False)
    )
    db.commit()
    return {"cleared": deleted}


@router.post("/message", response_model=schemas.AIMessageResponse)
@limiter.limit("50/minute")
async def send_ai_message(
    request: Request,
    payload: schemas.AIMessageRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    user_id = _as_int(getattr(current_user, "id", 0))
    message = _as_str(payload.message, "").strip()
    if not message:
        raise exceptions.ValidationError("Message cannot be empty")
    if len(message) > 1800:
        raise exceptions.ValidationError("Message is too long")

    page_data = payload.page_data if isinstance(payload.page_data, dict) else {}
    context = _build_private_context(db, current_user, payload.path, payload.page_title, page_data=page_data)
    safe_history_limit = clamp_limit(payload.history_limit, default=12, maximum=30)
    existing_history = _history_query(db, user_id, safe_history_limit)

    if not _is_allowed_topic(message):
        reply = TOPIC_GUARDRAIL_MESSAGE
    else:
        reply = await _generate_ai_reply(message=message, context=context, history=existing_history)

    compact_context = {
        "path": context.path,
        "title": context.title,
        "role": context.role,
        "user_stats": context.user_stats,
    }
    db.add(
        models.AIChatMessage(
            user_id=user_id,
            role="user",
            content=message,
            route_path=context.path,
            page_title=context.title,
            context_json=compact_context,
        )
    )
    db.add(
        models.AIChatMessage(
            user_id=user_id,
            role="assistant",
            content=reply,
            route_path=context.path,
            page_title=context.title,
            context_json=compact_context,
        )
    )
    db.commit()

    updated_history = _history_query(db, user_id, 120)
    return schemas.AIMessageResponse(
        reply=reply,
        context=context,
        history=_serialize_history_rows(updated_history),
    )


@router.post("/public-message", response_model=schemas.AIMessageResponse)
@limiter.limit("40/minute")
async def send_public_ai_message(
    request: Request,
    payload: schemas.AIMessageRequest,
    db: Session = Depends(get_db),
):
    del request
    message = _as_str(payload.message, "").strip()
    if not message:
        raise exceptions.ValidationError("Message cannot be empty")
    if len(message) > 1800:
        raise exceptions.ValidationError("Message is too long")

    page_data = payload.page_data if isinstance(payload.page_data, dict) else {}
    context = _build_public_context(db, payload.path, payload.page_title, page_data=page_data)

    if not _is_allowed_topic(message):
        reply = TOPIC_GUARDRAIL_MESSAGE
    else:
        # In public mode we do not persist or replay history.
        reply = await _generate_ai_reply(message=message, context=context, history=[])

    return schemas.AIMessageResponse(reply=reply, context=context, history=[])
