"""parse_headers: nhận diện/gộp header "Question N", bỏ số nhiễu, sort + dedup."""

import pickle

from quiz_extractor.geometry import Geom
from quiz_extractor.ocr import (
    _is_complete,
    _matches,
    _read_cache,
    _save_cache,
    parse_headers,
)

GEO = Geom(1040, 480)


def test_cache_roundtrip_and_resume_flags(tmp_path):
    cp = tmp_path / "c.pkl"
    _save_cache(cp, GEO, 4, [(0, [(1, 10)])], next_idx=8, complete=False)
    cached = _read_cache(cp)
    assert _matches(cached, GEO, 4)
    assert not _is_complete(cached) and cached["next"] == 8  # cache dở -> resume
    _save_cache(cp, GEO, 4, [(0, [(1, 10)])], next_idx=999, complete=True)
    assert _is_complete(_read_cache(cp))


def test_legacy_cache_treated_complete(tmp_path):
    cp = tmp_path / "c.pkl"
    with open(cp, "wb") as fh:  # cache cũ: không có khóa next/complete
        pickle.dump({"h": 1040, "w": 480, "step": 4, "data": []}, fh)
    assert _is_complete(_read_cache(cp))


def test_read_cache_missing_returns_none(tmp_path):
    assert _read_cache(tmp_path / "nope.pkl") is None


def det(text, x, y):
    """Tạo 1 detection giả: (bbox, text, conf). parse_headers chỉ dùng bbox[0]."""
    return ([[x, y], [x, y], [x, y], [x, y]], text, 0.9)


def mark(y):
    """Dòng marker grey-box ("Marked out of") ngay dưới header (anchor cấu trúc)."""
    return det("Marked out of 1.00", 25, y)


def test_single_token_header():
    dets = [det("Question 14", 25, 167), mark(200)]
    assert parse_headers(dets, GEO) == [(14, 167)]


def test_split_question_and_number_merged():
    # OCR tách "Question" và "14" thành 2 box cạnh nhau (cùng hàng).
    dets = [det("Question", 25, 167), det("14", 83, 161), mark(200)]
    assert parse_headers(dets, GEO) == [(14, 167)]


def test_header_without_marker_rejected():
    # "Question 14" mà KHÔNG có marker grey-box dưới -> không phải header thật.
    assert parse_headers([det("Question 14", 25, 167)], GEO) == []


def test_lone_number_ignored():
    # Số trong lưới nav (không có "Question" bên cạnh) bị bỏ.
    assert parse_headers([det("30", 100, 800)], GEO) == []


def test_number_too_far_not_merged():
    # "Question" và số cách quá xa (khác cụm) -> không gộp.
    dets = [det("Question", 25, 167), det("14", 400, 167), mark(200)]
    assert parse_headers(dets, GEO) == []


def test_flag_question_not_treated_as_header():
    # "Flag question" (chữ "question" ở x phải, không có marker dưới) KHÔNG là header.
    dets = [
        det("Flag", 43, 21),
        det("question", 73, 21),
        det("Question", 25, 200),  # header thật ở mép trái
        det("2", 83, 200),
        mark(232),
    ]
    assert parse_headers(dets, GEO) == [(2, 200)]


def test_orphan_question_number_inferred():
    # OCR đọc "Question" nhưng trượt số "1" -> suy từ câu 2 cách ~1 block phía dưới.
    dets = [det("Question", 25, 185), mark(218), det("Question 2", 25, 647), mark(680)]
    assert parse_headers(dets, GEO) == [(1, 185), (2, 647)]


def test_sorted_and_deduped_by_smallest_y():
    dets = [
        det("Question 15", 25, 640),
        mark(673),
        det("Question 14", 25, 167),
        mark(200),
        det("Question 14", 25, 900),  # trùng số -> giữ y nhỏ nhất
        mark(933),
    ]
    assert parse_headers(dets, GEO) == [(14, 167), (15, 640)]
