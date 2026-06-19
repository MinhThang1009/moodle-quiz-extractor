"""Orchestration: từ video -> 1 ảnh/câu (không sót, không lặp).

Quy trình:
  1. Đọc frame, OCR (hoặc dùng cache) tìm header "Question N".
  2. Gom ứng viên block theo số câu.
  3. Mỗi câu: chọn frame nét nhất tại vùng block (refine lân cận), cắt block theo
     ranh giới khoảng trắng (tự bỏ lưới nav / header câu kế).
"""

import logging
from collections import defaultdict
from pathlib import Path

import cv2

from . import config as cfg
from .geometry import Geom
from .imaging import block_sharpness, sharpest_neighbor, trim_trailing_white
from .ocr import load_frames, load_or_build_cache

logger = logging.getLogger(__name__)


def _collect_candidates(data: list, height: int) -> dict:
    """data [(idx, headers)] -> {qnum: [(idx, y1, y2, has_next)]}."""
    candidates = defaultdict(list)
    for idx, headers in data:
        for i, (number, y1) in enumerate(headers):
            if i + 1 < len(headers):
                y2, has_next = headers[i + 1][1], True
            else:
                y2, has_next = height, False
            candidates[number].append((idx, y1, y2, has_next))
    return candidates


def _pick_source(number_cands: list, frames: list, geo: Geom):
    """Chọn (idx, y1, hard_limit) tốt nhất cho 1 câu.

    Ưu tiên block có header kế (biên rõ) + nét nhất; nếu không có thì lấy frame header
    cao nhất đủ chỗ (câu cuối trang).
    """
    clean = [
        (idx, y1, y2)
        for (idx, y1, y2, has_next) in number_cands
        if has_next and geo.pair_min <= y2 - y1 <= geo.pair_max
    ]
    if clean:
        idx, y1, y2 = max(
            clean,
            key=lambda c: block_sharpness(
                cv2.cvtColor(frames[c[0]], cv2.COLOR_BGR2GRAY), c[1], c[2], geo
            ),
        )
        return idx, y1, y2

    roomy = [
        (idx, y1) for (idx, y1, _, _) in number_cands if geo.H - y1 >= geo.tail_room
    ]
    if roomy:
        idx, y1 = max(
            roomy,
            key=lambda c: block_sharpness(
                cv2.cvtColor(frames[c[0]], cv2.COLOR_BGR2GRAY), c[1], geo.H, geo
            ),
        )
    else:
        y1, idx = min((y1, idx) for (idx, y1, _, _) in number_cands)
    return idx, y1, geo.H


def extract_questions(
    video_path: Path,
    output_dir: Path,
    cache_path: Path,
    step: int,
) -> dict:
    """Trích xuất, lưu question-NN.png. Trả về {"saved": [...], "missing": [...]}."""
    frames = load_frames(video_path)
    full_h, full_w = frames[0].shape[:2]
    # Crop về vùng content (bỏ status bar + thanh browser) theo tỉ lệ -> OCR sạch hơn.
    c_top = int(cfg.F_CONTENT_TOP * full_h)
    c_bot = int(cfg.F_CONTENT_BOT * full_h)
    frames = [f[c_top:c_bot] for f in frames]
    height, width = frames[0].shape[:2]
    geo = Geom(height, width)
    logger.info(
        "Video %dx%d (content %dx%d), %d frame.",
        full_w,
        full_h,
        width,
        height,
        len(frames),
    )

    data = load_or_build_cache(frames, geo, cache_path, step)
    candidates = _collect_candidates(data, height)

    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in output_dir.glob("*.png"):
        stale.unlink()

    saved = []
    for number in sorted(candidates):
        idx, y1, hard = _pick_source(candidates[number], frames, geo)
        best_idx = sharpest_neighbor(frames, idx, y1, min(hard, height), geo)
        top = max(0, y1 - geo.top_margin)
        if hard < height:  # có header câu kế -> cắt tới ngay trước header đó
            crop = frames[best_idx][top : hard - geo.top_margin]
        else:  # câu cuối trang -> cắt tới đáy content rồi bỏ khoảng trắng thừa
            crop = trim_trailing_white(frames[best_idx][top:height])
        cv2.imwrite(str(output_dir / f"question-{number:02d}.png"), crop)
        saved.append(number)

    missing = []
    if saved:
        missing = [n for n in range(min(saved), max(saved) + 1) if n not in saved]
    return {"saved": saved, "missing": missing}


def log_report(result: dict, output_dir: Path) -> None:
    """Ghi log tóm tắt kết quả trích xuất."""
    saved, missing = result["saved"], result["missing"]
    logger.info("Đã lưu %d câu -> %s/", len(saved), output_dir)
    logger.info("Các câu: %s", saved)
    if saved:
        span = f"{min(saved)}-{max(saved)}"
        status = missing if missing else "không (đủ liên tục)"
        logger.info("Range %s, THIẾU: %s", span, status)
