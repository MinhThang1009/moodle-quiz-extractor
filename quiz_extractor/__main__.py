"""CLI: python -m quiz_extractor [--video ...] [--output ...] [--step N] [--force-ocr].

Ví dụ video khác cùng template:
    python -m quiz_extractor --video data/2.mp4 --output output/quiz2
"""

import argparse
import logging
import sys
from pathlib import Path

from . import config as cfg
from .extractor import extract_questions, log_report


def _force_utf8() -> None:
    """Console Windows mặc định cp1252 không in được tiếng Việt -> ép UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quiz_extractor",
        description="Trích xuất 1 ảnh/câu từ video screen-recording quiz Moodle.",
    )
    parser.add_argument(
        "--video", type=Path, default=cfg.DEFAULT_VIDEO, help="Đường dẫn video .mp4"
    )
    parser.add_argument(
        "--output", type=Path, default=cfg.DEFAULT_OUTPUT, help="Thư mục lưu ảnh câu"
    )
    parser.add_argument(
        "--cache", type=Path, default=cfg.DEFAULT_CACHE, help="File cache OCR"
    )
    parser.add_argument(
        "--step", type=int, default=cfg.DEFAULT_STEP, help="OCR mỗi STEP frame"
    )
    parser.add_argument(
        "--force-ocr", action="store_true", help="Bỏ cache, OCR lại từ đầu"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="In thêm log DEBUG"
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Chỉ in cảnh báo/lỗi"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="JSON override template (markers/fractions)",
    )
    return parser


def _setup_logging(verbose: bool, quiet: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING if quiet else logging.INFO
    logging.basicConfig(level=level, format="%(message)s", stream=sys.stdout)


def main() -> None:
    _force_utf8()
    args = build_parser().parse_args()
    _setup_logging(args.verbose, args.quiet)
    if args.config:
        cfg.load_overrides(args.config)
    if args.force_ocr and args.cache.exists():
        args.cache.unlink()
    result = extract_questions(args.video, args.output, args.cache, args.step)
    log_report(result, args.output)


if __name__ == "__main__":
    main()
