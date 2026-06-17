from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi.responses import RedirectResponse

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.exceptions import Conflict, Unauthorized, BadRequest
from app.models.user import User
from app.models.employee import Employee
from app.models.role import Role
from app.modules.auth.deps import get_current_user
from app.templates import render

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/login")
async def login_page(request: Request):
    return render("auth/login.html", request=request, show_nav=False)

@router.post("/login")
async def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        raise Unauthorized("البريد الإلكتروني أو كلمة المرور غير صحيحة")
    if not user.is_active:
        raise Unauthorized("الحساب غير نشط")
    token = create_access_token({"sub": str(user.id)})
    redirect_url = "/auth/profile/change-password" if user.must_change_password else "/dashboard"
    response = RedirectResponse(url=redirect_url, status_code=302)
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True, max_age=28800)
    return response

@router.get("/register")
async def register_page(request: Request):
    return render("auth/register.html", request=request, show_nav=False)

@router.post("/register")
async def register(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    if len(password) < 6:
        raise BadRequest("كلمة المرور يجب أن تكون 6 أحرف على الأقل")
    if password != confirm_password:
        raise BadRequest("كلمة المرور غير متطابقة")
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing:
        raise Conflict("البريد الإلكتروني مستخدم بالفعل")
    employee_role = db.execute(select(Role).where(Role.name == "موظف")).scalar_one_or_none()
    user = User(
        name=name,
        email=email,
        hashed_password=hash_password(password),
        role="employee",
        role_id=employee_role.id if employee_role else None,
    )
    db.add(user)
    db.commit()
    token = create_access_token({"sub": str(user.id)})
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True, max_age=28800)
    return response

@router.post("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie("access_token")
    return response

@router.get("/me")
async def get_me(request: Request, current_user: User = Depends(get_current_user)):
    emp = getattr(request.state, "employee", None)
    role = getattr(request.state, "role", None)
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": role.name if role else current_user.role,
        "employee_id": emp.id if emp else None,
        "department_id": emp.department_id if emp else None,
        "must_change_password": current_user.must_change_password,
    }

@router.get("/profile")
async def profile_page(request: Request, current_user: User = Depends(get_current_user)):
    return render("auth/profile.html", request=request, user=current_user, show_nav=True)

@router.post("/profile/save")
async def save_profile(
    request: Request,
    address: str = Form(""),
    phone: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.address = address or None
    current_user.phone = phone or None
    db.commit()
    return render("auth/profile.html", request=request, user=current_user, success="تم حفظ البيانات بنجاح", show_nav=True)

@router.post("/change-password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(current_password, current_user.hashed_password):
        raise BadRequest("كلمة المرور الحالية غير صحيحة")
    if len(new_password) < 6:
        raise BadRequest("كلمة المرور الجديدة يجب أن تكون 6 أحرف على الأقل")
    if new_password != confirm_password:
        raise BadRequest("كلمة المرور الجديدة غير متطابقة")
    current_user.hashed_password = hash_password(new_password)
    current_user.must_change_password = False
    db.commit()
    return render("auth/profile.html", request=request, user=current_user, success="تم تغيير كلمة المرور بنجاح", show_nav=True)

@router.get("/profile/change-password")
async def force_change_password_page(request: Request, current_user: User = Depends(get_current_user)):
    return render("auth/profile.html", request=request, user=current_user, show_nav=True)
