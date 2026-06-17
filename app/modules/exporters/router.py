from fastapi import APIRouter, Depends, Request, Form
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi.responses import RedirectResponse

from app.core.database import get_db
from app.models.exporter import Exporter
from app.models.product import Product
from app.models.license import License
from app.models.finance import Finance
from app.models.document import Document
from app.models.market import Market
from app.modules.auth.deps import get_current_user, require_role
from app.models.user import User
from app.templates import render
from app.core.exceptions import NotFound, Conflict
from app.core.audit import log_audit

router = APIRouter(prefix="/exporters", tags=["exporters"], dependencies=[Depends(require_role("admin", "employee"))])

@router.get("")
async def list_exporters(request: Request, q: str = "", db: Session = Depends(get_db)):
    query = select(Exporter)
    if q:
        query = query.where(Exporter.company_name.ilike(f"%{q}%"))
    exporters = db.execute(query.order_by(Exporter.id.desc())).scalars().all()
    return render("exporters/list.html", request=request, exporters=exporters, q=q, show_nav=True)

@router.get("/create")
async def create_form(request: Request):
    return render("exporters/form.html", request=request, exporter=None, show_nav=True)

@router.post("/create")
async def create(
    request: Request,
    company_name: str = Form(...),
    owner_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    commercial_registry: str = Form(""),
    address: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.execute(select(Exporter).where(Exporter.email == email)).scalar_one_or_none()
    if existing:
        raise Conflict("البريد الإلكتروني مستخدم بالفعل")
    exporter = Exporter(company_name=company_name, owner_name=owner_name, email=email, phone=phone, commercial_registry=commercial_registry, address=address)
    db.add(exporter)
    db.commit()
    db.refresh(exporter)
    log_audit(db, current_user, "CREATE", "Exporter", exporter.id, f"إنشاء مصدر: {company_name}")
    return RedirectResponse(url="/exporters", status_code=302)

@router.get("/{exporter_id}/edit")
async def edit_form(exporter_id: int, request: Request, db: Session = Depends(get_db)):
    exporter = db.execute(select(Exporter).where(Exporter.id == exporter_id)).scalar_one_or_none()
    if not exporter:
        raise NotFound("المصدر غير موجود")
    return render("exporters/form.html", request=request, exporter=exporter, show_nav=True)

@router.post("/{exporter_id}/edit")
async def edit(
    exporter_id: int,
    company_name: str = Form(...),
    owner_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    commercial_registry: str = Form(""),
    address: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    exporter = db.execute(select(Exporter).where(Exporter.id == exporter_id)).scalar_one_or_none()
    if not exporter:
        raise NotFound("المصدر غير موجود")
    dup = db.execute(select(Exporter).where(Exporter.email == email, Exporter.id != exporter_id)).scalar_one_or_none()
    if dup:
        raise Conflict("البريد الإلكتروني مستخدم بالفعل")
    exporter.company_name = company_name
    exporter.owner_name = owner_name
    exporter.email = email
    exporter.phone = phone
    exporter.commercial_registry = commercial_registry
    exporter.address = address
    db.commit()
    log_audit(db, current_user, "UPDATE", "Exporter", exporter.id, f"تعديل مصدر: {company_name}")
    return RedirectResponse(url="/exporters", status_code=302)

@router.get("/{exporter_id}")
async def detail(exporter_id: int, request: Request, db: Session = Depends(get_db)):
    exporter = db.execute(select(Exporter).where(Exporter.id == exporter_id)).scalar_one_or_none()
    if not exporter:
        raise NotFound("المصدر غير موجود")
    products = db.execute(select(Product).where(Product.exporter_id == exporter_id).order_by(Product.id)).scalars().all()
    licenses = db.execute(select(License).where(License.exporter_id == exporter_id).order_by(License.id.desc())).scalars().all()
    finance_records = db.execute(select(Finance).where(Finance.exporter_id == exporter_id).order_by(Finance.id.desc())).scalars().all()
    doc_license_ids = [l.id for l in licenses]
    documents = []
    if doc_license_ids:
        documents = db.execute(select(Document).where(Document.license_id.in_(doc_license_ids)).order_by(Document.id.desc())).scalars().all()
    product_names = {p.id: p.name for p in db.execute(select(Product)).scalars().all()}
    market_names = {m.id: m.country for m in db.execute(select(Market)).scalars().all()}
    return render("exporters/detail.html", request=request, exporter=exporter, products=products,
                  licenses=licenses, finance_records=finance_records, documents=documents,
                  product_names=product_names, market_names=market_names, show_nav=True)

@router.post("/{exporter_id}/delete")
async def delete(
    exporter_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    exporter = db.execute(select(Exporter).where(Exporter.id == exporter_id)).scalar_one_or_none()
    if not exporter:
        raise NotFound("المصدر غير موجود")
    name = exporter.company_name
    db.delete(exporter)
    db.commit()
    log_audit(db, current_user, "DELETE", "Exporter", exporter_id, f"حذف مصدر: {name}")
    return RedirectResponse(url="/exporters", status_code=302)
