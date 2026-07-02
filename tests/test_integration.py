"""Integration: chạy THẬT extract_questions trên video tổng hợp, chỉ mock OCR.

Tạo video .avi nhỏ bằng cv2, thay easyocr bằng Reader giả trả detection cố định
(Question 1 + Question 2). Mọi bước còn lại (stream video, build_cache, gom ứng viên,
pick, đọc frame theo nhu cầu, refine, cắt, lưu) chạy thật -> bắt được bug pipeline.
"""

import sys
import types
from pathlib import Path

import cv2
import numpy as np
import pytest

from quiz_extractor.extractor import extract_questions


def _make_video(path: Path, frames: int = 12) -> None:
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 30, (480, 1000))
    if not vw.isOpened():
        pytest.skip("Không có codec MJPG để tạo video test")
    for _ in range(frames):
        frame = np.full((1000, 480, 3), 255, np.uint8)
        frame[100:400] = 60  # ít nội dung cho có gì để crop
        vw.write(frame)
    vw.release()


def _box(x, y):
    return [[x, y], [x, y], [x, y], [x, y]]


class _FakeReader:
    def __init__(self, *a, **k):
        pass

    def readtext(self, img, detail=1, paragraph=False):
        # Cố định: Question 1 @y40 và Question 2 @y300, mỗi câu kèm marker grey-box.
        return [
            (_box(25, 40), "Question", 0.9),
            (_box(83, 40), "1", 0.9),
            (_box(25, 70), "Marked out of 1.00", 0.9),
            (_box(25, 300), "Question", 0.9),
            (_box(83, 300), "2", 0.9),
            (_box(25, 330), "Marked out of 1.00", 0.9),
        ]


def _patch_easyocr(monkeypatch):
    fake = types.ModuleType("easyocr")
    fake.Reader = _FakeReader
    monkeypatch.setitem(sys.modules, "easyocr", fake)


def test_extract_questions_end_to_end(tmp_path, monkeypatch):
    _patch_easyocr(monkeypatch)
    video = tmp_path / "v.avi"
    _make_video(video)
    out = tmp_path / "q"

    result = extract_questions(video, out, tmp_path / "c.pkl", step=4, auto_crop=False)

    assert result["saved"] == [1, 2]
    assert result["missing"] == []
    assert (out / "question-01.png").exists()
    assert (out / "question-02.png").exists()


def test_cache_complete_reused_without_ocr(tmp_path, monkeypatch):
    _patch_easyocr(monkeypatch)
    video = tmp_path / "v.avi"
    _make_video(video)
    out = tmp_path / "q"
    cache = tmp_path / "c.pkl"

    extract_questions(video, out, cache, step=4, auto_crop=False)  # build cache
    assert cache.exists()

    # Cache hoàn tất -> lần 2 không cần easyocr (gỡ fake để chứng minh không OCR lại).
    monkeypatch.delitem(sys.modules, "easyocr", raising=False)
    result = extract_questions(video, out, cache, step=4, auto_crop=False)
    assert result["saved"] == [1, 2]


def test_extract_questions_keeps_non_question_png(tmp_path, monkeypatch):
    _patch_easyocr(monkeypatch)
    video = tmp_path / "v.avi"
    _make_video(video)
    out = tmp_path / "q"
    out.mkdir()
    (out / "logo.png").write_bytes(b"keep")
    (out / "question-99.png").write_bytes(b"stale")

    result = extract_questions(video, out, tmp_path / "c.pkl", step=4, auto_crop=False)

    assert result["saved"] == [1, 2]
    assert (out / "logo.png").exists()
    assert not (out / "question-99.png").exists()


def test_extract_questions_raises_when_image_write_fails(tmp_path, monkeypatch):
    _patch_easyocr(monkeypatch)
    video = tmp_path / "v.avi"
    _make_video(video)
    monkeypatch.setattr("quiz_extractor.extractor.cv2.imwrite", lambda *a, **k: False)

    with pytest.raises(SystemExit, match="Không ghi được ảnh"):
        extract_questions(video, tmp_path / "q", tmp_path / "c.pkl", 4, auto_crop=False)
