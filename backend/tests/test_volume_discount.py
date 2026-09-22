"""路线临时体积折扣：开关改变装袋体积上限，重量上限不受影响。

与种子路线“滨江晚线”同构：两站点各 6L / 2kg，路线原上限 12L / 10kg，
折扣比例 0.5 后体积上限 6L —— 原上限可同袋，打折后必须分袋。
"""

from app.models.models import DeliveryRoute
from app.services.pack_engine import StopItem, effective_volume_limit, pack_route

MAX_WEIGHT = 10.0
MAX_VOLUME = 12.0
RATIO = 0.5
TWO_STOPS = [StopItem(1, 1, 2.0, 6.0), StopItem(2, 2, 2.0, 6.0)]


def test_discount_switch_changes_bag_count():
    off = pack_route(
        TWO_STOPS, MAX_WEIGHT, effective_volume_limit(MAX_VOLUME, False, RATIO)
    )
    on = pack_route(
        TWO_STOPS, MAX_WEIGHT, effective_volume_limit(MAX_VOLUME, True, RATIO)
    )
    assert len(off.bags) == 1  # 原上限 12L：两站点同袋
    assert len(on.bags) == 2  # 折扣后 6L：必须分袋
    assert not off.rejects and not on.rejects


def test_discount_off_restores_original_limit():
    assert effective_volume_limit(MAX_VOLUME, False, RATIO) == MAX_VOLUME
    assert effective_volume_limit(MAX_VOLUME, True, RATIO) == 6.0


def test_bag_volume_never_exceeds_discounted_limit():
    result = pack_route(
        TWO_STOPS, MAX_WEIGHT, effective_volume_limit(MAX_VOLUME, True, RATIO)
    )
    for bag in result.bags:
        assert bag.volume_l <= 6.0 + 1e-9


def test_route_weight_limit_not_changed_by_discount():
    route = DeliveryRoute(
        name="测试线",
        max_weight_kg=8.0,
        max_volume_l=12.0,
        volume_discount_enabled=True,
        volume_discount_ratio=0.5,
    )
    assert route.effective_max_volume_l == 6.0
    assert route.effective_max_weight_kg == 8.0  # 重量上限不被折扣改掉
    route.volume_discount_enabled = False
    assert route.effective_max_volume_l == 12.0  # 关闭后恢复原体积上限
    assert route.effective_max_weight_kg == 8.0


def test_seed_route_shape_matches_discount_story():
    # 与 seed 中滨江晚线一致：开关开关键袋数不同
    route = DeliveryRoute(
        name="滨江晚线",
        max_weight_kg=10.0,
        max_volume_l=12.0,
        volume_discount_enabled=True,
        volume_discount_ratio=0.5,
    )
    discounted = pack_route(TWO_STOPS, route.effective_max_weight_kg, route.effective_max_volume_l)
    route.volume_discount_enabled = False
    restored = pack_route(TWO_STOPS, route.effective_max_weight_kg, route.effective_max_volume_l)
    assert len(discounted.bags) == 2
    assert len(restored.bags) == 1
