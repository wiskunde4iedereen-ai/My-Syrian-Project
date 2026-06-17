from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class PlanningReport(Base):
    __tablename__ = "planning_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    circle_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("departments.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(20), default="director")
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    recipient: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    responded_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class PlanningReportStatus(Base):
    __tablename__ = "planning_report_statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(Integer, ForeignKey("planning_reports.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
