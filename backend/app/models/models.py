from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DeliveryRoute(Base):
    __tablename__ = "delivery_routes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    max_weight_kg: Mapped[float] = mapped_column(Float, default=8.0)
    max_volume_l: Mapped[float] = mapped_column(Float, default=20.0)
    volume_discount_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    volume_discount_ratio: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    stops: Mapped[list["SubscriberStop"]] = relationship(back_populates="route")

    @property
    def effective_max_volume_l(self) -> float:
        """装袋实际使用的体积上限：开启折扣时为原上限乘折扣比例。"""
        if self.volume_discount_enabled:
            return self.max_volume_l * self.volume_discount_ratio
        return self.max_volume_l


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
    # 本次装袋实际生效的体积限额（开启折扣时为原上限×比例），落库保证袋重页口径一致
    volume_discount_applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    volume_limit_l: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
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
