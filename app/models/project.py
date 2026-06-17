from datetime import datetime, timezone, date
from sqlalchemy import String, Integer, Float, Text, DateTime, Boolean, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    department_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("departments.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="planned")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
