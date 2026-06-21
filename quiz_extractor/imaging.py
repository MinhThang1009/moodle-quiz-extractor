"""Đo độ nét theo vùng block, tìm ranh giới block, refine frame nét nhất lân cận."""

import cv2
import numpy as np

from . import config as cfg
from .geometry import Geom


def block_sharpness(gray, y1: int, y2: int, geo: Geom) -> float:
    """Độ nét (Laplacian variance) riêng vùng block, né cột chứa nút record nổi."""
    region = gray[max(0, y1) : y2, geo.fx0 : geo.fx1]
    return float(cv2.Laplacian(region, cv2.CV_64F).var()) if region.size else 0.0


def trim_trailing_white(crop):
    """Bỏ các hàng gần trắng ở đáy crop (khoảng trắng thừa dưới đáp án câu cuối)."""
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    has_ink = (gray < cfg.INK).any(axis=1)
    rows = np.where(has_ink)[0]
    return crop if len(rows) == 0 else crop[: rows[-1] + 1]


def sharpest_neighbor(
    frames_by_idx: dict, idx: int, y1: int, y2: int, geo: Geom
) -> int:
    """±NEIGHBOR_R frame (dict idx->frame): chọn frame CÙNG nội dung, NÉT NHẤT."""
    base = cv2.cvtColor(frames_by_idx[idx], cv2.COLOR_BGR2GRAY)
    best_idx = idx
    best_sharp = block_sharpness(base, y1, y2, geo)
    for j in range(idx - cfg.NEIGHBOR_R, idx + cfg.NEIGHBOR_R + 1):
        if j == idx or j not in frames_by_idx:
            continue
        gray = cv2.cvtColor(frames_by_idx[j], cv2.COLOR_BGR2GRAY)
        if float(np.mean(cv2.absdiff(gray[y1:y2], base[y1:y2]))) > cfg.STILL_DIFF:
            continue  # đã cuộn -> không cùng nội dung
        sharp = block_sharpness(gray, y1, y2, geo)
        if sharp > best_sharp:
            best_idx, best_sharp = j, sharp
    return best_idx
