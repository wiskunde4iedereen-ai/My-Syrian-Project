from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, Form
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi.responses import RedirectResponse

from app.core.database import get_db
from app.models.license import License
from app.models.product import Product
from app.models.exporter import Exporter
from app.models.market import Market
from app.models.document import Document
from app.modules.auth.deps import get_current_user, require_role
from app.models.user import User
from app.templates import render
from app.core.exceptions import NotFound
from app.core.audit import log_audit

router = APIRouter(prefix="/licenses", tags=["licenses"],
                   dependencies=[Depends(require_role("admin", "employee"))])

@router.get("")
async def list_licenses(request: Request, status: str = "", db: Session = Depends(get_db)):
    query = select(License)
    if status:
        query = query.where(License.status == status)
    licenses = db.execute(query.order_by(License.id.desc())).scalars().all()
    products = {p.id: p.name for p in db.execute(select(Product)).scalars().all()}
    exporters = {e.id: e.company_name for e in db.execute(select(Exporter)).scalars().all()}
    markets = {m.id: m.country for m in db.execute(select(Market)).scalars().all()}
    return render("licenses/list.html", request=request, licenses=licenses,
                  products=products, exporters=exporters, markets=markets,
                  current_status=status, show_nav=True)

@router.get("/{license_id}")
async def license_detail(
    license_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    lic = db.execute(select(License).where(License.id == license_id)).scalar_one_or_none()
    if not lic:
        raise NotFound("الترخيص غير موجود")
    product = db.execute(select(Product).where(Product.id == lic.product_id)).scalar_one_or_none()
    exporter = db.execute(select(Exporter).where(Exporter.id == lic.exporter_id)).scalar_one_or_none()
    market = db.execute(select(Market).where(Market.id == lic.market_id)).scalar_one_or_none()
    docs = db.execute(
        select(Document).where(Document.license_id == license_id)
    ).scalars().all()
    return render("licenses/detail.html", request=request, lic=lic,
                  product=product, exporter=exporter, market=market,
                  docs=docs, show_nav=True)

@router.get("/create")
async def create_form(request: Request, db: Session = Depends(get_db)):
    products = db.execute(select(Product)).scalars().all()
    exporters = db.execute(select(Exporter)).scalars().all()
    markets = db.execute(select(Market)).scalars().all()
    return render("licenses/form.html", request=request, license=None,
                  products=products, exporters=exporters, markets=markets, show_nav=True)

@router.post("/create")
async def create(
    product_id: int = Form(...),
    exporter_id: int = Form(...),
    market_id: int = Form(...),
    notes: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lic = License(product_id=product_id, exporter_id=exporter_id, market_id=market_id, notes=notes, status="pending")
    db.add(lic)
    db.commit()
    db.refresh(lic)
    log_audit(db, current_user, "CREATE", "License", lic.id, "إنشاء ترخيص جديد")
    return RedirectResponse(url="/licenses", status_code=302)

@router.post("/{license_id}/approve")
async def approve(
    license_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lic = db.execute(select(License).where(License.id == license_id)).scalar_one_or_none()
    if not lic:
        raise NotFound("الترخيص غير موجود")
    lic.status = "approved"
    lic.approved_at = datetime.now(timezone.utc)
    db.commit()
    log_audit(db, current_user, "UPDATE", "License", license_id, "اعتماد ترخيص")
    return RedirectResponse(url=f"/licenses/{license_id}", status_code=302)

@router.post("/{license_id}/reject")
async def reject(
    license_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lic = db.execute(select(License).where(License.id == license_id)).scalar_one_or_none()
    if not lic:
        raise NotFound("الترخيص غير موجود")
    lic.status = "rejected"
    db.commit()
    log_audit(db, current_user, "UPDATE", "License", license_id, "رفض ترخيص")
    return RedirectResponse(url=f"/licenses/{license_id}", status_code=302)
