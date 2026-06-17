from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.models.user import User

def log_audit(
    db: Session,
    user: User,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    details: str = "",
):
    log = AuditLog(
        user_id=user.id,
        user_name=user.name,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
    db.add(log)
    db.commit()
