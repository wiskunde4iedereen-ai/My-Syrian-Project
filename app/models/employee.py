from datetime import datetime, timezone, date
from sqlalchemy import String, Integer, Date, Numeric, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    employee_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    department_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("departments.id"), nullable=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(100), default="")
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    salary: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
