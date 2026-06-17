from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, Form
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi.responses import RedirectResponse

from app.core.database import get_db
from app.models.finance import Finance
from app.models.license import License
from app.models.exporter import Exporter
from app.modules.auth.deps import get_current_user, require_role
from app.models.user import User
from app.templates import render
from app.core.exceptions import NotFound
from app.core.audit import log_audit

router = APIRouter(prefix="/finance", tags=["finance"],
                   dependencies=[Depends(require_role("admin", "employee"))])

@router.get("")
async def list_finance(request: Request, status: str = "", db: Session = Depends(get_db)):
    query = select(Finance)
    if status:
        query = query.where(Finance.status == status)
    records = db.execute(query.order_by(Finance.id.desc())).scalars().all()
    exporters = {e.id: e.company_name for e in db.execute(select(Exporter)).scalars().all()}
    return render("finance/list.html", request=request, records=records, exporters=exporters, current_status=status, show_nav=True)

@router.get("/create")
async def create_form(request: Request, db: Session = Depends(get_db)):
    licenses = db.execute(select(License)).scalars().all()
    exporters = db.execute(select(Exporter)).scalars().all()
    return render("finance/form.html", request=request, record=None, licenses=licenses, exporters=exporters, show_nav=True)

@router.post("/create")
async def create(
    license_id: int = Form(...),
    exporter_id: int = Form(...),
    amount: float = Form(...),
    fee_type: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rec = Finance(license_id=license_id, exporter_id=exporter_id, amount=amount, fee_type=fee_type, status="pending")
    db.add(rec)
    db.commit()
    db.refresh(rec)
    log_audit(db, current_user, "CREATE", "Finance", rec.id, f"إنشاء سجل مالي: {amount}")
    return RedirectResponse(url="/finance", status_code=302)

@router.post("/{finance_id}/pay")
async def mark_paid(
    finance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rec = db.execute(select(Finance).where(Finance.id == finance_id)).scalar_one_or_none()
    if not rec:
        raise NotFound("السجل المالي غير موجود")
    rec.status = "paid"
    rec.paid_at = datetime.now(timezone.utc)
    db.commit()
    log_audit(db, current_user, "UPDATE", "Finance", finance_id, "تسديد مبلغ مالي")
    return RedirectResponse(url="/finance", status_code=302)
