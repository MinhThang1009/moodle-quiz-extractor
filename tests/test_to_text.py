"""parse_question: tách câu hỏi + 4 đáp án từ các dòng OCR (logic thuần, không OCR)."""

import sys
import types
from pathlib import Path

import pytest

from quiz_extractor.to_text import _llm_result, parse_question


def test_llm_result_maps_options_by_order():
    obj = {
        "question": " Câu hỏi mẫu? ",
        "options": [{"label": "a", "text": " Một "}, {"label": "b", "text": "Hai"}],
    }
    assert _llm_result(obj, 7) == {
        "number": 7,
        "question": "Câu hỏi mẫu?",
        "options": {"a": "Một", "b": "Hai"},
    }


def test_llm_result_tolerates_missing_fields():
    assert _llm_result({}, 1) == {"number": 1, "question": "", "options": {}}


def test_anthropic_lower_bound_matches_structured_outputs_requirement():
    root = Path(__file__).resolve().parents[1]
    assert "anthropic>=0.115" in (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "anthropic>=0.115" in (root / "README.md").read_text(encoding="utf-8")


def test_extract_text_rejects_unreadable_image(tmp_path, monkeypatch):
    from quiz_extractor import to_text

    class FakeReader:
        def __init__(self, *args, **kwargs):
            pass

    fake_easyocr = types.ModuleType("easyocr")
    fake_easyocr.Reader = FakeReader
    monkeypatch.setitem(sys.modules, "easyocr", fake_easyocr)
    monkeypatch.setattr("quiz_extractor.ocr.gpu_available", lambda: False)
    images_dir = tmp_path / "questions"
    images_dir.mkdir()
    (images_dir / "question-01.png").write_bytes(b"not a png")

    with pytest.raises(SystemExit, match="Không đọc được ảnh"):
        to_text.extract_text(images_dir, tmp_path / "out", "easyocr", "unused")


def test_parse_question_splits_four_options():
    # toạ độ kiểu ảnh upscale: câu hỏi x≈72, nhãn a/b/c/d x≈140, dòng nối x≈200
    rows = [
        {"y": 10, "x0": 50, "text": "Question 7"},  # header -> bỏ
        {"y": 40, "x0": 50, "text": "Marked out of 1.00"},  # header -> bỏ
        {"y": 70, "x0": 72, "text": "Câu hỏi mẫu?"},
        {"y": 100, "x0": 140, "text": "a. Đáp án A"},
        {"y": 130, "x0": 140, "text": "b Đáp án B"},
        {"y": 155, "x0": 200, "text": "nối tiếp B"},  # dòng xuống hàng của b
        {"y": 185, "x0": 140, "text": "c) Đáp án C"},
        {"y": 215, "x0": 140, "text": "d. Đáp án D"},
    ]
    result = parse_question(rows, width=960)
    assert result["question"] == "Câu hỏi mẫu?"
    assert result["options"] == {
        "a": "Đáp án A",
        "b": "Đáp án B nối tiếp B",
        "c": "Đáp án C",
        "d": "Đáp án D",
    }


def test_parse_question_relabels_by_order():
    # nhãn OCR sai ("x.") vẫn được gán lại theo thứ tự a, b
    rows = [
        {"y": 70, "x0": 72, "text": "Câu?"},
        {"y": 100, "x0": 140, "text": "x. Một"},
        {"y": 130, "x0": 140, "text": "b. Hai"},
    ]
    result = parse_question(rows, width=960)
    # "x." không khớp a-d -> coi là phần câu hỏi; chỉ "b. Hai" là đáp án -> gán 'a'
    assert result["options"] == {"a": "Hai"}
