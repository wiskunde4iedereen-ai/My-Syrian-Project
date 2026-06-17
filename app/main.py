import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.core.database import engine, SessionLocal, Base, get_db
from sqlalchemy.orm import Session
from app.core.logging_config import setup_logging, get_logger
from app.core.config import get_settings
from app.core.security import hash_password
from app.modules.auth.deps import get_current_user, get_current_employee
from app.modules.auth.router import router as auth_router
from app.models.user import User
from app.models.employee import Employee
from app.models.department import Department
from app.models.role import Role
from app.models.permission import Permission
from app.templates import render
from app.core.database import init_db
from app.modules.exporters.router import router as exporters_router
from app.modules.products.router import router as products_router
from app.modules.markets.router import router as markets_router
from app.modules.licenses.router import router as licenses_router
from app.modules.finance.router import router as finance_router
from app.modules.documents.router import router as documents_router
from app.modules.reports.router import router as reports_router
from app.modules.admin.router import router as admin_router
from app.modules.requests.router import router as requests_router
from app.modules.projects.router import router as projects_router
from app.modules.events.router import router as events_router
from app.modules.complaints.router import router as complaints_router
from app.modules.vacation.router import router as vacation_router
from app.modules.notifications.router import router as notifications_router
from app.modules.planning.router import router as planning_router
from app.models.exporter import Exporter
from app.models.product import Product
from app.models.market import Market
from app.models.license import License
from app.models.finance import Finance
from app.models.document import Document
from app.models.project import Project
from app.models.event import Event
from app.models.complaint import Complaint
from app.models.vacation_request import VacationRequest
from app.models.notification import Notification
from app.models.planning import PlanningReport, PlanningReportStatus
from sqlalchemy import func

# Initialize database tables (must be after all model imports)
init_db()

# Seed default data
seed_db = SessionLocal()

# Seed roles
role_map = {}
role_names = [
    ("مدير عام", "Director General", False),
    ("معاون مدير عام", "Deputy Director General", False),
    ("مدير مديرية", "Directorate Manager", False),
    ("رئيس دائرة", "Department Head", False),
    ("موظف", "Employee", False),
    ("مطور النظام", "System Developer", True),
]
for rn, rne, rs in role_names:
    existing = seed_db.execute(select(Role).where(Role.name == rn)).scalar_one_or_none()
    if not existing:
        r = Role(name=rn, name_en=rne, is_system=rs)
        seed_db.add(r)
        seed_db.flush()
        role_map[rn] = r.id
    else:
        role_map[rn] = existing.id

# Seed departments (org structure)
dept_names = [
    (1, "مكتب المدير العام", None, 1),
    (2, "محاسبة الإدارة", None, 2),
    (3, "الموارد البشرية", None, 3),
    (4, "التخطيط والتعاون الدولي", None, 4),
    (5, "الخدمات التجارية", None, 5),
    (6, "الترويج والتعاون الدولي", None, 6),
    (7, "العلاقات العامة", 1, 7),
    (8, "الرقابة الداخلية", 1, 8),
    (9, "دعم سعر الفائدة", 1, 9),
    (10, "الإيرادات والمصروفات", 2, 10),
    (11, "الموازنة والتدقيق", 2, 11),
    (12, "شؤون العاملين والخدمات", 3, 12),
    (13, "الشؤون القانونية", 3, 13),
    (14, "التأمين الصحي", 3, 14),
    (15, "التخطيط والمتابعة", 4, 15),
    (16, "الإحصاء والدراسات", 4, 16),
    (17, "المعرض الدائم", 5, 17),
    (18, "مركز تدريب الإدارة الخارجية", 5, 18),
    (19, "الترويج والمعارض والمؤتمرات", 6, 19),
    (20, "نقطة التجارة الدولية", 6, 20),
    (21, "المعلوماتية", 6, 21),
]
dept_map = {}
for did, dn, pid, order in dept_names:
    existing = seed_db.execute(select(Department).where(Department.id == did)).scalar_one_or_none()
    if not existing:
        d = Department(id=did, name=dn, parent_id=pid, sort_order=order)
        seed_db.add(d)
        seed_db.flush()
    dept_map[dn] = did

# Seed permissions for each role
resource_list = ["exporters", "products", "markets", "licenses", "finance", "documents",
                  "reports", "employees", "audit", "departments", "requests", "projects",
                  "events", "complaints", "users", "backup", "planning_reports"]
perm_rules = {
    "مدير عام": {r: ("view", "create", "edit", "delete", "approve") for r in resource_list},
    "معاون مدير عام": {r: ("view", "create", "edit", "approve") for r in resource_list if r not in ("users", "backup", "departments")},
    "مدير مديرية": {r: ("view", "create", "edit") for r in resource_list if r in ("exporters", "products", "licenses", "finance", "documents", "requests", "projects", "events", "planning_reports")},
    "رئيس دائرة": {r: ("view", "create") for r in ("exporters", "products", "licenses", "finance", "documents", "requests")},
    "موظف": {"requests": ("view", "create")},
    "مطور النظام": {r: ("view", "create", "edit", "delete", "approve") for r in ("users", "backup", "employees", "audit", "departments", "reports", "planning_reports")},
}
action_map = {"view": "can_view", "create": "can_create", "edit": "can_edit", "delete": "can_delete", "approve": "can_approve"}
for rn, resources in perm_rules.items():
    rid = role_map.get(rn)
    if not rid:
        continue
    for res, actions in resources.items():
        existing = seed_db.execute(
            select(Permission).where(Permission.role_id == rid, Permission.resource == res)
        ).scalar_one_or_none()
        if existing:
            continue
        kwargs = {"role_id": rid, "resource": res}
        for a in actions:
            col = action_map.get(a)
            if col:
                kwargs[col] = True
        p = Permission(**kwargs)
        seed_db.add(p)

# Seed default users + employees
seed_users = [
    ("مدير النظام", "admin@heya.gov.sy", "admin123", role_map.get("مدير عام"), "EMP001"),
    ("المطور", "dev@heya.gov.sy", "dev123", role_map.get("مطور النظام"), "EMP002"),
    ("موظف", "emp@heya.gov.sy", "emp123", role_map.get("موظف"), "EMP003"),
    ("مدير التخطيط والتعاون الدولي", "planning@heya.gov.sy", "planning123", role_map.get("مدير مديرية"), "EMP004"),
]
for un, ue, up, rid, emp_no in seed_users:
    user = seed_db.execute(select(User).where(User.email == ue)).scalar_one_or_none()
    if not user:
        user = User(name=un, email=ue, hashed_password=hash_password(up), role="employee", role_id=rid, must_change_password=False)
        seed_db.add(user)
        seed_db.flush()
    # Create employee record if missing
    existing_emp = seed_db.execute(select(Employee).where(Employee.user_id == user.id)).scalar_one_or_none()
    if not existing_emp:
        dept_id = 4 if emp_no == "EMP004" else None
        emp = Employee(user_id=user.id, employee_no=emp_no, role_id=rid or role_map.get("موظف"), department_id=dept_id)
        seed_db.add(emp)

seed_db.commit()
seed_db.close()

setup_logging()
logger = get_logger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting_up", database_url=get_settings().database_url)
    yield
    logger.info("shutting_down")


app = FastAPI(title="نظام الهيئة", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

app.include_router(auth_router)
app.include_router(exporters_router)
app.include_router(products_router)
app.include_router(markets_router)
app.include_router(licenses_router)
app.include_router(finance_router)
app.include_router(documents_router)
app.include_router(reports_router)
app.include_router(admin_router)
app.include_router(requests_router)
app.include_router(projects_router)
app.include_router(events_router)
app.include_router(complaints_router)
app.include_router(vacation_router)
app.include_router(notifications_router)
app.include_router(planning_router)


@app.get("/")
async def root():
    return RedirectResponse(url="/auth/login")


@app.get("/dashboard")
async def dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    emp = getattr(request.state, "employee", None)
    role = getattr(request.state, "role", None)
    if emp and role and emp.department_id == 4 and role.name == "مدير مديرية":
        return RedirectResponse(url="/planning/dashboard")
    stats = {
        "exporters_count": db.query(func.count(Exporter.id)).scalar(),
        "products_count": db.query(func.count(Product.id)).scalar(),
        "markets_count": db.query(func.count(Market.id)).scalar(),
        "licenses_count": db.query(func.count(License.id)).scalar(),
        "finance_count": db.query(func.count(Finance.id)).scalar(),
        "documents_count": db.query(func.count(Document.id)).scalar(),
    }
    role_name = getattr(request.state, "role", None)
    role_name = role_name.name if role_name else current_user.role
    if role_name in ("موظف", "employee"):
        return render("dashboard/employee.html", request=request, user=current_user, show_nav=True, stats=stats)
    return render("dashboard/index.html", request=request, user=current_user, show_nav=True, stats=stats)
