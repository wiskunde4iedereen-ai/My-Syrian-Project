from fastapi import APIRouter, Depends, Request, Form
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from fastapi.responses import RedirectResponse

from app.core.database import get_db
from app.models.vacation_request import VacationRequest
from app.modules.auth.deps import get_current_user
from app.models.user import User
from app.templates import render
from app.core.audit import log_audit

router = APIRouter(prefix="/vacation", tags=["vacation"])


@router.get("/my-requests")
async def my_requests(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    requests_ = db.execute(
        select(VacationRequest).where(VacationRequest.user_id == current_user.id).order_by(desc(VacationRequest.id))
    ).scalars().all()
    return render("vacation/my_requests.html", request=request, requests=requests_, show_nav=True)


@router.get("/request")
async def request_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return render("vacation/form.html", request=request, show_nav=True)


@router.post("/request")
async def submit_request(
    request: Request,
    start_date: str = Form(...),
    days: int = Form(...),
    reason: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vr = VacationRequest(user_id=current_user.id, start_date=start_date, days=days, reason=reason)
    db.add(vr)
    db.commit()
    db.refresh(vr)
    log_audit(db, current_user, "CREATE", "VacationRequest", vr.id, "تقديم طلب إجازة")
    return render("vacation/form.html", request=request, success="تم تقديم طلب الإجازة بنجاح", show_nav=True)
