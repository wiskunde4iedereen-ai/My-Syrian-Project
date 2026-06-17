from sqlalchemy import String, Boolean, Integer, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="employee")
    role_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("roles.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    salary: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
