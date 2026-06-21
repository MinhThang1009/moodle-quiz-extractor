"""Đọc video, OCR tìm header "Question N", và cache kết quả OCR ra đĩa.

Cache phụ thuộc (video size, STEP). Lệch -> tự OCR lại.
"""

import logging
import pickle
import re
import sys
from pathlib import Path

import cv2

from . import config as cfg
from .geometry import Geom

logger = logging.getLogger(__name__)

SAVE_EVERY = 40  # lưu cache mỗi N frame đã OCR (cache resume thông minh)


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


def _read_cache(cache_path: Path) -> dict | None:
    if not cache_path.exists():
        return None
    try:
        with open(cache_path, "rb") as fh:
            cached = pickle.load(fh)
        return cached if isinstance(cached, dict) else None
    except (pickle.UnpicklingError, EOFError, OSError):
        return None


def _matches(cached: dict, geo: Geom, step: int) -> bool:
    return (
        cached.get("h") == geo.H
        and cached.get("w") == geo.W
        and cached.get("step") == step
    )


def _is_complete(cached: dict) -> bool:
    # Cache cũ (không có khóa "next") coi như đã hoàn tất.
    return bool(cached.get("complete", "next" not in cached))


def _save_cache(cache_path, geo, step, data, next_idx, complete) -> None:
    """Ghi cache nguyên tử (tmp + replace) để Ctrl+C giữa chừng không làm hỏng file."""
    payload = {
        "h": geo.H,
        "w": geo.W,
        "step": step,
        "data": data,
        "next": next_idx,
        "complete": complete,
    }
    tmp = cache_path.with_suffix(".tmp")
    with open(tmp, "wb") as fh:
        pickle.dump(payload, fh)
    tmp.replace(cache_path)


def _progress(done: int, total: int, idx: int, headers: list) -> None:
    """In tiến độ OCR dạng stream (1 dòng cập nhật tại chỗ)."""
    nums = ",".join(str(n) for n, _ in headers) if headers else "-"
    pct = 100.0 * done / total if total else 100.0
    sys.stdout.write(
        f"\rOCR {done:4d}/{total} ({pct:5.1f}%) frame {idx:5d}  câu[{nums}]      "
    )
    sys.stdout.flush()


def build_cache(frames: list, geo: Geom, cache_path: Path, step: int) -> list:
    """OCR mỗi `step` frame, giữ frame quiz. Stream tiến độ + cache resume."""
    import easyocr  # import muộn: nặng (torch)

    cache_path.parent.mkdir(parents=True, exist_ok=True)  # tạo folder ngay
    total = len(range(0, len(frames), step))

    # Resume nếu có cache DỞ khớp (size, step) -> tiếp tục từ frame còn lại.
    start, data = 0, []
    cached = _read_cache(cache_path)
    if cached and _matches(cached, geo, step) and not _is_complete(cached):
        start = int(cached.get("next", 0))
        data = list(cached.get("data", []))
        logger.info("Tiếp tục OCR từ frame %d (đã có %d câu).", start, len(data))

    reader = easyocr.Reader(list(cfg.OCR_LANGS), gpu=False, verbose=False)
    done = start // step  # số sample đã xong trước đó
    for k, idx in enumerate(range(start, len(frames), step), 1):
        detections = reader.readtext(frames[idx], detail=1, paragraph=False)
        headers = parse_headers(detections, geo)
        if _is_quiz_frame(detections, headers):
            data.append((idx, headers))
        done += 1
        _progress(done, total, idx, headers)
        if k % SAVE_EVERY == 0:
            _save_cache(cache_path, geo, step, data, idx + step, False)

    _save_cache(cache_path, geo, step, data, len(frames), True)
    sys.stdout.write("\n")
    sys.stdout.flush()
    logger.info("Đã cache %d frame quiz -> %s", len(data), cache_path)
    return data


def load_or_build_cache(frames: list, geo: Geom, cache_path: Path, step: int) -> list:
    """Dùng cache nếu khớp & hoàn tất; cache dở -> OCR tiếp; lệch -> OCR lại."""
    cached = _read_cache(cache_path)
    if cached and _matches(cached, geo, step):
        if _is_complete(cached):
            logger.info("Dùng cache %s.", cache_path)
            return cached["data"]
        logger.info("Cache còn dở -> tiếp tục OCR.")
    elif cached:
        logger.info("Cache lệch (độ phân giải/STEP) -> OCR lại.")
    return build_cache(frames, geo, cache_path, step)
