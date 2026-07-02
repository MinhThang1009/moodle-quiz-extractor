"""Đọc video, OCR tìm header "Question N", và cache kết quả OCR ra đĩa.

Cache phụ thuộc (video size, STEP). Lệch -> tự OCR lại.
"""

import logging
import os
import pickle
import re
import sys
from pathlib import Path

import cv2
import numpy as np

from . import config as cfg
from .geometry import Geom

logger = logging.getLogger(__name__)

SAVE_EVERY = 40  # lưu cache mỗi N frame đã OCR (cache resume thông minh)


def gpu_available() -> bool:
    """True nếu có GPU (CUDA/MPS) để easyocr chạy nhanh hơn nhiều."""
    try:
        import torch
    except ImportError:
        return False
    if torch.cuda.is_available():
        return True
    mps = getattr(torch.backends, "mps", None)
    return bool(mps and mps.is_available())


def video_props(video_path: Path) -> tuple[int, int, int]:
    """Trả về (số frame, H, W) mà không nạp toàn bộ video vào RAM."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise SystemExit(f"Không mở được video: {video_path}")
    ok, frame = cap.read()
    if not ok:
        cap.release()
        raise SystemExit(f"Video rỗng: {video_path}")
    h, w = frame.shape[:2]
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0  # best-effort (vài file báo sai)
    cap.release()
    return max(n, 0), h, w


def read_content_frames(video_path: Path, indices, c_top: int, c_bot: int) -> dict:
    """Đọc CHỈ các frame cần (đã crop content) -> {idx: frame}. Bộ nhớ ~ số idx."""
    want = set(indices)
    out: dict[int, object] = {}
    cap = cv2.VideoCapture(str(video_path))
    idx = 0
    while want:
        ok, frame = cap.read()
        if not ok:
            break
        if idx in want:
            out[idx] = frame[c_top:c_bot].copy()
            want.discard(idx)
        idx += 1
    cap.release()
    return out


def detect_content_band(
    video_path: Path, step: int = 5, t: float = 7.0
) -> tuple[float, float] | None:
    """Tự suy vùng nội dung web (bỏ chrome trình duyệt / status bar / overlay đáy).

    Ý tưởng: chỉ xét các cặp frame "cuộn thuần" (dải trên cùng đứng yên -> chrome/status
    bar không đổi, chỉ nội dung dịch), bỏ cặp chuyển tab/trang. Hàng động ở nhiều cặp =
    nội dung; chrome và overlay (kể cả overlay ẩn/hiện theo cuộn) thì ít/không động.
    Ngưỡng thích ứng theo mức động đỉnh nên không phụ thuộc độ phân giải/bố cục.

    Trả (f_top, f_bot) theo tỉ lệ H. Bất thường -> None để nơi gọi fallback về config.
    Đọc tuần tự, chỉ giữ 2 frame (seek không đáng tin với vài codec).
    """
    cap = cv2.VideoCapture(str(video_path))
    votes = None
    topband = 0
    prev = None
    idx = 0
    height = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.int16)
            if votes is None:
                height = gray.shape[0]
                votes = np.zeros(height)
                topband = max(1, int(0.05 * height))
            if prev is not None:
                row_diff = np.abs(gray - prev).mean(axis=1)
                if row_diff[:topband].mean() < 3.0:  # chrome trên yên -> cặp cuộn thuần
                    votes += row_diff > t
            prev = gray
        idx += 1
    cap.release()

    if votes is None or not votes.any():
        return None
    peak = float(np.percentile(votes, 90))  # mức động của nội dung thật
    if peak <= 0:
        return None
    dynamic = np.where(votes > 0.6 * peak)[0]
    if len(dynamic) == 0:
        return None
    f_top, f_bot = dynamic[0] / height, (dynamic[-1] + 1) / height
    # Clamp an toàn: kết quả vô lý (cắt quá nửa / dải quá hẹp) -> để nơi gọi fallback.
    if f_top > 0.4 or f_bot < 0.6 or f_bot - f_top < 0.3:
        return None
    return f_top, f_bot


def parse_headers(detections, geo: Geom) -> list:
    """OCR detail=1 -> list (qnum, header_y) sort theo y.

    Gộp trường hợp OCR tách "Question" và số thành 2 box cạnh nhau, và suy số cho
    header "Question" mà OCR trượt mất số (vd số "1" đơn lẻ mảnh khó đọc).
    """
    items, qword, nums, marker_ys = [], [], [], []
    for bbox, txt, _ in detections:
        y, x = bbox[0][1], bbox[0][0]
        token = txt.strip().lower()
        matched = cfg.QUESTION_RE.fullmatch(token)
        if matched and int(matched.group(1)) >= 1:  # Moodle đánh số từ 1
            items.append((int(matched.group(1)), y))
        elif token == "question" and x <= geo.head_xleft:
            qword.append(
                (y, x)
            )  # mép trái -> header thật; loại "question" của "Flag question"
        elif re.fullmatch(r"\d{1,3}", token):
            nums.append((y, x, int(token)))
        if any(mk in token for mk in cfg.QUIZ_MARKERS):
            marker_ys.append(y)  # dòng "Marked out of"/"Not yet"/"Flag question"
    orphans = []  # "Question" không ghép được số
    for qy, qx in qword:
        near = [
            (abs(ny - qy), value)
            for ny, nx, value in nums
            if abs(ny - qy) <= geo.head_ytol and 0 < nx - qx < geo.head_xdist
        ]
        value = min(near)[1] if near else 0
        if value >= 1:  # ghép được số hợp lệ (Moodle từ 1); 0 = đọc sai -> để suy số
            items.append((value, qy))
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
    # Anchor: header thật phải có marker grey-box ngay dưới (loại false-header).
    items = [
        (n, y)
        for (n, y) in items
        if any(y < my <= y + geo.head_span for my in marker_ys)
    ]
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


def _matches(cached: dict, geo: Geom, step: int, c_top: int, c_bot: int) -> bool:
    return (
        cached.get("h") == geo.H
        and cached.get("w") == geo.W
        and cached.get("step") == step
        and cached.get("c_top") == c_top
        and cached.get("c_bot") == c_bot
    )


def _is_complete(cached: dict) -> bool:
    # Cache cũ (không có khóa "next") coi như đã hoàn tất.
    return bool(cached.get("complete", "next" not in cached))


def _save_cache(cache_path, geo, step, c_top, c_bot, data, next_idx, complete) -> None:
    """Ghi cache nguyên tử (tmp + replace) để Ctrl+C giữa chừng không làm hỏng file."""
    payload = {
        "h": geo.H,
        "w": geo.W,
        "step": step,
        "c_top": c_top,
        "c_bot": c_bot,
        "data": data,
        "next": next_idx,
        "complete": complete,
    }
    tmp = cache_path.with_suffix(".tmp")
    with open(tmp, "wb") as fh:
        pickle.dump(payload, fh)
    tmp.replace(cache_path)


def _progress(scanned: int, total: int, idx: int, headers: list, skipped: int) -> None:
    """Tiến độ OCR: stream \\r khi 1 video; mốc ~10%/dòng (kèm nhãn) khi song song."""
    label = os.environ.get("QUIZ_LABEL", "")
    tag = f"[{label}] " if label else ""
    if os.environ.get("QUIZ_QUIET_PROGRESS"):
        # Song song: \r đè nhau -> in mốc ~10% mỗi dòng, kèm nhãn để phân biệt video.
        if total and scanned % max(1, total // 10) == 0:
            sys.stdout.write(
                f"{tag}OCR {100.0 * scanned / total:3.0f}% (frame {idx})\n"
            )
            sys.stdout.flush()
        return
    nums = ",".join(str(n) for n, _ in headers) if headers else "-"
    pct = 100.0 * scanned / total if total else 100.0
    sys.stdout.write(
        f"\r{tag}OCR {scanned:4d}/{total} ({pct:5.1f}%) "
        f"f{idx:5d} skip{skipped:4d} câu[{nums}]   "
    )
    sys.stdout.flush()


def build_cache(
    video_path: Path, geo: Geom, cache_path: Path, step: int, c_top: int, c_bot: int
) -> list:
    """Stream video, OCR mỗi `step` frame, lưu (idx, [(num, y, sharp)]).

    Streaming -> bộ nhớ ~1 frame. Stream tiến độ + cache resume thông minh. Mỗi header
    kèm độ nét block (tính ngay tại frame) để selection sau khỏi phải đọc lại frame.
    """
    import easyocr  # import muộn: nặng (torch)

    from .imaging import block_sharpness

    cache_path.parent.mkdir(parents=True, exist_ok=True)  # tạo folder ngay
    n = video_props(video_path)[0]
    total = (n + step - 1) // step if n > 0 else 0

    # Resume nếu có cache DỞ khớp (size, step) -> tiếp tục từ frame còn lại.
    start, data = 0, []
    cached = _read_cache(cache_path)
    if (
        cached
        and _matches(cached, geo, step, c_top, c_bot)
        and not _is_complete(cached)
    ):
        start = int(cached.get("next", 0))
        data = list(cached.get("data", []))
        logger.info("Tiếp tục OCR từ frame %d (đã có %d câu).", start, len(data))

    reader = easyocr.Reader(list(cfg.OCR_LANGS), gpu=gpu_available(), verbose=False)
    cap = cv2.VideoCapture(str(video_path))
    idx, ocred, skipped, scanned = 0, 0, 0, 0
    last_gray = None  # frame OCR gần nhất (anchor) để bỏ qua frame tĩnh trùng nội dung
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0 and idx >= start:
            gray = cv2.cvtColor(frame[c_top:c_bot], cv2.COLOR_BGR2GRAY)
            scanned += 1
            # So với anchor (không phải frame liền trước) -> cuộn chậm tích lũy vẫn được
            # OCR khi đủ khác; tĩnh hoàn toàn thì bỏ qua tới khi cuộn. Không sót câu.
            still = (
                last_gray is not None
                and float(cv2.absdiff(gray, last_gray).mean()) < cfg.STILL_DIFF
            )
            if still:
                skipped += 1
                _progress(start // step + scanned, total, idx, [], skipped)
            else:
                last_gray = gray
                detections = reader.readtext(
                    frame[c_top:c_bot], detail=1, paragraph=False
                )
                headers = parse_headers(detections, geo)
                if _is_quiz_frame(detections, headers):
                    triples = []
                    for i, (num, y) in enumerate(headers):
                        y2 = headers[i + 1][1] if i + 1 < len(headers) else geo.H
                        triples.append((num, y, block_sharpness(gray, y, y2, geo)))
                    data.append((idx, triples))
                ocred += 1
                _progress(start // step + scanned, total, idx, headers, skipped)
                if ocred % SAVE_EVERY == 0:
                    _save_cache(
                        cache_path, geo, step, c_top, c_bot, data, idx + step, False
                    )
        idx += 1
    cap.release()

    _save_cache(cache_path, geo, step, c_top, c_bot, data, idx, True)
    sys.stdout.write("\n")
    sys.stdout.flush()
    logger.info(
        "Đã cache %d frame quiz (%d OCR, %d bỏ qua frame tĩnh) -> %s",
        len(data),
        ocred,
        skipped,
        cache_path,
    )
    return data


def load_or_build_cache(
    video_path: Path, geo: Geom, cache_path: Path, step: int, c_top: int, c_bot: int
) -> list:
    """Dùng cache nếu khớp & hoàn tất; cache dở -> OCR tiếp; lệch -> OCR lại."""
    cached = _read_cache(cache_path)
    if cached and _matches(cached, geo, step, c_top, c_bot):
        if _is_complete(cached):
            logger.info("Dùng cache %s.", cache_path)
            return cached["data"]
        logger.info("Cache còn dở -> tiếp tục OCR.")
    elif cached:
        logger.info("Cache lệch (độ phân giải/STEP) -> OCR lại.")
    return build_cache(video_path, geo, cache_path, step, c_top, c_bot)
