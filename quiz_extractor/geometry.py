"""Suy ra các ngưỡng pixel từ kích thước (H, W) của video hiện tại."""

from . import config as cfg


class Geom:
    """Ngưỡng px = fraction (config) * kích thước video -> tự co giãn theo res."""

    def __init__(self, height: int, width: int):
        self.H, self.W = height, width
        self.pair_min = int(cfg.F_PAIR_MIN * height)
        self.pair_max = int(cfg.F_PAIR_MAX * height)
        self.tail_room = int(cfg.F_TAIL_ROOM * height)
        self.head_ytol = int(cfg.F_HEAD_YTOL * height)
        self.head_xdist = int(cfg.F_HEAD_XDIST * width)
        self.fx0 = int(cfg.F_FEAT_X0 * width)
        self.fx1 = int(cfg.F_FEAT_X1 * width)
        self.top_margin = int(cfg.F_TOP_MARGIN * height)
