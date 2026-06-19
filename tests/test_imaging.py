"""trim_trailing_white / block_sharpness / sharpest_neighbor (ảnh tổng hợp)."""

import numpy as np

from quiz_extractor.geometry import Geom
from quiz_extractor.imaging import (
    block_sharpness,
    sharpest_neighbor,
    trim_trailing_white,
)


def test_trim_trailing_white_removes_bottom_blank():
    crop = np.full((300, 480, 3), 255, np.uint8)  # toàn trắng
    crop[0:200, :, :] = 50  # nội dung 0..199, trắng 200..299
    out = trim_trailing_white(crop)
    assert 199 <= out.shape[0] <= 201  # bỏ phần trắng đáy


def test_trim_trailing_white_all_blank_returns_input():
    crop = np.full((100, 480, 3), 255, np.uint8)
    assert trim_trailing_white(crop).shape[0] == 100


def test_block_sharpness_sharp_gt_blurry():
    geo = Geom(200, 480)
    sharp = np.zeros((200, 480), np.uint8)
    sharp[:, ::2] = 255  # sọc dọc -> tần số cao
    blurry = np.full((200, 480), 128, np.uint8)  # đồng nhất
    assert block_sharpness(sharp, 0, 200, geo) > block_sharpness(blurry, 0, 200, geo)


def test_sharpest_neighbor_identical_returns_self():
    geo = Geom(200, 480)
    base = np.full((200, 480, 3), 128, np.uint8)
    frames = [base.copy() for _ in range(5)]
    assert sharpest_neighbor(frames, 2, 0, 200, geo) == 2


def test_sharpest_neighbor_picks_sharper_same_content():
    geo = Geom(200, 480)
    base = np.full((200, 480, 3), 128, np.uint8)
    frames = [base.copy() for _ in range(5)]
    sharper = base.copy()
    sharper[:, 14:398:2, :] = (
        131  # sọc mờ: khác rất ít (diff < STILL_DIFF) nhưng nét hơn
    )
    frames[3] = sharper
    assert sharpest_neighbor(frames, 2, 0, 200, geo) == 3
