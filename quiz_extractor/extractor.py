"""Orchestration: từ video -> 1 ảnh/câu (không sót, không lặp).

Quy trình (tiết kiệm RAM — không nạp toàn bộ video):
  1. Stream video, OCR (hoặc dùng cache) tìm header "Question N" + độ nét từng block.
  2. Gom ứng viên theo số câu; mỗi câu chọn nguồn tốt nhất (dùng độ nét đã cache).
  3. Đọc CHỈ các frame cần (frame chọn ± lân cận), refine + cắt block + lưu.
"""

import logging
from collections import defaultdict
from pathlib import Path

import cv2

from . import config as cfg
from .geometry import Geom
from .imaging import sharpest_neighbor, trim_trailing_white
from .ocr import (
    detect_content_band,
    load_or_build_cache,
    read_content_frames,
    video_props,
)

logger = logging.getLogger(__name__)


def _collect_candidates(data: list, height: int) -> dict:
    """data [(idx, [(num, y, sharp)])] -> {qnum: [(idx, y1, y2, has_next, sharp)]}."""
    candidates = defaultdict(list)
    for idx, headers in data:
        for i, (number, y1, sharp) in enumerate(headers):
            if i + 1 < len(headers):
                y2, has_next = headers[i + 1][1], True
            else:
                y2, has_next = height, False
            candidates[number].append((idx, y1, y2, has_next, sharp))
    return candidates


def _pick_source(number_cands: list, geo: Geom):
    """Chọn (idx, y1, hard_limit) tốt nhất cho câu — dùng độ nét đã cache.

    Ưu tiên block có header kế (biên rõ) + nét nhất; nếu không có thì lấy frame header
    cao nhất (chỗ trống nhiều nhất) để lọt cả block (câu dài / cuối trang).
    """
    m = geo.top_margin  # header phải cách mép trên >= m, nếu không bị content-crop xén
    clean = [
        (idx, y1, y2, sharp)
        for (idx, y1, y2, has_next, sharp) in number_cands
        if has_next and geo.pair_min <= y2 - y1 <= geo.pair_max and y1 >= m
    ]
    if clean:
        idx, y1, y2, _ = max(clean, key=lambda c: c[3])
        return idx, y1, y2
    # tail: header cao nhất nhưng không sát mép (tránh xén header, vẫn đủ chỗ dưới).
    safe = [(y1, idx) for (idx, y1, _, _, _) in number_cands if y1 >= m]
    y1, idx = (
        min(safe) if safe else min((y1, idx) for (idx, y1, _, _, _) in number_cands)
    )
    return idx, y1, geo.H


def extract_questions(
    video_path: Path,
    output_dir: Path,
    cache_path: Path,
    step: int,
    auto_crop: bool = True,
) -> dict:
    """Trích xuất, lưu question-NN.png. Trả về {"saved", "missing", "incomplete"}.

    auto_crop=True: tự suy vùng nội dung từ video (chạy mọi layout không cần --config);
    thất bại -> fallback tỉ lệ cố định trong config. auto_crop=False: luôn dùng config.
    """
    n_frames, full_h, full_w = video_props(video_path)
    f_top, f_bot = cfg.F_CONTENT_TOP, cfg.F_CONTENT_BOT
    if auto_crop:
        band = detect_content_band(video_path)
        if band:
            f_top, f_bot = band
            logger.info(
                "Auto-crop: vùng nội dung [%.3f, %.3f] (tỉ lệ H).", f_top, f_bot
            )
        else:
            logger.info(
                "Auto-crop không chắc chắn -> dùng tỉ lệ mặc định %.3f/%.3f.",
                f_top,
                f_bot,
            )
    c_top = int(f_top * full_h)
    c_bot = int(f_bot * full_h)
    height = c_bot - c_top
    geo = Geom(height, full_w)
    logger.info(
        "Video %dx%d (content %dx%d), %d frame.",
        full_w,
        full_h,
        full_w,
        height,
        n_frames,
    )

    data = load_or_build_cache(video_path, geo, cache_path, step, c_top, c_bot)
    candidates = _collect_candidates(data, height)
    picks = {n: _pick_source(candidates[n], geo) for n in sorted(candidates)}

    # Đọc CHỈ các frame cần: mỗi câu = frame chọn ± NEIGHBOR_R (để refine độ nét).
    needed: set[int] = set()
    for idx, _, _ in picks.values():
        needed.update(range(max(0, idx - cfg.NEIGHBOR_R), idx + cfg.NEIGHBOR_R + 1))
    frames = read_content_frames(video_path, needed, c_top, c_bot)

    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in output_dir.glob("question-*.png"):
        stale.unlink()

    saved, incomplete = [], []
    incomplete_h = int(cfg.F_INCOMPLETE * height)
    m = geo.top_margin
    for number, (idx, y1, hard) in picks.items():
        if idx not in frames:  # video ngắn hơn cache (đã đổi/cắt) -> bỏ câu, cảnh báo
            logger.warning(
                "Không đọc được frame %d cho câu %d (video đã đổi?).", idx, number
            )
            continue
        best = sharpest_neighbor(frames, idx, y1, min(hard, height), geo)
        top = max(0, y1 - m)  # chừa top_margin phía trên: bao viền info box + đệm
        if hard < height:  # có header câu kế -> cắt tới ngay trước header đó
            crop = frames[best][top : hard - m]
        else:  # câu cuối trang -> cắt tới đáy content rồi bỏ khoảng trắng thừa
            crop = trim_trailing_white(frames[best][top:height])
        target = output_dir / f"question-{number:02d}.png"
        if not cv2.imwrite(str(target), crop):
            raise SystemExit(f"Không ghi được ảnh: {target}")
        saved.append(number)
        if crop.shape[0] < incomplete_h:  # ảnh quá ngắn -> nghi thiếu nội dung
            incomplete.append(number)

    missing = []
    if saved:
        missing = [n for n in range(min(saved), max(saved) + 1) if n not in saved]
    return {"saved": saved, "missing": missing, "incomplete": incomplete}


def log_report(result: dict, output_dir: Path) -> None:
    """Ghi log tóm tắt; cảnh báo (WARNING) nếu thiếu câu hoặc câu thiếu nội dung."""
    saved, missing = result["saved"], result["missing"]
    incomplete = result.get("incomplete", [])
    logger.info("Đã lưu %d câu -> %s/", len(saved), output_dir)
    logger.info("Các câu: %s", saved)
    if saved:
        span = f"{min(saved)}-{max(saved)}"
        if missing:
            logger.warning("⚠ THIẾU câu trong khoảng %s: %s", span, missing)
        else:
            logger.info("Range %s: đủ liên tục, không sót.", span)
    if incomplete:
        logger.warning("⚠ Câu có thể THIẾU NỘI DUNG (ảnh quá ngắn): %s", incomplete)
