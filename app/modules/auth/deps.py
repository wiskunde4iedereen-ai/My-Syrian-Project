from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.models.employee import Employee
from app.models.role import Role
from app.models.permission import Permission
from app.core.exceptions import Unauthorized, Forbidden


def _get_token(request: Request, authorization: str | None = Header(None)) -> str | None:
    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ")[1]
    cookie = request.cookies.get("access_token")
    if cookie and cookie.startswith("Bearer "):
        return cookie.split(" ")[1]
    return None


def get_current_user(
    request: Request,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User:
    token = _get_token(request, authorization)
    if not token:
        raise Unauthorized("يرجى تسجيل الدخول")
    payload = decode_token(token)
    if payload is None:
        raise Unauthorized("رمز الدخول غير صالح أو منتهي الصلاحية")
    user = db.execute(select(User).where(User.id == int(payload.get("sub")))).scalar_one_or_none()
    if not user or not user.is_active:
        raise Unauthorized("المستخدم غير موجود أو غير نشط")
    request.state.user = user
    emp = db.execute(select(Employee).where(Employee.user_id == user.id)).scalar_one_or_none()
    request.state.employee = emp
    request.state.permissions = []
    if emp and emp.role_id:
        role = db.execute(select(Role).where(Role.id == emp.role_id)).scalar_one_or_none()
        request.state.role = role
        if role:
            perms = db.execute(select(Permission).where(Permission.role_id == role.id)).scalars().all()
            request.state.permissions = perms
    else:
        request.state.role = None
    return user


def get_current_employee(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Employee | None:
    return request.state.employee


def has_permission(resource: str, action: str) -> bool:
    def checker(request: Request, current_user: User = Depends(get_current_user)) -> bool:
        permissions = getattr(request.state, "permissions", [])
        for p in permissions:
            if p.resource == resource and getattr(p, f"can_{action}", False):
                return True
        raise Forbidden("ليس لديك صلاحية للوصول إلى هذه الميزة")
    return checker


ROLE_MAP = {
    "مدير عام": "admin",
    "معاون مدير عام": "admin",
    "مدير مديرية": "employee",
    "رئيس دائرة": "employee",
    "موظف": "employee",
    "مطور النظام": "developer",
}


def require_role(*roles: str):
    def role_checker(request: Request, current_user: User = Depends(get_current_user)) -> User:
        role = getattr(request.state, "role", None)
        role_name = role.name if role else current_user.role
        mapped = ROLE_MAP.get(role_name, current_user.role)
        if role_name not in roles and mapped not in roles and current_user.role not in roles:
            raise Forbidden("ليس لديك صلاحية للوصول إلى هذه الميزة")
        request.state.user = current_user
        return current_user
    return role_checker


PLANNING_DEPT_ID = 4


def is_planning_director(request: Request) -> bool:
    emp = getattr(request.state, "employee", None)
    if not emp or emp.department_id != PLANNING_DEPT_ID:
        return False
    role = getattr(request.state, "role", None)
    return bool(role and role.name == "مدير مديرية")
