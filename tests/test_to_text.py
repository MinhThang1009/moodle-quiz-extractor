"""parse_question: tách câu hỏi + 4 đáp án từ các dòng OCR (logic thuần, không OCR)."""

from quiz_extractor.to_text import parse_question


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
