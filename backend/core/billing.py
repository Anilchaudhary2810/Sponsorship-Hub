from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class PlanDefinition:
    code: str
    name: str
    monthly_price_inr: int
    limits: dict[str, int]
    features: list[str]


PLAN_DEFINITIONS: dict[str, PlanDefinition] = {
    "free": PlanDefinition(
        code="free",
        name="Free",
        monthly_price_inr=0,
        limits={
            "events_per_month": 5,
            "campaigns_per_month": 5,
            "deals_per_month": 30,
            "chat_messages_per_month": 1000,
        },
        features=[
            "Core dashboards",
            "Deal lifecycle tracking",
            "Basic analytics",
        ],
    ),
    "starter": PlanDefinition(
        code="starter",
        name="Starter",
        monthly_price_inr=2499,
        limits={
            "events_per_month": 25,
            "campaigns_per_month": 25,
            "deals_per_month": 200,
            "chat_messages_per_month": 8000,
        },
        features=[
            "Priority notifications",
            "Advanced dashboard filters",
            "Extended analytics",
        ],
    ),
    "growth": PlanDefinition(
        code="growth",
        name="Growth",
        monthly_price_inr=7999,
        limits={
            "events_per_month": 120,
            "campaigns_per_month": 120,
            "deals_per_month": 1200,
            "chat_messages_per_month": 50000,
        },
        features=[
            "Ops metrics",
            "Audit event visibility",
            "Faster support response",
        ],
    ),
    "enterprise": PlanDefinition(
        code="enterprise",
        name="Enterprise",
        monthly_price_inr=19999,
        limits={
            "events_per_month": 10000,
            "campaigns_per_month": 10000,
            "deals_per_month": 100000,
            "chat_messages_per_month": 1000000,
        },
        features=[
            "High-volume limits",
            "Security and compliance support",
            "Dedicated onboarding",
        ],
    ),
}


def normalize_plan_tier(value: Any) -> str:
    tier = str(value or "free").strip().lower()
    if tier not in PLAN_DEFINITIONS:
        return "free"
    return tier


def month_window_utc(now: datetime | None = None) -> tuple[datetime, datetime]:
    ref = now or datetime.now(timezone.utc)
    start = ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end
