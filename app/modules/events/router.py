from fastapi import APIRouter, Depends, Request, Form
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from fastapi.responses import RedirectResponse

from app.core.database import get_db
from app.models.event import Event
from app.models.department import Department
from app.modules.auth.deps import get_current_user
from app.models.user import User
from app.templates import render
from app.core.exceptions import NotFound
from app.core.audit import log_audit

router = APIRouter(prefix="/events", tags=["events"])


@router.get("")
async def list_events(
    request: Request,
    status: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Event)
    if status:
        query = query.where(Event.status == status)
    events = db.execute(query.order_by(desc(Event.id))).scalars().all()
    departments = {d.id: d.name for d in db.execute(select(Department)).scalars().all()}
    return render("events/list.html", request=request, events=events, departments=departments, current_status=status, show_nav=True)


@router.get("/create")
async def create_form(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    departments = db.execute(select(Department)).scalars().all()
    return render("events/form.html", request=request, event=None, departments=departments, show_nav=True)


@router.post("/create")
async def create(
    request: Request,
    name: str = Form(...),
    event_type: str = Form(""),
    description: str = Form(""),
    location: str = Form(""),
    department_id: int = Form(0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    emp = getattr(request.state, "employee", None)
    if not emp:
        from app.core.exceptions import BadRequest
        raise BadRequest("يجب أن يكون لديك سجل موظف")
    dept_id = department_id if department_id else None
    ev = Event(name=name, event_type=event_type, description=description, location=location, department_id=dept_id, created_by=emp.id)
    db.add(ev)
    db.commit()
    db.refresh(ev)
    log_audit(db, current_user, "CREATE", "Event", ev.id, f"إنشاء فعالية: {name}")
    return RedirectResponse(url="/events", status_code=302)
