from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sender_name: Mapped[str] = mapped_column(String(150), nullable=False)
    sender_contact: Mapped[str] = mapped_column(String(100), default="")
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    department_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("departments.id"), nullable=True)
    assigned_to: Mapped[int | None] = mapped_column(Integer, ForeignKey("employees.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")
    response: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=lambda: datetime.now(timezone.utc), nullable=True)
