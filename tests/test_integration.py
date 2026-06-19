"""Integration: chạy toàn bộ extract_questions (collect -> pick -> crop -> save).

Mock 2 ranh giới I/O (đọc frame + cache OCR) bằng dữ liệu tổng hợp -> không cần video
thật hay easyocr/torch, chạy nhanh trên CI.
"""

from pathlib import Path

import numpy as np

from quiz_extractor import extractor


def _make_frames():
    """3 frame trắng (1000x480), có 2 dải nội dung tối cho 2 câu."""
    frame = np.full((1000, 480, 3), 255, np.uint8)
    frame[107:330, :] = 60  # block câu 1 (full-y)
    frame[447:670, :] = 60  # block câu 2
    return [frame.copy() for _ in range(3)]


def test_extract_questions_end_to_end(tmp_path, monkeypatch):
    frames = _make_frames()
    # headers theo toạ độ CONTENT-CROP (sau khi crop [c_top:c_bot], c_top≈67):
    # câu 1 @ content-y 40, câu 2 @ content-y 380
    data = [(0, [(1, 40), (2, 380)])]
    monkeypatch.setattr(extractor, "load_frames", lambda _p: frames)
    monkeypatch.setattr(extractor, "load_or_build_cache", lambda *a, **k: data)

    out = tmp_path / "questions"
    result = extractor.extract_questions(
        Path("dummy.mp4"), out, tmp_path / "cache.pkl", step=4
    )

    assert result["saved"] == [1, 2]
    assert result["missing"] == []
    assert (out / "question-01.png").exists()
    assert (out / "question-02.png").exists()


def test_missing_reported_when_gap(tmp_path, monkeypatch):
    frames = _make_frames()
    # chỉ thấy câu 1 và câu 3 -> báo thiếu câu 2
    data = [(0, [(1, 40), (3, 380)])]
    monkeypatch.setattr(extractor, "load_frames", lambda _p: frames)
    monkeypatch.setattr(extractor, "load_or_build_cache", lambda *a, **k: data)

    result = extractor.extract_questions(
        Path("dummy.mp4"), tmp_path / "q", tmp_path / "c.pkl", step=4
    )

    assert result["saved"] == [1, 3]
    assert result["missing"] == [2]
