from typing import Any

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

JsonValue = dict[str, Any] | list[Any]


class TableInfo(Base):
    __tablename__ = "table_info"
    __table_args__ = {"schema": "meta"}

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(128))
    role: Mapped[str | None] = mapped_column(String(32))
    description: Mapped[str | None] = mapped_column(Text)


class ColumnInfo(Base):
    __tablename__ = "column_info"
    __table_args__ = {"schema": "meta"}

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(128))
    type: Mapped[str | None] = mapped_column(String(64))
    role: Mapped[str | None] = mapped_column(String(32))
    examples: Mapped[JsonValue | None] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(Text)
    alias: Mapped[JsonValue | None] = mapped_column(JSON)
    table_id: Mapped[str | None] = mapped_column(String(64))


class MetricInfo(Base):
    __tablename__ = "metric_info"
    __table_args__ = {"schema": "meta"}

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text)
    relevant_columns: Mapped[JsonValue | None] = mapped_column(JSON)
    alias: Mapped[JsonValue | None] = mapped_column(JSON)


class ColumnMetric(Base):
    __tablename__ = "column_metric"
    __table_args__ = {"schema": "meta"}

    column_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    metric_id: Mapped[str] = mapped_column(String(64), primary_key=True)
