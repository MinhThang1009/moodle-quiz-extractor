"""Geom suy ngưỡng px từ (H, W) và co giãn đúng theo độ phân giải."""

from quiz_extractor import config as cfg
from quiz_extractor.geometry import Geom


def test_thresholds_match_fractions():
    geo = Geom(1040, 480)
    assert geo.pair_min == int(cfg.F_PAIR_MIN * 1040)
    assert geo.pair_max == int(cfg.F_PAIR_MAX * 1040)
    assert geo.fx1 == int(cfg.F_FEAT_X1 * 480)


def test_larger_video_scales_up():
    small = Geom(1040, 480)
    big = Geom(2080, 960)
    assert big.pair_min > small.pair_min
    assert big.pair_max > small.pair_max
    assert big.fx1 > small.fx1
