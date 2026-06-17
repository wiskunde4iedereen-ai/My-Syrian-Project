from fastapi import APIRouter, Depends, Request, Form
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from fastapi.responses import RedirectResponse

from app.core.database import get_db
from app.models.complaint import Complaint
from app.models.department import Department
from app.models.employee import Employee
from app.modules.auth.deps import get_current_user
from app.models.user import User
from app.templates import render
from app.core.exceptions import NotFound
from app.core.audit import log_audit

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.get("")
async def list_complaints(
    request: Request,
    status: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Complaint)
    if status:
        query = query.where(Complaint.status == status)
    complaints = db.execute(query.order_by(desc(Complaint.id))).scalars().all()
    departments = {d.id: d.name for d in db.execute(select(Department)).scalars().all()}
    employees = {e.id: e for e in db.execute(select(Employee)).scalars().all()}
    return render("complaints/list.html", request=request, complaints=complaints, departments=departments, employees=employees, current_status=status, show_nav=True)


@router.get("/create")
async def create_form(request: Request, db: Session = Depends(get_db)):
    departments = db.execute(select(Department)).scalars().all()
    return render("complaints/form.html", request=request, complaint=None, departments=departments, show_nav=True)


@router.post("/create")
async def create(
    request: Request,
    sender_name: str = Form(...),
    sender_contact: str = Form(""),
    subject: str = Form(...),
    description: str = Form(""),
    department_id: int = Form(0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dept_id = department_id if department_id else None
    comp = Complaint(sender_name=sender_name, sender_contact=sender_contact, subject=subject, description=description, department_id=dept_id)
    db.add(comp)
    db.commit()
    db.refresh(comp)
    log_audit(db, current_user, "CREATE", "Complaint", comp.id, f"إنشاء شكوى: {subject}")
    return RedirectResponse(url="/complaints", status_code=302)


@router.get("/{comp_id}/respond")
async def respond_form(
    comp_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comp = db.execute(select(Complaint).where(Complaint.id == comp_id)).scalar_one_or_none()
    if not comp:
        raise NotFound("الشكوى غير موجودة")
    return render("complaints/respond.html", request=request, complaint=comp, show_nav=True)


@router.post("/{comp_id}/respond")
async def respond(
    comp_id: int,
    request: Request,
    response: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comp = db.execute(select(Complaint).where(Complaint.id == comp_id)).scalar_one_or_none()
    if not comp:
        raise NotFound("الشكوى غير موجودة")
    emp = getattr(request.state, "employee", None)
    comp.response = response
    comp.status = "closed"
    comp.assigned_to = emp.id if emp else comp.assigned_to
    db.commit()
    log_audit(db, current_user, "UPDATE", "Complaint", comp_id, "الرد على شكوى")
    return RedirectResponse(url="/complaints", status_code=302)
