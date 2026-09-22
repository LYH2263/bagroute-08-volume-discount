from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.services.pack_engine import effective_volume_limit


class DeliveryRoute(Base):
    __tablename__ = "delivery_routes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    max_weight_kg: Mapped[float] = mapped_column(Float, default=8.0)
    max_volume_l: Mapped[float] = mapped_column(Float, default=20.0)
    # 临时体积折扣：开关 + 比例落库；关闭后恢复原体积上限
    volume_discount_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    volume_discount_ratio: Mapped[float] = mapped_column(Float, default=1.0)
    stops: Mapped[list["SubscriberStop"]] = relationship(back_populates="route")

    @property
    def effective_max_volume_l(self) -> float:
        """本次装袋体积上限 = 原上限 × 折扣（开关打开时）。"""
        return effective_volume_limit(
            self.max_volume_l, self.volume_discount_enabled, self.volume_discount_ratio
        )

    @property
    def effective_max_weight_kg(self) -> float:
        """重量上限不受体积折扣影响。"""
        return self.max_weight_kg


class SubscriberStop(Base):
    __tablename__ = "subscriber_stops"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("delivery_routes.id"))
    seq: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(80))
    weight_kg: Mapped[float] = mapped_column(Float)
    volume_l: Mapped[float] = mapped_column(Float)
    route: Mapped[DeliveryRoute] = relationship(back_populates="stops")


class PackBag(Base):
    __tablename__ = "pack_bags"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("delivery_routes.id"))
    bag_index: Mapped[int] = mapped_column(Integer)
    weight_kg: Mapped[float] = mapped_column(Float)
    volume_l: Mapped[float] = mapped_column(Float)
    # 本次装袋实际采用的体积上限快照（可能为折扣后上限），保证袋重页分子分母一致
    volume_limit_l: Mapped[float] = mapped_column(Float, default=0.0)
    discount_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    items: Mapped[list["BagItem"]] = relationship(back_populates="bag")


class BagItem(Base):
    __tablename__ = "bag_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bag_id: Mapped[int] = mapped_column(ForeignKey("pack_bags.id"))
    stop_id: Mapped[int] = mapped_column(ForeignKey("subscriber_stops.id"))
    stop_name: Mapped[str] = mapped_column(String(80))
    weight_kg: Mapped[float] = mapped_column(Float)
    volume_l: Mapped[float] = mapped_column(Float)
    bag: Mapped[PackBag] = relationship(back_populates="items")


class RejectRecord(Base):
    __tablename__ = "reject_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("delivery_routes.id"))
    stop_id: Mapped[int] = mapped_column(Integer)
    stop_name: Mapped[str] = mapped_column(String(80))
    reason: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
