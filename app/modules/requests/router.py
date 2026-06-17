from fastapi import APIRouter, Depends, Request, Form
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from fastapi.responses import RedirectResponse

from app.core.database import get_db
from app.models.request import Request as RequestModel
from app.models.employee import Employee
from app.modules.auth.deps import get_current_user
from app.models.user import User
from app.templates import render
from app.core.exceptions import NotFound
from app.core.audit import log_audit

router = APIRouter(prefix="/requests", tags=["requests"])


@router.get("")
async def list_requests(
    request: Request,
    status: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(RequestModel)
    if status:
        query = query.where(RequestModel.status == status)
    requests = db.execute(query.order_by(desc(RequestModel.id))).scalars().all()
    employees = {e.id: e for e in db.execute(select(Employee)).scalars().all()}
    return render("requests/list.html", request=request, requests=requests, employees=employees, current_status=status, show_nav=True)


@router.get("/create")
async def create_form(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return render("requests/form.html", request=request, req=None, show_nav=True)


@router.post("/create")
async def create(
    request: Request,
    request_type: str = Form(...),
    subject: str = Form(...),
    description: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    emp = getattr(request.state, "employee", None)
    if not emp:
        from app.core.exceptions import BadRequest
        raise BadRequest("يجب أن يكون لديك سجل موظف لتقديم طلب")
    req = RequestModel(employee_id=emp.id, request_type=request_type, subject=subject, description=description)
    db.add(req)
    db.commit()
    db.refresh(req)
    log_audit(db, current_user, "CREATE", "Request", req.id, f"إنشاء طلب: {subject}")
    return RedirectResponse(url="/requests", status_code=302)


@router.post("/{req_id}/approve")
async def approve(
    req_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = db.execute(select(RequestModel).where(RequestModel.id == req_id)).scalar_one_or_none()
    if not req:
        raise NotFound("الطلب غير موجود")
    emp = getattr(request.state, "employee", None)
    req.status = "approved"
    req.reviewed_by = emp.id if emp else None
    db.commit()
    log_audit(db, current_user, "UPDATE", "Request", req_id, "اعتماد طلب")
    return RedirectResponse(url="/requests", status_code=302)


@router.post("/{req_id}/reject")
async def reject(
    req_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = db.execute(select(RequestModel).where(RequestModel.id == req_id)).scalar_one_or_none()
    if not req:
        raise NotFound("الطلب غير موجود")
    emp = getattr(request.state, "employee", None)
    req.status = "rejected"
    req.reviewed_by = emp.id if emp else None
    db.commit()
    log_audit(db, current_user, "UPDATE", "Request", req_id, "رفض طلب")
    return RedirectResponse(url="/requests", status_code=302)
