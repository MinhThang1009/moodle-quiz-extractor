"""parse_headers: nhận diện/gộp header "Question N", bỏ số nhiễu, sort + dedup."""

from quiz_extractor.geometry import Geom
from quiz_extractor.ocr import parse_headers

GEO = Geom(1040, 480)


def det(text, x, y):
    """Tạo 1 detection giả: (bbox, text, conf). parse_headers chỉ dùng bbox[0]."""
    return ([[x, y], [x, y], [x, y], [x, y]], text, 0.9)


def test_single_token_header():
    assert parse_headers([det("Question 14", 25, 167)], GEO) == [(14, 167)]


def test_split_question_and_number_merged():
    # OCR tách "Question" và "14" thành 2 box cạnh nhau (cùng hàng).
    dets = [det("Question", 25, 167), det("14", 83, 161)]
    assert parse_headers(dets, GEO) == [(14, 167)]


def test_lone_number_ignored():
    # Số trong lưới nav (không có "Question" bên cạnh) bị bỏ.
    assert parse_headers([det("30", 100, 800)], GEO) == []


def test_number_too_far_not_merged():
    # "Question" và số cách quá xa (khác cụm) -> không gộp.
    dets = [det("Question", 25, 167), det("14", 400, 167)]
    assert parse_headers(dets, GEO) == []


def test_orphan_question_number_inferred():
    # OCR đọc "Question" nhưng trượt số "1" -> suy từ câu 2 cách ~1 block phía dưới.
    dets = [det("Question", 25, 185), det("Question 2", 25, 647)]
    assert parse_headers(dets, GEO) == [(1, 185), (2, 647)]


def test_sorted_and_deduped_by_smallest_y():
    dets = [
        det("Question 15", 25, 640),
        det("Question 14", 25, 167),
        det("Question 14", 25, 900),  # trùng số -> giữ y nhỏ nhất
    ]
    assert parse_headers(dets, GEO) == [(14, 167), (15, 640)]
