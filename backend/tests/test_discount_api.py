import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.models import DeliveryRoute, SubscriberStop

# 不使用 with 进入 TestClient，避免触发真实 Postgres 的 lifespan
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base.metadata.create_all(engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_tables():
    db = TestingSessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.close()
    yield


def _make_route(enabled: bool = False, ratio: float = 0.7) -> int:
    """两站体积各 4L（合计 8L）、重量各 3kg（合计 6kg）。

    原上限 10L/8kg 下可同袋；0.7 折扣后体积上限 7L 必须分袋，
    而重量 6kg 始终低于 8kg 上限，用于证明分袋只因体积折扣。
    """
    db = TestingSessionLocal()
    route = DeliveryRoute(
        name="折扣测试线",
        max_weight_kg=8.0,
        max_volume_l=10.0,
        volume_discount_enabled=enabled,
        volume_discount_ratio=ratio,
    )
    db.add(route)
    db.flush()
    db.add_all(
        [
            SubscriberStop(route_id=route.id, seq=1, name="折扣点甲", weight_kg=3.0, volume_l=4.0),
            SubscriberStop(route_id=route.id, seq=2, name="折扣点乙", weight_kg=3.0, volume_l=4.0),
        ]
    )
    db.commit()
    rid = route.id
    db.close()
    return rid


def _pack(rid: int):
    res = client.post("/api/pack", json={"route_id": rid})
    assert res.status_code == 200, res.text
    return res.json()


def _bag_volume_total(bag) -> float:
    return sum(i["volume_l"] for i in bag["items"])


def test_discount_toggle_changes_bag_count():
    rid = _make_route(enabled=False)

    # 关闭折扣：10L 上限，合计 8L 同袋
    bags_off = _pack(rid)
    assert len(bags_off) == 1
    assert bags_off[0]["volume_discount_applied"] is False
    assert bags_off[0]["volume_limit_l"] == 10.0

    # 打开折扣：上限变 7L，必须分两袋
    res = client.patch(f"/api/routes/{rid}/discount", json={"volume_discount_enabled": True, "volume_discount_ratio": 0.7})
    assert res.status_code == 200, res.text
    assert res.json()["effective_max_volume_l"] == pytest.approx(7.0)

    bags_on = _pack(rid)
    assert len(bags_on) == 2
    for bag in bags_on:
        assert bag["volume_discount_applied"] is True
        assert bag["volume_limit_l"] == pytest.approx(7.0)
        # 袋明细体积合计不得超过打折后上限
        assert _bag_volume_total(bag) <= 7.0 + 1e-9
        assert bag["volume_l"] == pytest.approx(_bag_volume_total(bag))

    # 关闭折扣后恢复原上限，重新同袋
    res = client.patch(f"/api/routes/{rid}/discount", json={"volume_discount_enabled": False, "volume_discount_ratio": 0.7})
    assert res.status_code == 200
    bags_again = _pack(rid)
    assert len(bags_again) == 1
    assert bags_again[0]["volume_discount_applied"] is False
    assert bags_again[0]["volume_limit_l"] == 10.0


def test_discount_persists_across_requests():
    rid = _make_route(enabled=False)
    res = client.patch(f"/api/routes/{rid}/discount", json={"volume_discount_enabled": True, "volume_discount_ratio": 0.7})
    assert res.status_code == 200

    # 再次读取（新会话），开关与比例仍落库有效，重量上限保持不变
    rows = client.get("/api/routes").json()
    route = next(r for r in rows if r["id"] == rid)
    assert route["volume_discount_enabled"] is True
    assert route["volume_discount_ratio"] == pytest.approx(0.7)
    assert route["effective_max_volume_l"] == pytest.approx(7.0)
    assert route["max_weight_kg"] == 8.0
    assert route["max_volume_l"] == 10.0


def test_weight_cap_unaffected_by_discount():
    rid = _make_route(enabled=True, ratio=0.7)
    bags = _pack(rid)
    assert len(bags) == 2  # 体积分袋

    # 两站合计 6kg 本可同袋（<8kg），分袋完全由体积导致
    weights = client.get("/api/weights").json()
    assert len(weights) == 2
    for w in weights:
        # 重量填充分母仍是原重量上限 8kg：3/8 = 37.5%
        assert w["fill_weight_pct"] == pytest.approx(37.5)
        # 体积填充按打折后上限 7L 计算：4/7 ≈ 57.1%，分子分母口径一致
        assert w["fill_volume_pct"] == pytest.approx(57.1, abs=0.05)


def test_discount_ratio_validation():
    rid = _make_route()
    bad = client.patch(f"/api/routes/{rid}/discount", json={"volume_discount_enabled": True, "volume_discount_ratio": 1.2})
    assert bad.status_code == 422
    zero = client.patch(f"/api/routes/{rid}/discount", json={"volume_discount_enabled": True, "volume_discount_ratio": 0.0})
    assert zero.status_code == 422
    missing = client.patch("/api/routes/999/discount", json={"volume_discount_enabled": True, "volume_discount_ratio": 0.7})
    assert missing.status_code == 404
