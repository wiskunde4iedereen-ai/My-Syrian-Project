from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.notification import Notification
from app.modules.auth.deps import get_current_user
from app.models.user import User
from app.templates import render

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/count")
async def unread_count(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id, Notification.is_read == False
        )
    ).scalar()
    return {"count": count}


@router.get("")
async def list_notifications(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notifications = db.execute(
        select(Notification).where(Notification.user_id == current_user.id).order_by(Notification.id.desc())
    ).scalars().all()
    return render("notifications/list.html", request=request, notifications=notifications, show_nav=True)


@router.post("/read-all")
async def mark_all_read(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.execute(
        select(Notification).where(Notification.user_id == current_user.id, Notification.is_read == False)
    )
    notifications = db.execute(
        select(Notification).where(Notification.user_id == current_user.id, Notification.is_read == False)
    ).scalars().all()
    for n in notifications:
        n.is_read = True
    db.commit()
    return {"ok": True}
