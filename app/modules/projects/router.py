from fastapi import APIRouter, Depends, Request, Form
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from fastapi.responses import RedirectResponse

from app.core.database import get_db
from app.models.project import Project
from app.models.department import Department
from app.modules.auth.deps import get_current_user
from app.models.user import User
from app.templates import render
from app.core.exceptions import NotFound
from app.core.audit import log_audit

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
async def list_projects(
    request: Request,
    status: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Project)
    if status:
        query = query.where(Project.status == status)
    projects = db.execute(query.order_by(desc(Project.id))).scalars().all()
    departments = {d.id: d.name for d in db.execute(select(Department)).scalars().all()}
    return render("projects/list.html", request=request, projects=projects, departments=departments, current_status=status, show_nav=True)


@router.get("/create")
async def create_form(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    departments = db.execute(select(Department)).scalars().all()
    return render("projects/form.html", request=request, project=None, departments=departments, show_nav=True)


@router.post("/create")
async def create(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    department_id: int = Form(0),
    budget: float = Form(0.0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    emp = getattr(request.state, "employee", None)
    if not emp:
        from app.core.exceptions import BadRequest
        raise BadRequest("يجب أن يكون لديك سجل موظف")
    dept_id = department_id if department_id else None
    proj = Project(name=name, description=description, department_id=dept_id, budget=budget if budget else None, created_by=emp.id)
    db.add(proj)
    db.commit()
    db.refresh(proj)
    log_audit(db, current_user, "CREATE", "Project", proj.id, f"إنشاء مشروع: {name}")
    return RedirectResponse(url="/projects", status_code=302)
