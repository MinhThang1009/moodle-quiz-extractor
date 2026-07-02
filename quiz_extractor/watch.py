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
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from . import config as cfg
from .extractor import extract_questions, log_report
from .to_text import DEFAULT_LLM_MODEL, extract_text

logger = logging.getLogger(__name__)


def positive_int(value: str) -> int:
    """argparse type: số nguyên dương."""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("phải là số nguyên") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("phải > 0")
    return parsed


def positive_float(value: str) -> float:
    """argparse type: số thực dương."""
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("phải là số") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("phải > 0")
    return parsed


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


def _already_done(out_root: Path, video: Path, reprocess: bool) -> bool:
    """True nếu video đã có ảnh câu -> bỏ qua (trừ khi --reprocess)."""
    if reprocess:
        return False
    return any(_outputs(out_root, video)[1].glob("question-*.png"))


def _worker_init(threads: int) -> None:
    """Init worker pool: UTF-8, tắt progress \\r, giới hạn thread/worker."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    os.environ["QUIZ_QUIET_PROGRESS"] = "1"
    os.environ["OMP_NUM_THREADS"] = str(threads)
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)


def process_video(
    video: Path,
    out_root: Path,
    step: int,
    to_text: str,
    model: str,
    config_path: Path | None = None,
) -> None:
    """Chạy pipeline cho 1 video: trích ảnh câu, rồi OCR text nếu bật."""
    if config_path:
        cfg.load_overrides(config_path)
    out_dir, questions_dir, cache = _outputs(out_root, video)
    os.environ["QUIZ_LABEL"] = video.name  # nhãn cho dòng tiến độ OCR (phân biệt video)
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
    workers: int,
    config_path: Path | None = None,
) -> None:
    if workers > 1:
        _watch_parallel(
            input_dir,
            out_root,
            step,
            to_text,
            model,
            interval,
            stable,
            reprocess,
            once,
            workers,
            config_path,
        )
    else:
        _watch_sequential(
            input_dir,
            out_root,
            step,
            to_text,
            model,
            interval,
            stable,
            reprocess,
            once,
            config_path,
        )


def _watch_sequential(
    input_dir,
    out_root,
    step,
    to_text,
    model,
    interval,
    stable,
    reprocess,
    once,
    config_path,
) -> None:
    seen: dict[Path, float] = {}  # video -> mtime đã xử lý
    logger.info("Theo dõi %s/ (mỗi %.0fs). Ctrl+C để dừng.", input_dir, interval)
    while True:
        for video in sorted(input_dir.glob("*.mp4")):
            mtime = video.stat().st_mtime
            if seen.get(video) == mtime:
                continue
            if _already_done(out_root, video, reprocess):
                seen[video] = mtime  # đã có kết quả -> bỏ qua
                continue
            if not _is_stable(video, stable):
                continue  # đang copy, để lần quét sau
            try:
                process_video(video, out_root, step, to_text, model, config_path)
            except Exception:  # noqa: BLE001 - watcher không được chết vì 1 video lỗi
                logger.exception("Lỗi khi xử lý %s, bỏ qua.", video.name)
            seen[video] = video.stat().st_mtime
        if once:
            return
        time.sleep(interval)


def _watch_parallel(
    input_dir,
    out_root,
    step,
    to_text,
    model,
    interval,
    stable,
    reprocess,
    once,
    workers,
    config_path,
) -> None:
    threads = max(1, (os.cpu_count() or 4) // workers)
    ex = ProcessPoolExecutor(
        max_workers=workers, initializer=_worker_init, initargs=(threads,)
    )
    seen: dict[Path, float] = {}
    inflight: dict[Path, tuple] = {}  # video -> (future, mtime)
    logger.info(
        "Theo dõi %s/ — song song %d video. Ctrl+C để dừng.", input_dir, workers
    )
    try:
        if once:
            vids = [
                v
                for v in sorted(input_dir.glob("*.mp4"))
                if not _already_done(out_root, v, reprocess) and _is_stable(v, stable)
            ]
            futs = {
                ex.submit(
                    process_video, v, out_root, step, to_text, model, config_path
                ): v
                for v in vids
            }
            for v in vids:
                logger.info("▶ Bắt đầu %s", v.name)
            for fut in as_completed(futs):
                _reap(fut, futs[fut])
            return
        while True:
            for video in sorted(input_dir.glob("*.mp4")):
                if video in inflight:
                    continue
                mtime = video.stat().st_mtime
                if seen.get(video) == mtime:
                    continue
                if _already_done(out_root, video, reprocess):
                    seen[video] = mtime
                    continue
                if not _is_stable(video, stable):
                    continue
                inflight[video] = (
                    ex.submit(
                        process_video,
                        video,
                        out_root,
                        step,
                        to_text,
                        model,
                        config_path,
                    ),
                    mtime,
                )
                logger.info("▶ Bắt đầu %s", video.name)
            for video in list(inflight):
                fut, mtime = inflight[video]
                if fut.done():
                    _reap(fut, video)
                    seen[video] = mtime
                    del inflight[video]
            time.sleep(interval)
    finally:
        ex.shutdown(wait=True)


def _reap(fut, video: Path) -> None:
    try:
        fut.result()
        logger.info("✓ Xong %s", video.name)
    except Exception:  # noqa: BLE001 - 1 video lỗi không làm chết batch
        logger.exception("Lỗi khi xử lý %s", video.name)


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
        "--step", type=positive_int, default=cfg.DEFAULT_STEP, help="OCR mỗi STEP frame"
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
        "--interval", type=positive_float, default=5.0, help="Chu kỳ quét (giây)"
    )
    parser.add_argument(
        "--stable",
        type=positive_float,
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
        "--workers",
        type=positive_int,
        default=1,
        help="Số video xử lý song song (>1 = process pool)",
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
            args.workers,
            args.config,
        )
    except KeyboardInterrupt:
        logger.info("Đã dừng watcher.")


if __name__ == "__main__":
    main()
