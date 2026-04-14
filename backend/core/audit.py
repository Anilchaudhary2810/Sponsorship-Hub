from typing import Optional
from sqlalchemy.orm import Session

from .. import models


def log_audit_event(
    db: Session,
    action: str,
    actor_user_id: Optional[int] = None,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    event = models.AuditEvent(
        action=action,
        actor_user_id=actor_user_id,
        target_type=target_type,
        target_id=target_id,
        ip_address=ip_address,
        user_agent=user_agent,
        event_meta=metadata or {},
    )
    db.add(event)
    db.commit()
