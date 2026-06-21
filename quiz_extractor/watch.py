"""Watcher: theo dõi thư mục video, tự chạy pipeline khi có video mới.

Dùng polling (không cần dep watchdog) — quét thư mục mỗi `interval` giây, xử lý video
mới/đã đổi, chờ file copy xong (size ổn định) trước khi chạy. Mỗi video xuất ra
`output/<tên-video>/` (ảnh câu + cache, và text nếu bật --to-text).

    python -m quiz_extractor.watch                 # theo dõi data/, OCR easyocr
    python -m quiz_extractor.watch --to-text none  # chỉ trích ảnh, không OCR text
    python -m quiz_extractor.watch --to-text llm   # OCR bằng vision LLM
"""

import argparse
import logging
import sys
import time
from pathlib import Path

from . import config as cfg
from .extractor import extract_questions, log_report
from .to_text import DEFAULT_LLM_MODEL, extract_text

logger = logging.getLogger(__name__)


def _outputs(out_root: Path, video: Path) -> tuple[Path, Path, Path]:
    """(out_dir, questions_dir, cache_path) cho 1 video."""
    out_dir = out_root / video.stem
    return out_dir, out_dir / "questions", out_dir / "ocr_cache.pkl"


def _is_stable(video: Path, secs: float) -> bool:
    """File coi là copy xong nếu size > 0 và không đổi sau `secs` giây."""
    try:
        size1 = video.stat().st_size
    except OSError:
        return False
    time.sleep(secs)
    try:
        return size1 > 0 and video.stat().st_size == size1
    except OSError:
        return False


def process_video(
    video: Path, out_root: Path, step: int, to_text: str, model: str
) -> None:
    """Chạy pipeline cho 1 video: trích ảnh câu, rồi OCR text nếu bật."""
    out_dir, questions_dir, cache = _outputs(out_root, video)
    logger.info("=== Xử lý %s -> %s/ ===", video.name, out_dir)
    result = extract_questions(video, questions_dir, cache, step)
    log_report(result, questions_dir)
    if to_text != "none":
        extract_text(questions_dir, out_dir, to_text, model)
        logger.info("Đã xuất text -> %s/questions.{json,md}", out_dir)


def watch(
    input_dir: Path,
    out_root: Path,
    step: int,
    to_text: str,
    model: str,
    interval: float,
    stable: float,
    reprocess: bool,
    once: bool,
) -> None:
    seen: dict[Path, float] = {}  # video -> mtime đã xử lý
    logger.info("Theo dõi %s/ (mỗi %.0fs). Ctrl+C để dừng.", input_dir, interval)
    while True:
        for video in sorted(input_dir.glob("*.mp4")):
            mtime = video.stat().st_mtime
            if seen.get(video) == mtime:
                continue
            _, questions_dir, _ = _outputs(out_root, video)
            if not reprocess and any(questions_dir.glob("*.png")):
                seen[video] = mtime  # đã có kết quả -> bỏ qua
                continue
            if not _is_stable(video, stable):
                continue  # đang copy, để lần quét sau
            try:
                process_video(video, out_root, step, to_text, model)
            except Exception:  # noqa: BLE001 - watcher không được chết vì 1 video lỗi
                logger.exception("Lỗi khi xử lý %s, bỏ qua.", video.name)
            seen[video] = video.stat().st_mtime
        if once:
            return
        time.sleep(interval)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        prog="quiz_extractor.watch",
        description="Theo dõi thư mục, tự chạy pipeline khi có video mới.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=cfg.DEFAULT_VIDEO.parent,
        help="Thư mục chứa video",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("output"), help="Thư mục gốc xuất kết quả"
    )
    parser.add_argument(
        "--step", type=int, default=cfg.DEFAULT_STEP, help="OCR mỗi STEP frame"
    )
    parser.add_argument(
        "--to-text",
        choices=["none", "easyocr", "llm"],
        default="easyocr",
        help="OCR ảnh sang text sau khi trích (none = chỉ trích ảnh)",
    )
    parser.add_argument(
        "--model", default=DEFAULT_LLM_MODEL, help="Model khi --to-text llm"
    )
    parser.add_argument(
        "--interval", type=float, default=5.0, help="Chu kỳ quét (giây)"
    )
    parser.add_argument(
        "--stable",
        type=float,
        default=2.0,
        help="Đợi size ổn định bấy nhiêu giây (file copy xong)",
    )
    parser.add_argument(
        "--reprocess", action="store_true", help="Xử lý lại cả video đã có kết quả"
    )
    parser.add_argument(
        "--once", action="store_true", help="Quét 1 lượt rồi thoát (không lặp)"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="JSON override template (markers/fractions)",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    if args.config:
        cfg.load_overrides(args.config)
    try:
        watch(
            args.input,
            args.output,
            args.step,
            args.to_text,
            args.model,
            args.interval,
            args.stable,
            args.reprocess,
            args.once,
        )
    except KeyboardInterrupt:
        logger.info("Đã dừng watcher.")


if __name__ == "__main__":
    main()
