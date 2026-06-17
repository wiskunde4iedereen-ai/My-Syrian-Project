from fastapi import APIRouter, Depends, Request, Form
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi.responses import RedirectResponse

from app.core.database import get_db
from app.models.market import Market
from app.modules.auth.deps import get_current_user, require_role
from app.models.user import User
from app.templates import render
from app.core.exceptions import NotFound
from app.core.audit import log_audit

router = APIRouter(prefix="/markets", tags=["markets"], dependencies=[Depends(require_role("admin", "employee"))])

@router.get("")
async def list_markets(request: Request, q: str = "", db: Session = Depends(get_db)):
    query = select(Market)
    if q:
        query = query.where(Market.country.ilike(f"%{q}%"))
    markets = db.execute(query.order_by(Market.id.desc())).scalars().all()
    return render("markets/list.html", request=request, markets=markets, q=q, show_nav=True)

@router.get("/create")
async def create_form(request: Request):
    return render("markets/form.html", request=request, market=None, show_nav=True)

@router.post("/create")
async def create(
    country: str = Form(...),
    city: str = Form(""),
    requirements: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    market = Market(country=country, city=city, requirements=requirements)
    db.add(market)
    db.commit()
    db.refresh(market)
    log_audit(db, current_user, "CREATE", "Market", market.id, f"إنشاء سوق: {country}")
    return RedirectResponse(url="/markets", status_code=302)

@router.get("/{market_id}/edit")
async def edit_form(market_id: int, request: Request, db: Session = Depends(get_db)):
    market = db.execute(select(Market).where(Market.id == market_id)).scalar_one_or_none()
    if not market:
        raise NotFound("السوق غير موجود")
    return render("markets/form.html", request=request, market=market, show_nav=True)

@router.post("/{market_id}/edit")
async def edit(
    market_id: int,
    country: str = Form(...),
    city: str = Form(""),
    requirements: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    market = db.execute(select(Market).where(Market.id == market_id)).scalar_one_or_none()
    if not market:
        raise NotFound("السوق غير موجود")
    market.country = country
    market.city = city
    market.requirements = requirements
    db.commit()
    log_audit(db, current_user, "UPDATE", "Market", market.id, f"تعديل سوق: {country}")
    return RedirectResponse(url="/markets", status_code=302)

@router.post("/{market_id}/delete")
async def delete(
    market_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    market = db.execute(select(Market).where(Market.id == market_id)).scalar_one_or_none()
    if not market:
        raise NotFound("السوق غير موجود")
    name = market.country
    db.delete(market)
    db.commit()
    log_audit(db, current_user, "DELETE", "Market", market_id, f"حذف سوق: {name}")
    return RedirectResponse(url="/markets", status_code=302)
