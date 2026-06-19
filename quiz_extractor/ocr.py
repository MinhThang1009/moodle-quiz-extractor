"""Đọc video, OCR tìm header "Question N", và cache kết quả OCR ra đĩa.

Cache phụ thuộc (video size, STEP). Lệch -> tự OCR lại.
"""

import logging
import pickle
import re
from pathlib import Path

import cv2

from . import config as cfg
from .geometry import Geom

logger = logging.getLogger(__name__)


def load_frames(video_path: Path) -> list:
    """Đọc toàn bộ frame của video vào RAM (BGR)."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise SystemExit(f"Không mở được video: {video_path}")
    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(frame)
    cap.release()
    if not frames:
        raise SystemExit(f"Video rỗng: {video_path}")
    return frames


def parse_headers(detections, geo: Geom) -> list:
    """OCR detail=1 -> list (qnum, header_y) sort theo y.

    Gộp trường hợp OCR tách "Question" và số thành 2 box cạnh nhau, và suy số cho
    header "Question" mà OCR trượt mất số (vd số "1" đơn lẻ mảnh khó đọc).
    """
    items, qword, nums = [], [], []
    for bbox, txt, _ in detections:
        y, x = bbox[0][1], bbox[0][0]
        token = txt.strip().lower()
        matched = cfg.QUESTION_RE.fullmatch(token)
        if matched:
            items.append((int(matched.group(1)), y))
        elif token == "question":
            qword.append((y, x))
        elif re.fullmatch(r"\d{1,3}", token):
            nums.append((y, x, int(token)))
    orphans = []  # "Question" không ghép được số
    for qy, qx in qword:
        near = [
            (abs(ny - qy), value)
            for ny, nx, value in nums
            if abs(ny - qy) <= geo.head_ytol and 0 < nx - qx < geo.head_xdist
        ]
        if near:
            items.append((min(near)[1], qy))
        else:
            orphans.append(qy)
    # Suy số orphan từ header numbered gần nhất cách ~1 block (trên: n-1, dưới: n+1).
    numbered = list(items)
    for oy in orphans:
        if not numbered:
            continue
        n_near, y_near = min(numbered, key=lambda t: abs(t[1] - oy))
        gap = abs(y_near - oy)
        if geo.pair_min * 0.6 <= gap <= geo.pair_max:
            inferred = n_near - 1 if oy < y_near else n_near + 1
            if inferred >= 1:
                items.append((inferred, oy))
    earliest: dict[int, float] = {}
    for number, y in items:
        if number not in earliest or y < earliest[number]:
            earliest[number] = y
    return sorted(((n, int(y)) for n, y in earliest.items()), key=lambda t: t[1])


def _is_quiz_frame(detections, headers) -> bool:
    """Frame thuộc trang quiz nếu có header HOẶC chứa marker quiz (loại overlay)."""
    if headers:
        return True
    text = " ".join(t for _, t, _ in detections).lower()
    return any(marker in text for marker in cfg.QUIZ_MARKERS)


def build_cache(frames: list, geo: Geom, cache_path: Path, step: int) -> list:
    """OCR mỗi `step` frame, giữ lại frame quiz, lưu (idx, headers) ra cache."""
    import easyocr  # import muộn: nặng (torch)

    reader = easyocr.Reader(list(cfg.OCR_LANGS), gpu=False, verbose=False)
    data, done = [], 0
    for idx in range(0, len(frames), step):
        detections = reader.readtext(frames[idx], detail=1, paragraph=False)
        headers = parse_headers(detections, geo)
        if not _is_quiz_frame(detections, headers):
            continue
        data.append((idx, headers))
        done += 1
        if done % 40 == 0:
            logger.info("...OCR %d frame quiz", done)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"h": geo.H, "w": geo.W, "step": step, "data": data}
    with open(cache_path, "wb") as fh:
        pickle.dump(payload, fh)
    logger.info("Đã cache %d frame quiz -> %s", len(data), cache_path)
    return data


def load_or_build_cache(frames: list, geo: Geom, cache_path: Path, step: int) -> list:
    """Dùng cache nếu khớp (size, step); ngược lại OCR lại."""
    if cache_path.exists():
        with open(cache_path, "rb") as fh:
            cached = pickle.load(fh)
        if (
            isinstance(cached, dict)
            and cached.get("h") == geo.H
            and cached.get("w") == geo.W
            and cached.get("step") == step
        ):
            logger.info("Dùng cache %s.", cache_path)
            return cached["data"]
        logger.info("Cache lệch (độ phân giải/STEP) -> OCR lại.")
    return build_cache(frames, geo, cache_path, step)
