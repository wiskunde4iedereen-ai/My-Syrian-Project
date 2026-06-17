import os
import shutil
from uuid import uuid4
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi.responses import RedirectResponse
from fastapi.responses import FileResponse

from app.core.database import get_db
from app.models.document import Document
from app.models.license import License
from app.modules.auth.deps import get_current_user, require_role
from app.models.user import User
from app.templates import render
from app.core.exceptions import NotFound
from app.core.audit import log_audit

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter(prefix="/documents", tags=["documents"],
                   dependencies=[Depends(require_role("admin", "employee"))])

@router.get("")
async def list_documents(request: Request, doc_type: str = "", db: Session = Depends(get_db)):
    query = select(Document)
    if doc_type:
        query = query.where(Document.doc_type == doc_type)
    docs = db.execute(query.order_by(Document.id.desc())).scalars().all()
    return render("documents/list.html", request=request, docs=docs, current_type=doc_type, show_nav=True)

@router.get("/upload")
async def upload_form(request: Request, db: Session = Depends(get_db)):
    licenses = db.execute(select(License)).scalars().all()
    return render("documents/form.html", request=request, licenses=licenses, show_nav=True)

@router.post("/upload")
async def upload(
    license_id: int = Form(...),
    doc_type: str = Form(""),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ext = os.path.splitext(file.filename)[1] if file.filename else ""
    filename = f"{uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)
    doc = Document(license_id=license_id, filename=file.filename or filename, filepath=filepath, doc_type=doc_type)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    log_audit(db, current_user, "CREATE", "Document", doc.id, f"رفع مستند: {file.filename}")
    return RedirectResponse(url="/documents", status_code=302)

@router.get("/{doc_id}/download")
async def download(doc_id: int, db: Session = Depends(get_db)):
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    if not doc:
        raise NotFound("المستند غير موجود")
    return FileResponse(doc.filepath, filename=doc.filename, media_type="application/octet-stream")
