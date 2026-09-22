from datetime import datetime
from pydantic import BaseModel, Field


class RouteOut(BaseModel):
    id: int
    name: str
    max_weight_kg: float
    max_volume_l: float
    volume_discount_enabled: bool
    volume_discount_ratio: float
    effective_max_volume_l: float
    model_config = {"from_attributes": True}


class RouteDiscountUpdate(BaseModel):
    volume_discount_enabled: bool
    volume_discount_ratio: float = Field(gt=0.0, le=1.0)


class StopOut(BaseModel):
    id: int
    route_id: int
    seq: int
    name: str
    weight_kg: float
    volume_l: float
    model_config = {"from_attributes": True}


class BagItemOut(BaseModel):
    stop_id: int
    stop_name: str
    weight_kg: float
    volume_l: float


class BagOut(BaseModel):
    id: int
    route_id: int
    bag_index: int
    weight_kg: float
    volume_l: float
    items: list[BagItemOut] = []
    volume_discount_applied: bool = False
    volume_limit_l: float | None = None
    model_config = {"from_attributes": True}


class RejectOut(BaseModel):
    id: int
    route_id: int
    stop_id: int
    stop_name: str
    reason: str
    created_at: datetime
    model_config = {"from_attributes": True}


class PackRequest(BaseModel):
    route_id: int


class WeightOut(BaseModel):
    bag_id: int
    bag_index: int
    route_id: int
    weight_kg: float
    volume_l: float
    fill_weight_pct: float
    fill_volume_pct: float
