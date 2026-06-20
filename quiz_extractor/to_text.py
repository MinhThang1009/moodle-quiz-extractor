"""Chuyển ảnh câu (output/questions/question-NN.png) sang TEXT bằng easyocr.

Pipeline: upscale 2x (giúp đọc dấu tiếng Việt + nhãn a/b/c/d) -> OCR -> gom detection
thành dòng theo y -> tách câu hỏi (cột trái) và đáp án (cột phải, mốc là nhãn a/b/c/d).
Xuất questions.json (cấu trúc) + questions.md (đọc).

OCR không bao giờ exact 100% (dấu tiếng Việt có thể sai lác đác) -> nên rà lại; cần
chính xác tuyệt đối thì dùng vision LLM (xem README).
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path

import cv2

from . import config as cfg

logger = logging.getLogger(__name__)

UPSCALE = 2
F_YTOL = 0.020  # gom dòng: |dy| < ngưỡng (tỉ lệ H ảnh đã upscale)
F_LETTER_X_MAX = 0.18  # nhãn a/b/c/d nằm ở cột x < ngưỡng (tỉ lệ W)
HEADER_RE = re.compile(r"^\s*(question\b|not yet|marked out of|flag\b)", re.I)
OPTION_RE = re.compile(r"^([a-dA-D])(?:[.)]\s*|\s+)(.+)")
NUM_RE = re.compile(r"question-(\d+)", re.I)
# Lưới điều hướng Moodle ở đáy trang -> cắt bỏ nếu lọt vào text
NAV_RE = re.compile(r"\s*(previous page|next page|quiz navigation).*$", re.I)

# --- Engine LLM (Anthropic vision) ---
DEFAULT_LLM_MODEL = "claude-opus-4-8"
LLM_PROMPT = (
    "Đây là ảnh một câu hỏi trắc nghiệm Moodle tiếng Việt. Trích CHÍNH XÁC phần đề bài "
    "và các đáp án, giữ nguyên dấu tiếng Việt. Bỏ qua header 'Question N', "
    "'Not yet answered', 'Marked out of', 'Flag question' và lưới điều hướng. "
    "Mỗi đáp án gồm label (a/b/c/d) và text."
)
LLM_SCHEMA = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "options": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "text": {"type": "string"},
                },
                "required": ["label", "text"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["question", "options"],
    "additionalProperties": False,
}


def _strip_nav(text: str) -> str:
    return NAV_RE.sub("", text).strip()


def parse_question(rows: list, width: int) -> dict:
    """rows (đã gom, sort theo y) -> {"question": str, "options": {a..: str}}.

    Đáp án gán nhãn a/b/c/d theo THỨ TỰ xuất hiện (không tin nhãn OCR có thể sai).
    """
    letter_x_max = F_LETTER_X_MAX * width
    q_lines: list[str] = []
    options: list[str] = []
    for r in rows:
        text = r["text"].strip()
        if not text or HEADER_RE.match(text):
            continue
        m = OPTION_RE.match(text)
        if m and r["x0"] < letter_x_max:
            options.append(m.group(2).strip())
        elif options:
            options[-1] += " " + text  # dòng xuống hàng của đáp án hiện tại
        else:
            q_lines.append(text)
    question = _strip_nav(" ".join(q_lines).strip())
    labelled = {chr(ord("a") + i): _strip_nav(opt) for i, opt in enumerate(options[:8])}
    return {"question": question, "options": labelled}


def _number_of(path: Path) -> int:
    match = NUM_RE.search(path.name)
    return int(match.group(1)) if match else 0


def _questions_easyocr(images: list) -> list:
    """OCR offline bằng easyocr (~95%, sai dấu lác đác)."""
    import easyocr  # import muộn: nặng

    reader = easyocr.Reader(list(cfg.OCR_LANGS), gpu=False, verbose=False)
    results = []
    for path in images:
        up = cv2.resize(
            cv2.imread(str(path)),
            None,
            fx=UPSCALE,
            fy=UPSCALE,
            interpolation=cv2.INTER_CUBIC,
        )
        ytol = max(8, int(F_YTOL * up.shape[0]))
        rows = _cluster_rows(reader.readtext(up, detail=1, paragraph=False), ytol)
        parsed = parse_question(rows, up.shape[1])
        parsed["number"] = _number_of(path)
        results.append(parsed)
        logger.info("Câu %d: %d đáp án", parsed["number"], len(parsed["options"]))
    return results


def _questions_llm(images: list, model: str) -> list:
    """Vision LLM (Anthropic) — chính xác nhất; cần ANTHROPIC_API_KEY, có chi phí."""
    import base64

    import anthropic  # import muộn: chỉ cần khi dùng engine llm

    client = anthropic.Anthropic()  # đọc ANTHROPIC_API_KEY từ môi trường
    results = []
    for path in images:
        data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": data,
                            },
                        },
                        {"type": "text", "text": LLM_PROMPT},
                    ],
                }
            ],
            output_config={"format": {"type": "json_schema", "schema": LLM_SCHEMA}},
        )
        text = next(b.text for b in response.content if b.type == "text")
        obj = json.loads(text)
        options = {
            chr(ord("a") + i): o["text"].strip()
            for i, o in enumerate(obj.get("options", [])[:8])
        }
        number = _number_of(path)
        results.append(
            {
                "number": number,
                "question": obj.get("question", "").strip(),
                "options": options,
            }
        )
        logger.info("Câu %d: %d đáp án", number, len(options))
    return results


def extract_text(images_dir: Path, out_dir: Path, engine: str, model: str) -> list:
    images = sorted(images_dir.glob("question-*.png"))
    if not images:
        raise SystemExit(f"Không có ảnh question-*.png trong {images_dir}")

    results = (
        _questions_llm(images, model) if engine == "llm" else _questions_easyocr(images)
    )
    results.sort(key=lambda r: r["number"])

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "questions.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "questions.md").write_text(_to_markdown(results), encoding="utf-8")
    return results


def _cluster_rows(detections, ytol: int) -> list:
    """Gom detection thành dòng theo y (|dy|<ytol); nối text trong dòng theo x."""
    if not detections:
        return []
    items = sorted(
        ((int(b[0][0]), int(b[0][1]), t) for b, t, _ in detections),
        key=lambda r: (r[1], r[0]),
    )
    groups: list[tuple[int, list[tuple[int, str]]]] = []
    for x, y, text in items:
        if groups and abs(y - groups[-1][0]) <= ytol:
            groups[-1][1].append((x, text))
        else:
            groups.append((y, [(x, text)]))
    out = []
    for y, parts in groups:
        parts.sort()
        out.append({"y": y, "x0": parts[0][0], "text": " ".join(p[1] for p in parts)})
    return out


def _to_markdown(results: list) -> str:
    lines = ["# Câu hỏi (trích từ ảnh bằng OCR — nên rà lại)\n"]
    for r in results:
        lines.append(f"## Câu {r['number']}\n")
        if r["question"]:
            lines.append(r["question"] + "\n")
        for letter, opt in r["options"].items():
            lines.append(f"- **{letter}.** {opt}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        prog="quiz_extractor.to_text",
        description="OCR ảnh câu (question-*.png) sang text (json + md).",
    )
    parser.add_argument(
        "--input", type=Path, default=cfg.DEFAULT_OUTPUT, help="Thư mục ảnh câu"
    )
    parser.add_argument(
        "--output", type=Path, default=Path("output"), help="Thư mục xuất json/md"
    )
    parser.add_argument(
        "--engine",
        choices=["easyocr", "llm"],
        default="easyocr",
        help="easyocr (offline) hoặc llm (Anthropic vision, cần ANTHROPIC_API_KEY)",
    )
    parser.add_argument(
        "--model", default=DEFAULT_LLM_MODEL, help="Model khi --engine llm"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    results = extract_text(args.input, args.output, args.engine, args.model)
    logger.info("Đã xuất %d câu -> %s/questions.{json,md}", len(results), args.output)


if __name__ == "__main__":
    main()
