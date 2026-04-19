from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from .. import exceptions, models, schemas
from ..core.limiter import limiter
from ..database import get_db
from .auth_router import get_current_user

router = APIRouter(prefix="/integrations", tags=["Integrations"])


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_str(value: Any, default: str = "") -> str:
    if isinstance(value, str):
        return value
    return default


def _get_connection(db: Session, user_id: int, provider: str) -> models.IntegrationConnection | None:
    return db.query(models.IntegrationConnection).filter(
        models.IntegrationConnection.user_id == user_id,
        models.IntegrationConnection.provider == provider,
    ).first()


def _log_event(
    db: Session,
    connection_id: int,
    event_type: str,
    status: str,
    request_payload: dict[str, Any],
    response_payload: dict[str, Any],
) -> models.IntegrationEvent:
    event = models.IntegrationEvent(
        connection_id=connection_id,
        event_type=event_type,
        status=status,
        request_payload=request_payload,
        response_payload=response_payload,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/connections", response_model=list[schemas.IntegrationConnectionResponse])
@limiter.limit("80/minute")
def list_connections(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    user_id = _as_int(getattr(current_user, "id", 0))
    return db.query(models.IntegrationConnection).filter(
        models.IntegrationConnection.user_id == user_id
    ).order_by(models.IntegrationConnection.provider.asc()).all()


@router.post("/connect", response_model=schemas.IntegrationConnectionResponse)
@limiter.limit("40/minute")
def connect_provider(
    request: Request,
    payload: schemas.IntegrationConnectRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    user_id = _as_int(getattr(current_user, "id", 0))
    provider = payload.provider

    existing = _get_connection(db, user_id, provider)
    if existing:
        existing_config = getattr(existing, "config_json", {})
        merged_config = payload.config_json if payload.config_json is not None else (existing_config if isinstance(existing_config, dict) else {})
        setattr(existing, "status", "connected")
        setattr(existing, "config_json", merged_config)
        setattr(existing, "last_sync_at", datetime.utcnow())
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    conn = models.IntegrationConnection(
        user_id=user_id,
        provider=provider,
        status="connected",
        config_json=payload.config_json or {},
        last_sync_at=None,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return conn


@router.delete("/{provider}")
@limiter.limit("40/minute")
def disconnect_provider(
    request: Request,
    provider: schemas.IntegrationProvider,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    user_id = _as_int(getattr(current_user, "id", 0))
    conn = _get_connection(db, user_id, provider)
    if not conn:
        raise exceptions.ValidationError("Integration not connected")
    setattr(conn, "status", "disconnected")
    db.add(conn)
    db.commit()
    return {"ok": True}


@router.post("/{provider}/sync", response_model=schemas.IntegrationEventResponse)
@limiter.limit("60/minute")
def sync_provider(
    request: Request,
    provider: schemas.IntegrationProvider,
    payload: schemas.IntegrationSyncRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    user_id = _as_int(getattr(current_user, "id", 0))
    conn = _get_connection(db, user_id, provider)
    if not conn or _as_str(getattr(conn, "status", "")) != "connected":
        raise exceptions.ValidationError(f"{provider} integration is not connected")

    if provider == "hubspot":
        response_payload = {
            "synced": True,
            "entity": payload.payload.get("entity", "deal"),
            "external_id": f"hs_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        }
    elif provider == "sheets":
        response_payload = {"synced": True, "sheet_url": payload.payload.get("sheet_url", "https://docs.google.com/spreadsheets/")}
    elif provider == "slack":
        response_payload = {"sent": True, "channel": payload.payload.get("channel", "#alerts")}
    elif provider == "email":
        response_payload = {"sent": True, "to": payload.payload.get("to", getattr(current_user, "email", "unknown@example.com"))}
    else:  # calendar
        response_payload = {"synced": True, "event_count": _as_int(payload.payload.get("event_count", 1), default=1)}

    setattr(conn, "last_sync_at", datetime.utcnow())
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return _log_event(
        db,
        connection_id=_as_int(getattr(conn, "id", 0)),
        event_type=payload.event_type,
        status="success",
        request_payload=payload.payload,
        response_payload=response_payload,
    )


@router.get("/{provider}/events", response_model=list[schemas.IntegrationEventResponse])
@limiter.limit("80/minute")
def list_integration_events(
    request: Request,
    provider: schemas.IntegrationProvider,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    user_id = _as_int(getattr(current_user, "id", 0))
    safe_limit = max(1, min(200, int(limit)))
    conn = _get_connection(db, user_id, provider)
    if not conn:
        return []
    return db.query(models.IntegrationEvent).filter(
        models.IntegrationEvent.connection_id == conn.id
    ).order_by(models.IntegrationEvent.created_at.desc()).limit(safe_limit).all()


@router.post("/{provider}/test-alert", response_model=schemas.IntegrationEventResponse)
@limiter.limit("40/minute")
def send_test_alert(
    request: Request,
    provider: schemas.IntegrationProvider,
    payload: schemas.IntegrationSyncRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    user_id = _as_int(getattr(current_user, "id", 0))
    conn = _get_connection(db, user_id, provider)
    if not conn or _as_str(getattr(conn, "status", "")) != "connected":
        raise exceptions.ValidationError(f"{provider} integration is not connected")

    if provider not in {"slack", "email"}:
        raise exceptions.ValidationError("Test alert is supported only for slack/email")

    response_payload = {
        "ok": True,
        "provider": provider,
        "message": payload.payload.get("message", "This is a test alert from Sponsorship Hub."),
        "sent_at": datetime.utcnow().isoformat(),
    }
    return _log_event(
        db,
        connection_id=_as_int(getattr(conn, "id", 0)),
        event_type=f"{provider}_test_alert",
        status="success",
        request_payload=payload.payload,
        response_payload=response_payload,
    )


@router.get("/sheets/export.csv")
@limiter.limit("40/minute")
def export_deals_csv_for_sheets(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    user_id = _as_int(getattr(current_user, "id", 0))
    role = _as_str(getattr(current_user, "role", ""))
    deals_query = db.query(models.Deal)
    if role == "sponsor":
        deals_query = deals_query.filter(models.Deal.sponsor_id == user_id)
    elif role == "organizer":
        deals_query = deals_query.filter(models.Deal.organizer_id == user_id)
    else:
        deals_query = deals_query.filter(models.Deal.influencer_id == user_id)
    deals = deals_query.order_by(models.Deal.created_at.desc()).limit(500).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["deal_id", "deal_type", "status", "payment_status", "payment_amount", "currency", "created_at"])
    for deal in deals:
        writer.writerow(
            [
                _as_int(getattr(deal, "id", 0)),
                _as_str(getattr(deal, "deal_type", "")),
                _as_str(getattr(deal, "status", "")),
                _as_str(getattr(deal, "payment_status", "")),
                str(getattr(deal, "payment_amount", 0) or 0),
                _as_str(getattr(deal, "currency", "INR"), default="INR"),
                str(getattr(deal, "created_at", "")),
            ]
        )
    csv_text = output.getvalue()
    filename = f"deals-export-{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/calendar/export.ics")
@limiter.limit("40/minute")
def export_calendar_ics(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    user_id = _as_int(getattr(current_user, "id", 0))
    role = _as_str(getattr(current_user, "role", ""))

    if role == "organizer":
        events = db.query(models.Event).filter(models.Event.organizer_id == user_id).order_by(models.Event.date.asc()).limit(200).all()
    elif role == "sponsor":
        event_ids = [eid for (eid,) in db.query(models.Deal.event_id).filter(models.Deal.sponsor_id == user_id, models.Deal.event_id.isnot(None)).all()]
        events = db.query(models.Event).filter(models.Event.id.in_(event_ids)).order_by(models.Event.date.asc()).limit(200).all() if event_ids else []
    else:
        event_ids = [eid for (eid,) in db.query(models.Deal.event_id).filter(models.Deal.influencer_id == user_id, models.Deal.event_id.isnot(None)).all()]
        events = db.query(models.Event).filter(models.Event.id.in_(event_ids)).order_by(models.Event.date.asc()).limit(200).all() if event_ids else []

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SponsorshipHub//EN",
    ]
    now_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    for event in events:
        if not getattr(event, "date", None):
            continue
        start = f"{event.date.strftime('%Y%m%d')}T090000Z"
        end = f"{event.date.strftime('%Y%m%d')}T170000Z"
        uid = f"event-{event.id}@sponsorshiphub.local"
        title = _as_str(getattr(event, "title", "Event"), default="Event")
        location = _as_str(getattr(event, "location", ""), default="")
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now_stamp}",
                f"DTSTART:{start}",
                f"DTEND:{end}",
                f"SUMMARY:{title}",
                f"LOCATION:{location}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    ics_body = "\r\n".join(lines) + "\r\n"
    filename = f"calendar-export-{datetime.utcnow().strftime('%Y%m%d')}.ics"
    return Response(
        content=ics_body,
        media_type="text/calendar",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
