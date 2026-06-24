import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.core.database import get_db
from app.models.user import User
from app.models.employee import Employee
from app.models.department import Department
from app.models.role import Role
from app.models.audit_log import AuditLog
from app.models.notification import Notification
from app.models.planning import PlanningReport, PlanningReportStatus
from app.models.vacation_request import VacationRequest
from app.models.evaluation import EmployeeEvaluation
from app.modules.auth.deps import get_current_user, is_planning_director
from app.templates import render
from app.core.exceptions import Forbidden, NotFound
from app.core.audit import log_audit

router = APIRouter(prefix="/planning", tags=["planning"])

PLANNING_DEPT_ID = 4
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads", "planning")


def _require_planning_director(request: Request, current_user: User = Depends(get_current_user)):
    if not is_planning_director(request):
        raise Forbidden("ليس لديك صلاحية الوصول إلى هذه الصفحة")
    return current_user


@router.get("/dashboard")
async def planning_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(_require_planning_director),
):
    emp = getattr(request.state, "employee", None)
    circles = db.execute(
        select(Department).where(Department.parent_id == PLANNING_DEPT_ID).order_by(Department.sort_order)
    ).scalars().all()
    unread_count = db.execute(
        select(Notification).where(Notification.user_id == current_user.id, Notification.is_read == False)
    ).scalar()
    return render("planning/dashboard.html", request=request, user=current_user, emp=emp, circles=circles, unread_count=unread_count or 0, show_nav=True)


@router.get("/profile")
async def planning_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(_require_planning_director),
):
    emp = getattr(request.state, "employee", None)
    role = getattr(request.state, "role", None)
    return render("planning/profile.html", request=request, user=current_user, emp=emp, user_role=role, show_nav=True)


@router.get("/circles")
async def list_circles(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(_require_planning_director),
):
    circles = db.execute(
        select(Department).where(Department.parent_id == PLANNING_DEPT_ID).order_by(Department.sort_order)
    ).scalars().all()
    employees_count = {}
    for c in circles:
        cnt = db.execute(select(Employee).where(Employee.department_id == c.id)).scalars().all()
        employees_count[c.id] = len(cnt)
    return render("planning/circles.html", request=request, circles=circles, employees_count=employees_count, show_nav=True)


@router.get("/circles/{dept_id}")
async def circle_detail(
    dept_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(_require_planning_director),
):
    circle = db.execute(select(Department).where(Department.id == dept_id, Department.parent_id == PLANNING_DEPT_ID)).scalar_one_or_none()
    if not circle:
        raise NotFound("الدائرة غير موجودة")
    employees = db.execute(
        select(Employee).where(Employee.department_id == dept_id).order_by(Employee.id)
    ).scalars().all()
    user_map = {}
    for e in employees:
        u = db.execute(select(User).where(User.id == e.user_id)).scalar_one_or_none()
        if u:
            user_map[e.id] = u
    reports = db.execute(
        select(PlanningReport).where(PlanningReport.circle_id == dept_id).order_by(desc(PlanningReport.id))
    ).scalars().all()
    report_users = {}
    for r in reports:
        u = db.execute(select(User).where(User.id == r.created_by)).scalar_one_or_none()
        if u:
            report_users[r.id] = u
    return render("planning/circle_detail.html", request=request, circle=circle, employees=employees, user_map=user_map, reports=reports, report_users=report_users, show_nav=True)


@router.get("/circles/{dept_id}/employees/{user_id}")
async def circle_employee_detail(
    dept_id: int,
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(_require_planning_director),
):
    circle = db.execute(select(Department).where(Department.id == dept_id)).scalar_one_or_none()
    if not circle:
        raise NotFound("الدائرة غير موجودة")
    emp_user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not emp_user:
        raise NotFound("الموظف غير موجود")
    emp_record = db.execute(select(Employee).where(Employee.user_id == user_id, Employee.department_id == dept_id)).scalar_one_or_none()
    logs = db.execute(
        select(AuditLog).where(AuditLog.user_id == user_id).order_by(desc(AuditLog.created_at)).limit(200)
    ).scalars().all()
    role = db.execute(select(Role).where(Role.id == emp_record.role_id)).scalar_one_or_none() if emp_record else None
    vacation_count = db.execute(
        select(VacationRequest).where(VacationRequest.user_id == user_id)
    ).scalars().all()
    return render("planning/employee_detail.html", request=request, circle=circle, emp_user=emp_user, emp_record=emp_record, logs=logs, role=role, vacation_count=len(vacation_count), show_nav=True)


@router.get("/reports")
async def planning_reports(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(_require_planning_director),
):
    director_reports = db.execute(
        select(PlanningReport).where(PlanningReport.source_type == "director").order_by(desc(PlanningReport.id))
    ).scalars().all()
    directorate_reports = db.execute(
        select(PlanningReport).where(PlanningReport.source_type == "directorate").order_by(desc(PlanningReport.id))
    ).scalars().all()
    external_reports = db.execute(
        select(PlanningReport).where(PlanningReport.source_type == "external").order_by(desc(PlanningReport.id))
    ).scalars().all()
    users_map = {}
    for r in list(director_reports) + list(directorate_reports) + list(external_reports):
        if r.created_by not in users_map:
            u = db.execute(select(User).where(User.id == r.created_by)).scalar_one_or_none()
            users_map[r.created_by] = u.name if u else "?"
    return render("planning/reports.html", request=request, director_reports=director_reports, directorate_reports=directorate_reports, external_reports=external_reports, users_map=users_map, show_nav=True)


@router.get("/reports/create")
async def create_report_form(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(_require_planning_director),
):
    circles = db.execute(
        select(Department).where(Department.parent_id == PLANNING_DEPT_ID).order_by(Department.sort_order)
    ).scalars().all()
    directorates = db.execute(
        select(Department).where(Department.parent_id.is_(None)).order_by(Department.sort_order)
    ).scalars().all()
    return render("planning/report_form.html", request=request, circles=circles, directorates=directorates, show_nav=True)


@router.post("/reports/create")
async def create_report(
    request: Request,
    file: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(_require_planning_director),
):
    form = await request.form()
    title = form.get("title", "")
    description = form.get("description", "")
    source_type = form.get("source_type", "director")
    circle_id = int(form.get("circle_id", 0))
    recipient = form.get("recipient", "")
    cid = circle_id if circle_id else None
    dir_ids = form.getlist("directorate_ids") if hasattr(form, "getlist") else []
    combined_recipient = recipient or ""
    if dir_ids:
        dir_names = []
        for did in dir_ids:
            try:
                d = db.execute(select(Department).where(Department.id == int(did))).scalar_one_or_none()
                if d:
                    dir_names.append(d.name)
            except ValueError:
                pass
        if dir_names:
            combined_recipient = (combined_recipient + " - " if combined_recipient else "") + "، ".join(dir_names)
    report = PlanningReport(
        title=title, description=description, source_type=source_type,
        circle_id=cid, recipient=combined_recipient or None,
        created_by=current_user.id, status="draft",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    if file and file.filename:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ext = os.path.splitext(file.filename)[1]
        fname = f"report_{report.id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}{ext}"
        fpath = os.path.join(UPLOAD_DIR, fname)
        content = await file.read()
        with open(fpath, "wb") as f:
            f.write(content)
        report.file_path = fpath
    PlanningReportStatus(report_id=report.id, status="draft", note="تم إنشاء التقرير", created_by=current_user.id)
    # Notify the planning director about the new report
    if source_type != "director":
        director = db.execute(
            select(User).join(Employee).join(Role).where(
                Employee.department_id == PLANNING_DEPT_ID,
                Role.name == "مدير مديرية",
            )
        ).scalar_one_or_none()
        if director:
            notification = Notification(user_id=director.id, message=f"تقرير جديد: {title}", related_type="planning_report", related_id=report.id)
            db.add(notification)
    db.commit()
    return RedirectResponse(url="/planning/reports", status_code=302)


@router.post("/reports/{report_id}/upload")
async def upload_report_file(
    report_id: int,
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(_require_planning_director),
):
    report = db.execute(select(PlanningReport).where(PlanningReport.id == report_id)).scalar_one_or_none()
    if not report:
        raise NotFound("التقرير غير موجود")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename)[1] if file.filename else ""
    fname = f"report_{report_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}{ext}"
    fpath = os.path.join(UPLOAD_DIR, fname)
    content = await file.read()
    with open(fpath, "wb") as f:
        f.write(content)
    report.file_path = fpath
    db.commit()
    return RedirectResponse(url="/planning/reports", status_code=302)


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(_require_planning_director),
):
    report = db.execute(select(PlanningReport).where(PlanningReport.id == report_id)).scalar_one_or_none()
    if not report or not report.file_path:
        raise NotFound("الملف غير موجود")
    if not os.path.exists(report.file_path):
        raise NotFound("الملف غير موجود على الخادم")
    return FileResponse(report.file_path, filename=os.path.basename(report.file_path))


@router.get("/reports/{report_id}/tracking")
async def report_tracking(
    report_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(_require_planning_director),
):
    report = db.execute(select(PlanningReport).where(PlanningReport.id == report_id)).scalar_one_or_none()
    if not report:
        raise NotFound("التقرير غير موجود")
    statuses = db.execute(
        select(PlanningReportStatus).where(PlanningReportStatus.report_id == report_id).order_by(PlanningReportStatus.id)
    ).scalars().all()
    users_map = {}
    for s in statuses:
        if s.created_by not in users_map:
            u = db.execute(select(User).where(User.id == s.created_by)).scalar_one_or_none()
            users_map[s.created_by] = u.name if u else "?"
    circles = db.execute(
        select(Department).where(Department.parent_id == PLANNING_DEPT_ID).order_by(Department.sort_order)
    ).scalars().all()
    return render("planning/report_tracking.html", request=request, report=report, statuses=statuses, users_map=users_map, circles=circles, show_nav=True)


@router.post("/reports/{report_id}/update-status")
async def update_report_status(
    report_id: int,
    request: Request,
    status: str = Form(...),
    note: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(_require_planning_director),
):
    report = db.execute(select(PlanningReport).where(PlanningReport.id == report_id)).scalar_one_or_none()
    if not report:
        raise NotFound("التقرير غير موجود")
    report.status = status
    tracking = PlanningReportStatus(report_id=report_id, status=status, note=note or None, created_by=current_user.id)
    db.add(tracking)
    db.commit()
    return RedirectResponse(url=f"/planning/reports/{report_id}/tracking", status_code=302)


@router.post("/reports/{report_id}/respond")
async def respond_report(
    report_id: int,
    request: Request,
    response: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(_require_planning_director),
):
    report = db.execute(select(PlanningReport).where(PlanningReport.id == report_id)).scalar_one_or_none()
    if not report:
        raise NotFound("التقرير غير موجود")
    report.response = response
    report.status = "responded"
    report.responded_by = current_user.id
    report.responded_at = datetime.now(timezone.utc)
    tracking = PlanningReportStatus(report_id=report_id, status="responded", note="تم الرد على التقرير", created_by=current_user.id)
    db.add(tracking)
    db.commit()
    return RedirectResponse(url="/planning/reports", status_code=302)


@router.get("/evaluations")
async def list_evaluations(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(_require_planning_director),
):
    planning_employees = db.execute(
        select(Employee).where(
            (Employee.department_id == PLANNING_DEPT_ID) |
            (Employee.department_id.in_(
                select(Department.id).where(Department.parent_id == PLANNING_DEPT_ID)
            ))
        ).order_by(Employee.id)
    ).scalars().all()
    users_map = {}
    dept_map = {}
    for e in planning_employees:
        u = db.execute(select(User).where(User.id == e.user_id)).scalar_one_or_none()
        if u:
            users_map[e.id] = u
        d = db.execute(select(Department).where(Department.id == e.department_id)).scalar_one_or_none()
        if d:
            dept_map[e.id] = d
    evaluation_counts = {}
    for e in planning_employees:
        cnt = db.execute(
            select(EmployeeEvaluation).where(EmployeeEvaluation.employee_id == e.id)
        ).scalars().all()
        evaluation_counts[e.id] = len(cnt)
    return render("planning/evaluations.html", request=request, employees=planning_employees, users_map=users_map, dept_map=dept_map, evaluation_counts=evaluation_counts, show_nav=True)


@router.get("/evaluations/{employee_id}")
async def employee_evaluation_detail(
    employee_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(_require_planning_director),
):
    emp = db.execute(select(Employee).where(Employee.id == employee_id)).scalar_one_or_none()
    if not emp:
        raise NotFound("الموظف غير موجود")
    emp_user = db.execute(select(User).where(User.id == emp.user_id)).scalar_one_or_none()
    dept = db.execute(select(Department).where(Department.id == emp.department_id)).scalar_one_or_none()
    role = db.execute(select(Role).where(Role.id == emp.role_id)).scalar_one_or_none()
    evaluations = db.execute(
        select(EmployeeEvaluation).where(EmployeeEvaluation.employee_id == employee_id).order_by(desc(EmployeeEvaluation.id))
    ).scalars().all()
    evaluator_names = {}
    for ev in evaluations:
        if ev.evaluator_id not in evaluator_names:
            eu = db.execute(select(User).where(User.id == ev.evaluator_id)).scalar_one_or_none()
            evaluator_names[ev.evaluator_id] = eu.name if eu else "?"
    directorates = db.execute(
        select(Department).where(Department.id != PLANNING_DEPT_ID).order_by(Department.parent_id.asc().nulls_first(), Department.sort_order)
    ).scalars().all()
    return render("planning/evaluation_detail.html", request=request, emp=emp, emp_user=emp_user, dept=dept, role=role, evaluations=evaluations, evaluator_names=evaluator_names, directorates=directorates, show_nav=True)


@router.post("/evaluations/{employee_id}")
async def save_evaluation(
    employee_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(_require_planning_director),
):
    emp = db.execute(select(Employee).where(Employee.id == employee_id)).scalar_one_or_none()
    if not emp:
        raise NotFound("الموظف غير موجود")
    form = await request.form()
    title = form.get("title", "")
    content = form.get("content", "")
    rating_raw = form.get("rating")
    rating = int(rating_raw) if rating_raw else None
    ev = EmployeeEvaluation(
        employee_id=employee_id,
        evaluator_id=current_user.id,
        title=title or f"تقييم {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        content=content,
        rating=rating,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    log_audit(db, current_user, "create", "employee_evaluation", ev.id, f"تقييم للموظف {emp.employee_no}")
    return RedirectResponse(url=f"/planning/evaluations/{employee_id}", status_code=302)


@router.post("/evaluations/{evaluation_id}/share")
async def share_evaluation(
    evaluation_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(_require_planning_director),
):
    ev = db.execute(select(EmployeeEvaluation).where(EmployeeEvaluation.id == evaluation_id)).scalar_one_or_none()
    if not ev:
        raise NotFound("التقييم غير موجود")
    form = await request.form()
    target_ids = form.getlist("directorate_ids") if hasattr(form, "getlist") else []
    general_manager = form.get("share_gm") == "on"
    shared_list = []
    if target_ids:
        for did in target_ids:
            try:
                directors = db.execute(
                    select(User).join(Employee).join(Role).where(
                        Employee.department_id == int(did),
                        Role.name == "مدير مديرية",
                    )
                ).scalars().all()
                for d in directors:
                    if d.id not in shared_list:
                        shared_list.append(d.id)
                        notification = Notification(
                            user_id=d.id,
                            message=f"تقييم جديد: {ev.title}",
                            related_type="employee_evaluation",
                            related_id=ev.id,
                        )
                        db.add(notification)
            except ValueError:
                pass
    if general_manager:
        gm_users = db.execute(
            select(User).join(Employee).join(Role).where(Role.name == "مدير عام")
        ).scalars().all()
        for gm in gm_users:
            if gm.id not in shared_list:
                shared_list.append(gm.id)
                notification = Notification(
                    user_id=gm.id,
                    message=f"تقييم جديد: {ev.title}",
                    related_type="employee_evaluation",
                    related_id=ev.id,
                )
                db.add(notification)
    import json
    ev.shared_with = json.dumps(shared_list)
    db.commit()
    log_audit(db, current_user, "share", "employee_evaluation", ev.id, f"مشاركة تقييم مع {len(shared_list)} مستخدم")
    return RedirectResponse(url=f"/planning/evaluations/{ev.employee_id}", status_code=302)
