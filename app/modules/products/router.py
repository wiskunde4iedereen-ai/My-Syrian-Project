from fastapi import APIRouter, Depends, Request, Form
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi.responses import RedirectResponse

from app.core.database import get_db
from app.models.product import Product
from app.models.exporter import Exporter
from app.modules.auth.deps import get_current_user, require_role
from app.models.user import User
from app.templates import render
from app.core.exceptions import NotFound
from app.core.audit import log_audit

router = APIRouter(prefix="/products", tags=["products"], dependencies=[Depends(require_role("admin", "employee"))])

@router.get("")
async def list_products(request: Request, q: str = "", db: Session = Depends(get_db)):
    query = select(Product)
    if q:
        query = query.where(Product.name.ilike(f"%{q}%"))
    products = db.execute(query.order_by(Product.id.desc())).scalars().all()
    exporters = {e.id: e.company_name for e in db.execute(select(Exporter)).scalars().all()}
    return render("products/list.html", request=request, products=products, exporters=exporters, q=q, show_nav=True)

@router.get("/create")
async def create_form(request: Request, db: Session = Depends(get_db)):
    exporters = db.execute(select(Exporter)).scalars().all()
    return render("products/form.html", request=request, product=None, exporters=exporters, show_nav=True)

@router.post("/create")
async def create(
    name: str = Form(...),
    category: str = Form(""),
    hs_code: str = Form(""),
    origin: str = Form(""),
    unit: str = Form(""),
    exporter_id: int = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = Product(name=name, category=category, hs_code=hs_code, origin=origin, unit=unit, exporter_id=exporter_id)
    db.add(product)
    db.commit()
    db.refresh(product)
    log_audit(db, current_user, "CREATE", "Product", product.id, f"إنشاء منتج: {name}")
    return RedirectResponse(url="/products", status_code=302)

@router.get("/{product_id}/edit")
async def edit_form(product_id: int, request: Request, db: Session = Depends(get_db)):
    product = db.execute(select(Product).where(Product.id == product_id)).scalar_one_or_none()
    if not product:
        raise NotFound("المنتج غير موجود")
    exporters = db.execute(select(Exporter)).scalars().all()
    return render("products/form.html", request=request, product=product, exporters=exporters, show_nav=True)

@router.post("/{product_id}/edit")
async def edit(
    product_id: int,
    name: str = Form(...),
    category: str = Form(""),
    hs_code: str = Form(""),
    origin: str = Form(""),
    unit: str = Form(""),
    exporter_id: int = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = db.execute(select(Product).where(Product.id == product_id)).scalar_one_or_none()
    if not product:
        raise NotFound("المنتج غير موجود")
    product.name = name
    product.category = category
    product.hs_code = hs_code
    product.origin = origin
    product.unit = unit
    product.exporter_id = exporter_id
    db.commit()
    log_audit(db, current_user, "UPDATE", "Product", product.id, f"تعديل منتج: {name}")
    return RedirectResponse(url="/products", status_code=302)

@router.post("/{product_id}/delete")
async def delete(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = db.execute(select(Product).where(Product.id == product_id)).scalar_one_or_none()
    if not product:
        raise NotFound("المنتج غير موجود")
    name = product.name
    db.delete(product)
    db.commit()
    log_audit(db, current_user, "DELETE", "Product", product_id, f"حذف منتج: {name}")
    return RedirectResponse(url="/products", status_code=302)
