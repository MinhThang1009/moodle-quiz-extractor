# Changelog

Tất cả thay đổi đáng chú ý của dự án được ghi ở đây.

Định dạng theo [Keep a Changelog](https://keepachangelog.com/vi/1.1.0/),
phiên bản tuân thủ [Semantic Versioning](https://semver.org/lang/vi/).

## [1.1.2](https://github.com/MinhThang1009/moodle-quiz-extractor/compare/v1.1.1...v1.1.2) (2026-06-29)


### Documentation

* cập nhật README theo tính năng hiện tại ([#10](https://github.com/MinhThang1009/moodle-quiz-extractor/issues/10)) ([17cc76a](https://github.com/MinhThang1009/moodle-quiz-extractor/commit/17cc76ab2fdc14203f0aaf0cddca32c3944dd39d))

## [1.1.1](https://github.com/MinhThang1009/moodle-quiz-extractor/compare/v1.1.0...v1.1.1) (2026-06-29)


### Documentation

* dọn block [Unreleased] thủ công trùng release-please ([#7](https://github.com/MinhThang1009/moodle-quiz-extractor/issues/7)) ([203adb0](https://github.com/MinhThang1009/moodle-quiz-extractor/commit/203adb00ea6dbe2f1b833b643d8e5fa027ab64f5))
* đồng bộ tài liệu với code và quy trình hiện tại ([#9](https://github.com/MinhThang1009/moodle-quiz-extractor/issues/9)) ([20372d0](https://github.com/MinhThang1009/moodle-quiz-extractor/commit/20372d0ec905c13fd641aa44e24dcdf61ee0e8b2))

## [1.1.0](https://github.com/MinhThang1009/moodle-quiz-extractor/compare/v1.0.0...v1.1.0) (2026-06-29)

### Features

* **ocr:** stream tiến độ OCR + cache resume thông minh ([8c7f4d7](https://github.com/MinhThang1009/moodle-quiz-extractor/commit/8c7f4d7822ef37c702c7f443fc9bcdaf1322426a))
* streaming/memory, GPU auto-detect, --config, cảnh báo thiếu, integration test ([a1545ae](https://github.com/MinhThang1009/moodle-quiz-extractor/commit/a1545ae58382733d85ef7f08bf4b419c44956a60))
* **to_text:** OCR ảnh câu sang text (engine easyocr + llm) ([e41ba69](https://github.com/MinhThang1009/moodle-quiz-extractor/commit/e41ba69fc924b80bf9741fb928691a9a599ad805))
* tự nhận diện vùng nội dung + tiến độ watcher, hỗ trợ layout desktop ([ff87f5b](https://github.com/MinhThang1009/moodle-quiz-extractor/commit/ff87f5b242156eebe6298baae855167144a62168))
* **watch:** watcher tự chạy pipeline khi có video mới ([1467bc5](https://github.com/MinhThang1009/moodle-quiz-extractor/commit/1467bc5349052d414c79ac31db3abe9320c826ba))
* **watch:** xử lý nhiều video song song (--workers N) ([33165ed](https://github.com/MinhThang1009/moodle-quiz-extractor/commit/33165eda280f0e639ab8d9f975f3bbeef543f169))

### Bug Fixes

* **crop:** đáp án cuối bị cắt do mép dưới content quá bảo thủ ([8b744b5](https://github.com/MinhThang1009/moodle-quiz-extractor/commit/8b744b533e5406a72f61f4a0c96117735009679f))
* **extractor:** câu dài/cuối trang không bị cắt đáp án ([def6878](https://github.com/MinhThang1009/moodle-quiz-extractor/commit/def6878b47717cd4ae216dcf1e389f9e3a61d79a))
* **ocr:** nhiều câu mất dòng "Question N" (Flag question + anchor cấu trúc) ([a0df16f](https://github.com/MinhThang1009/moodle-quiz-extractor/commit/a0df16fda169cabcb8ee6f658506d127f624a512))

### Performance Improvements

* **ocr:** bỏ qua frame tĩnh (giảm ~49% lượt OCR, không sót câu) ([3f728fd](https://github.com/MinhThang1009/moodle-quiz-extractor/commit/3f728fd8e28cbee6054f5eb6fef6f212a3ce9e57))

### Documentation

* xóa ảnh demo.png và bỏ section Demo trong README ([6747aa2](https://github.com/MinhThang1009/moodle-quiz-extractor/commit/6747aa2b91e852604559a1b7ae87c17878822d3c))

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

[1.0.0]: https://github.com/MinhThang1009/moodle-quiz-extractor/releases/tag/v1.0.0
