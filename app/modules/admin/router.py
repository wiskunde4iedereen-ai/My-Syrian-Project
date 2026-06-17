import os, io, shutil, zipfile
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from fastapi.responses import RedirectResponse

from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.department import Department
from app.models.employee import Employee
from app.models.role import Role
from app.models.permission import Permission
from app.modules.auth.deps import get_current_user
from app.templates import render
from app.core.audit import log_audit
from app.core.security import hash_password
from app.core.config import get_settings
from app.core.exceptions import Conflict, BadRequest

router = APIRouter(prefix="/admin", tags=["admin"])

def _admin_only(request: Request, current_user: User):
    role = getattr(request.state, "role", None)
    role_name = role.name if role else current_user.role
    if role_name not in ("مدير عام", "مطور النظام", "admin") and current_user.role != "admin":
        from app.core.exceptions import Forbidden
        raise Forbidden()


def _dev_only(request: Request, current_user: User):
    """مطور النظام only — إدارة المستخدمين والنسخ والصلاحيات."""
    role = getattr(request.state, "role", None)
    role_name = role.name if role else current_user.role
    if role_name not in ("مطور النظام", "مدير عام", "admin") and current_user.role not in ("developer", "admin"):
        from app.core.exceptions import Forbidden
        raise Forbidden()


@router.get("/audit")
async def audit_logs(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _admin_only(request, current_user)
    logs = db.execute(
        select(AuditLog).order_by(desc(AuditLog.created_at)).limit(200)
    ).scalars().all()
    return render("admin/audit.html", request=request, logs=logs, show_nav=True, user=current_user)

@router.get("/employees")
async def employees(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _admin_only(request, current_user)
    users = db.execute(
        select(User).order_by(User.id.desc())
    ).scalars().all()
    return render("admin/employees.html", request=request, users=users, show_nav=True, user=current_user)

@router.get("/employees/{user_id}")
async def employee_detail(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _admin_only(request, current_user)
    target = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not target:
        from app.core.exceptions import NotFound
        raise NotFound("الموظف غير موجود")
    logs = db.execute(
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(desc(AuditLog.created_at))
        .limit(500)
    ).scalars().all()
    return render("admin/employee_detail.html", request=request, emp=target, logs=logs, show_nav=True, user=current_user)

@router.post("/employees/{user_id}/deactivate")
async def deactivate_employee(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _admin_only(request, current_user)
    target = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not target:
        from app.core.exceptions import NotFound
        raise NotFound("الموظف غير موجود")
    role = getattr(request.state, "role", None)
    role_name = role.name if role else current_user.role
    if role_name in ("مدير عام", "مطور النظام", "admin"):
        pass
    target.is_active = False
    db.commit()
    log_audit(db, current_user, "UPDATE", "User", user_id, f"سحب صلاحيات الموظف: {target.name}")
    return RedirectResponse(url=f"/admin/employees/{user_id}", status_code=302)

@router.post("/employees/{user_id}/reactivate")
async def reactivate_employee(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _admin_only(request, current_user)
    target = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not target:
        from app.core.exceptions import NotFound
        raise NotFound("الموظف غير موجود")
    target.is_active = True
    db.commit()
    log_audit(db, current_user, "UPDATE", "User", user_id, f"إعادة صلاحيات الموظف: {target.name}")
    return RedirectResponse(url=f"/admin/employees/{user_id}", status_code=302)


@router.get("/departments")
async def list_departments(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _admin_only(request, current_user)
    depts = db.execute(select(Department).order_by(Department.sort_order)).scalars().all()
    return render("admin/departments.html", request=request, departments=depts, show_nav=True, user=current_user)


@router.post("/departments/create")
async def create_department(
    name: str = Form(...),
    parent_id: int = Form(0),
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _admin_only(request, current_user)
    pid = parent_id if parent_id else None
    dept = Department(name=name, parent_id=pid)
    db.add(dept)
    db.commit()
    log_audit(db, current_user, "CREATE", "Department", dept.id, f"إنشاء قسم: {name}")
    return RedirectResponse(url="/admin/departments", status_code=302)


@router.post("/departments/{dept_id}/delete")
async def delete_department(
    dept_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _admin_only(request, current_user)
    dept = db.execute(select(Department).where(Department.id == dept_id)).scalar_one_or_none()
    if not dept:
        from app.core.exceptions import NotFound
        raise NotFound("القسم غير موجود")
    name = dept.name
    db.delete(dept)
    db.commit()
    log_audit(db, current_user, "DELETE", "Department", dept_id, f"حذف قسم: {name}")
    return RedirectResponse(url="/admin/departments", status_code=302)


@router.get("/users")
async def user_management(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _dev_only(request, current_user)
    users = db.execute(
        select(User).order_by(User.id.desc())
    ).scalars().all()
    roles = {r.id: r.name for r in db.execute(select(Role)).scalars().all()}
    role = getattr(request.state, "role", None)
    role_name = role.name if role else current_user.role
    is_dev = role_name == "مطور النظام"
    return render("admin/user_management.html", request=request, users=users, roles=roles, is_dev=is_dev, show_nav=True, user=current_user)


# ---------- User management (مطور النظام) ----------

@router.get("/users/create")
async def create_user_form(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _dev_only(request, current_user)
    roles = db.execute(select(Role).order_by(Role.id)).scalars().all()
    return render("admin/create_user.html", request=request, roles=roles, show_nav=True, user=current_user)


@router.post("/users/create")
async def create_user(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role_id: int = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _dev_only(request, current_user)
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing:
        raise Conflict("البريد الإلكتروني مستخدم بالفعل")
    if len(password) < 6:
        raise BadRequest("كلمة المرور يجب أن تكون 6 أحرف على الأقل")
    role = db.execute(select(Role).where(Role.id == role_id)).scalar_one_or_none()
    if not role:
        from app.core.exceptions import NotFound
        raise NotFound("الصفة غير موجودة")
    user = User(
        name=name,
        email=email,
        hashed_password=hash_password(password),
        role="employee",
        role_id=role.id,
        must_change_password=True,
    )
    db.add(user)
    db.commit()
    log_audit(db, current_user, "CREATE", "User", user.id, f"إنشاء مستخدم جديد: {name} ({email}) بصفة {role.name}")
    roles = db.execute(select(Role).order_by(Role.id)).scalars().all()
    return render("admin/create_user.html", request=request, roles=roles,
                  success=f"تم إنشاء المستخدم {name} بنجاح. كلمة المرور المؤقتة: {password}",
                  show_nav=True, user=current_user)


@router.post("/users/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _dev_only(request, current_user)
    target = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not target:
        from app.core.exceptions import NotFound
        raise NotFound("المستخدم غير موجود")
    import secrets
    temp_password = secrets.token_hex(4)
    target.hashed_password = hash_password(temp_password)
    target.must_change_password = True
    db.commit()
    log_audit(db, current_user, "UPDATE", "User", user_id, f"إعادة تعيين كلمة سر المستخدم: {target.name}")
    users = db.execute(select(User).order_by(User.id.desc())).scalars().all()
    roles = {r.id: r.name for r in db.execute(select(Role)).scalars().all()}
    role = getattr(request.state, "role", None)
    role_name = role.name if role else current_user.role
    is_dev = role_name == "مطور النظام"
    return render("admin/user_management.html", request=request,
                  users=users, roles=roles, is_dev=is_dev,
                  success=f"تم إعادة تعيين كلمة السر للمستخدم {target.name}. كلمة المرور الجديدة: {temp_password}",
                  show_nav=True, user=current_user)


# ---------- Backup (مطور النظام) ----------

@router.get("/backup")
async def backup_page(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    _dev_only(request, current_user)
    return render("admin/backup.html", request=request, show_nav=True, user=current_user)


@router.get("/backup/export")
async def export_backup(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _dev_only(request, current_user)
    settings = get_settings()
    db_path = settings.database_url.replace("sqlite:///", "")
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="قاعدة البيانات غير موجودة")
    backup_dir = os.path.join(os.path.dirname(db_path), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_name = f"heya_backup_{timestamp}.zip"
    backup_path = os.path.join(backup_dir, backup_name)
    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(db_path, os.path.basename(db_path))
    log_audit(db, current_user, "CREATE", "Backup", 0, f"تصدير نسخة احتياطية: {backup_name}")
    return FileResponse(backup_path, filename=backup_name, media_type="application/zip")


# ---------- Permissions management (مطور النظام) ----------

RESOURCE_LIST = ["exporters", "products", "markets", "licenses", "finance", "documents",
                  "reports", "employees", "audit", "departments", "requests", "projects",
                  "events", "complaints", "users", "backup", "planning_reports"]
ACTION_FIELDS = ["can_view", "can_create", "can_edit", "can_delete", "can_approve"]


@router.get("/permissions")
async def permissions_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _dev_only(request, current_user)
    roles = db.execute(select(Role).order_by(Role.id)).scalars().all()
    perms = db.execute(select(Permission)).scalars().all()
    perm_map = {(p.role_id, p.resource): p for p in perms}
    return render("admin/permissions.html", request=request, roles=roles,
                  resources=RESOURCE_LIST, perm_map=perm_map, show_nav=True, user=current_user)


@router.post("/permissions/update")
async def update_permissions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _dev_only(request, current_user)
    form = await request.form()
    roles = db.execute(select(Role).order_by(Role.id)).scalars().all()
    for role in roles:
        for resource in RESOURCE_LIST:
            perm = db.execute(
                select(Permission).where(Permission.role_id == role.id, Permission.resource == resource)
            ).scalar_one_or_none()
            if not perm:
                perm = Permission(role_id=role.id, resource=resource)
                db.add(perm)
            for field in ACTION_FIELDS:
                key = f"{role.id}_{resource}_{field}"
                setattr(perm, field, key in form)
    db.commit()
    log_audit(db, current_user, "UPDATE", "Permissions", 0, "تحديث جميع الصلاحيات")
    roles = db.execute(select(Role).order_by(Role.id)).scalars().all()
    perms = db.execute(select(Permission)).scalars().all()
    perm_map = {(p.role_id, p.resource): p for p in perms}
    return render("admin/permissions.html", request=request, roles=roles,
                  resources=RESOURCE_LIST, perm_map=perm_map,
                  success="تم حفظ الصلاحيات بنجاح", show_nav=True, user=current_user)
