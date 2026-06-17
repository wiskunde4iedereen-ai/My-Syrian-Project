from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    request_type: Mapped[str] = mapped_column(String(50), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    reviewed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("employees.id"), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=lambda: datetime.now(timezone.utc), nullable=True)
