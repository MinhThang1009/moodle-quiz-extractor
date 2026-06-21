# Changelog

Tất cả thay đổi đáng chú ý của dự án được ghi ở đây.

Định dạng theo [Keep a Changelog](https://keepachangelog.com/vi/1.1.0/),
phiên bản tuân thủ [Semantic Versioning](https://semver.org/lang/vi/).

## [Unreleased]

### Added
- Lệnh `quiz_extractor.to_text`: OCR ảnh câu sang text có cấu trúc (`questions.json` + `.md`),
  2 engine — `easyocr` (offline, mặc định) và `llm` (Anthropic vision, chính xác hơn).
- Lệnh `quiz_extractor.watch`: watcher (polling) tự chạy pipeline khi có video mới trong
  `data/` -> `output/<tên-video>/`; cờ `--to-text`, `--once`, `--reprocess`.
- Cờ `--config <json>` (mọi lệnh): override marker template + tỉ lệ layout tại runtime ->
  chạy được Moodle theme/ngôn ngữ khác (vd "Câu hỏi N") hoặc quay desktop, không sửa code.
- **GPU auto-detect**: easyocr tự dùng CUDA/MPS nếu có (nhanh hơn nhiều), fallback CPU.
- Cảnh báo (WARNING) nổi bật khi **thiếu câu** hoặc câu **thiếu nội dung** (ảnh quá ngắn).
- Integration test thật: chạy `extract_questions` trên video tổng hợp (chỉ mock OCR).
- `quiz_extractor.watch --workers N`: xử lý nhiều video **song song** (process pool, mỗi
  worker giới hạn thread để khỏi tranh CPU); vẫn bỏ qua video đã có kết quả.

### Changed
- OCR build_cache: in tiến độ dạng stream (1 dòng cập nhật tại chỗ) + tạo thư mục output ngay.
- **Cache resume thông minh**: lưu cache tăng dần (mỗi 40 frame, ghi nguyên tử), Ctrl+C giữa
  chừng -> chạy lại tiếp tục đúng chỗ thay vì OCR lại từ đầu.
- **Tiết kiệm RAM**: stream video thay vì nạp toàn bộ frame (OCR ~1 frame; extract chỉ đọc
  frame cần) -> không OOM với video dài. Cache lưu kèm độ nét từng block để selection khỏi đọc lại.
- **Bỏ qua frame tĩnh**: frame trùng nội dung frame OCR gần nhất (diff < `STILL_DIFF`) thì không
  OCR lại -> nhanh hơn nhiều ở đoạn màn hình đứng yên. So với anchor (không phải frame liền
  trước) nên cuộn chậm tích lũy vẫn được OCR -> không sót câu.

### Fixed
- Câu dài/cuối trang không còn bị cắt đáp án: tail chọn frame header cao nhất (đủ chỗ cả block).
- Đáp án cuối (vd câu 40 đáp án d) không còn bị cắt dòng chót: mép dưới content (`F_CONTENT_BOT`
  0.827 → 0.856) quá bảo thủ nên cắt luôn dòng cuối nội dung web; nới tới ngay trên overlay
  browser ("Tóm tắt trang"/nav bar) -> lấy trọn nội dung mà không dính thanh điều hướng.
- **Nhiều câu mất dòng "Question N"**: chữ "question" trong "Flag question" bị nhận nhầm thành
  header (rồi gán số) → chọn nhầm frame có header bị cắt. Sửa 2 lớp: (1) **anchor cấu trúc** —
  "Question" chỉ là header thật nếu có marker grey-box (Marked out of/Not yet) ngay dưới
  (`F_HEAD_SPAN`); (2) chỉ nhận "Question" ở mép trái (`F_HEAD_XLEFT`).

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

[Unreleased]: https://github.com/MinhThang1009/moodle-quiz-extractor/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/MinhThang1009/moodle-quiz-extractor/releases/tag/v1.0.0
