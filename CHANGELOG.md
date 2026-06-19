# Changelog

Tất cả thay đổi đáng chú ý của dự án được ghi ở đây.

Định dạng theo [Keep a Changelog](https://keepachangelog.com/vi/1.1.0/),
phiên bản tuân thủ [Semantic Versioning](https://semver.org/lang/vi/).

## [Unreleased]

## [1.0.0] - 2026-06-19

### Added
- Trích xuất 1 ảnh/câu từ video screen-recording quiz Moodle, đảm bảo **không sót câu, không lặp ảnh**.
- Thuật toán dense-sample + OCR header `Question N` + gom theo số câu + chọn frame nét nhất theo block.
- Refine frame lân cận (±N) để né motion blur khi cuộn nhanh.
- Cắt block theo ranh giới khoảng trắng (tự bỏ lưới nav / header câu kế).
- Thiết kế **portable**: bám text Moodle + ngưỡng theo tỉ lệ `H/W`, chạy mọi độ phân giải mà không sửa code.
- **Cache OCR** theo (độ phân giải, step) — chạy lại gần như tức thì.
- CLI `python -m quiz_extractor` với các tham số `--video`, `--output`, `--cache`, `--step`, `--force-ocr`, `-v/--verbose`, `-q/--quiet`.
- Bộ test `pytest` cho geometry / parse_headers / imaging / extractor.
- Logging thay cho `print`; single-source version; pre-commit, mypy, CI (lint + test matrix), Dependabot.

### Fixed
- Suy số cho header `Question` khi OCR trượt số đơn lẻ (vd "1") -> không còn sót câu 1.

### Known issues
- Không trích được nội dung **chưa từng được quay** (vd: đáp án câu cuối nếu người quay tắt recording sớm).
- Đoạn cuộn quá nhanh bị motion blur → ảnh chọn ra kém nét hơn.

[Unreleased]: https://example.com/compare/v1.0.0...HEAD
[1.0.0]: https://example.com/releases/tag/v1.0.0
