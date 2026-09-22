from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import BagItem, DeliveryRoute, PackBag, RejectRecord, SubscriberStop
from app.schemas.schemas import (
    BagItemOut,
    BagOut,
    PackRequest,
    RejectOut,
    RouteOut,
    RouteUpdate,
    StopOut,
    WeightOut,
)
from app.services.pack_engine import StopItem, pack_route

api_router = APIRouter()


@api_router.get("/health")
def health():
    return {"status": "ok"}


@api_router.get("/routes", response_model=list[RouteOut])
def routes(db: Session = Depends(get_db)):
    return db.scalars(select(DeliveryRoute).order_by(DeliveryRoute.id)).all()


@api_router.patch("/routes/{route_id}", response_model=RouteOut)
def update_route(route_id: int, body: RouteUpdate, db: Session = Depends(get_db)):
    route = db.get(DeliveryRoute, route_id)
    if not route:
        raise HTTPException(404, "路线不存在")
    route.volume_discount_enabled = body.volume_discount_enabled
    route.volume_discount_ratio = body.volume_discount_ratio
    db.commit()
    db.refresh(route)
    return route


@api_router.get("/stops", response_model=list[StopOut])
def stops(route_id: int | None = None, db: Session = Depends(get_db)):
    q = select(SubscriberStop).order_by(SubscriberStop.route_id, SubscriberStop.seq)
    if route_id is not None:
        q = q.where(SubscriberStop.route_id == route_id)
    return db.scalars(q).all()


@api_router.post("/pack", response_model=list[BagOut])
def pack(body: PackRequest, db: Session = Depends(get_db)):
    route = db.get(DeliveryRoute, body.route_id)
    if not route:
        raise HTTPException(404, "路线不存在")
    # clear previous pack for route
    old_bags = db.scalars(select(PackBag).where(PackBag.route_id == route.id)).all()
    for b in old_bags:
        for it in list(b.items):
            db.delete(it)
        db.delete(b)
    old_rej = db.scalars(select(RejectRecord).where(RejectRecord.route_id == route.id)).all()
    for r in old_rej:
        db.delete(r)
    db.flush()

    stops = db.scalars(
        select(SubscriberStop).where(SubscriberStop.route_id == route.id).order_by(SubscriberStop.seq)
    ).all()
    items = [
        StopItem(s.id, s.seq, s.weight_kg, s.volume_l, s.name) for s in stops
    ]
    # 体积上限按路线折扣设置折算；重量上限不打折
    max_weight = route.effective_max_weight_kg
    max_volume = route.effective_max_volume_l
    result = pack_route(items, max_weight, max_volume)
    out_bags: list[PackBag] = []
    for bag in result.bags:
        row = PackBag(
            route_id=route.id,
            bag_index=bag.bag_index,
            weight_kg=round(bag.weight_kg, 3),
            volume_l=round(bag.volume_l, 3),
            volume_limit_l=round(max_volume, 3),
            discount_applied=bool(route.volume_discount_enabled),
        )
        db.add(row)
        db.flush()
        for it in bag.items:
            db.add(
                BagItem(
                    bag_id=row.id,
                    stop_id=it.stop_id,
                    stop_name=it.label,
                    weight_kg=it.weight_kg,
                    volume_l=it.volume_l,
                )
            )
        out_bags.append(row)
    for stop, reason in result.rejects:
        db.add(
            RejectRecord(
                route_id=route.id,
                stop_id=stop.stop_id,
                stop_name=stop.label,
                reason=reason,
            )
        )
    db.commit()
    return [
        BagOut(
            id=b.id,
            route_id=b.route_id,
            bag_index=b.bag_index,
            weight_kg=b.weight_kg,
            volume_l=b.volume_l,
            volume_limit_l=b.volume_limit_l,
            discount_applied=b.discount_applied,
            items=[
                BagItemOut(
                    stop_id=i.stop_id,
                    stop_name=i.stop_name,
                    weight_kg=i.weight_kg,
                    volume_l=i.volume_l,
                )
                for i in db.scalars(select(BagItem).where(BagItem.bag_id == b.id)).all()
            ],
        )
        for b in out_bags
    ]


@api_router.get("/bags", response_model=list[BagOut])
def bags(db: Session = Depends(get_db)):
    rows = db.scalars(select(PackBag).order_by(PackBag.route_id, PackBag.bag_index)).all()
    out = []
    for b in rows:
        items = db.scalars(select(BagItem).where(BagItem.bag_id == b.id)).all()
        out.append(
            BagOut(
                id=b.id,
                route_id=b.route_id,
                bag_index=b.bag_index,
                weight_kg=b.weight_kg,
                volume_l=b.volume_l,
                volume_limit_l=b.volume_limit_l,
                discount_applied=b.discount_applied,
                items=[
                    BagItemOut(
                        stop_id=i.stop_id,
                        stop_name=i.stop_name,
                        weight_kg=i.weight_kg,
                        volume_l=i.volume_l,
                    )
                    for i in items
                ],
            )
        )
    return out


@api_router.get("/rejects", response_model=list[RejectOut])
def rejects(db: Session = Depends(get_db)):
    return db.scalars(select(RejectRecord).order_by(RejectRecord.id.desc())).all()


@api_router.get("/weights", response_model=list[WeightOut])
def weights(db: Session = Depends(get_db)):
    bags = db.scalars(select(PackBag).order_by(PackBag.id)).all()
    out = []
    for b in bags:
        route = db.get(DeliveryRoute, b.route_id)
        assert route
        # 体积填充按本次装袋落库的（可能折扣后的）上限计算，避免分子分母对不上
        volume_limit = b.volume_limit_l or route.effective_max_volume_l
        out.append(
            WeightOut(
                bag_id=b.id,
                bag_index=b.bag_index,
                route_id=b.route_id,
                weight_kg=b.weight_kg,
                volume_l=b.volume_l,
                volume_limit_l=volume_limit,
                discount_applied=bool(b.discount_applied),
                fill_weight_pct=round(100 * b.weight_kg / route.effective_max_weight_kg, 1),
                fill_volume_pct=round(100 * b.volume_l / volume_limit, 1),
            )
        )
    return out
