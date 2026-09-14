from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DimRegion(Base):
    __tablename__ = "dim_region"
    __table_args__ = {"schema": "dw"}

    region_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    province: Mapped[str | None] = mapped_column(String(50))
    region_name: Mapped[str | None] = mapped_column(String(50))
    country: Mapped[str | None] = mapped_column(String(50))


class DimCustomer(Base):
    __tablename__ = "dim_customer"
    __table_args__ = {"schema": "dw"}

    customer_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    customer_name: Mapped[str | None] = mapped_column(String(50))
    gender: Mapped[str | None] = mapped_column(String(10))
    member_level: Mapped[str | None] = mapped_column(String(20))


class DimProduct(Base):
    __tablename__ = "dim_product"
    __table_args__ = {"schema": "dw"}

    product_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    product_name: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(50))
    brand: Mapped[str | None] = mapped_column(String(50))


class DimDate(Base):
    __tablename__ = "dim_date"
    __table_args__ = {"schema": "dw"}

    date_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    year: Mapped[int | None] = mapped_column(Integer)
    quarter: Mapped[str | None] = mapped_column(String(2))
    month: Mapped[int | None] = mapped_column(Integer)
    day: Mapped[int | None] = mapped_column(Integer)


class FactOrder(Base):
    __tablename__ = "fact_order"
    __table_args__ = {"schema": "dw"}

    order_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    customer_id: Mapped[str | None] = mapped_column(String(20))
    product_id: Mapped[str | None] = mapped_column(String(20))
    date_id: Mapped[int | None] = mapped_column(Integer)
    region_id: Mapped[str | None] = mapped_column(String(20))
    order_quantity: Mapped[int | None] = mapped_column(Integer)
    order_amount: Mapped[float | None] = mapped_column(Float)
