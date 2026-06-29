# Changelog

Tất cả thay đổi đáng chú ý của dự án được ghi ở đây.

Định dạng theo [Keep a Changelog](https://keepachangelog.com/vi/1.1.0/),
phiên bản tuân thủ [Semantic Versioning](https://semver.org/lang/vi/).

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

## [Unreleased]

### Added
- **Auto-detect vùng nội dung** (mặc định bật): tự suy `F_CONTENT_TOP/BOT` từ video bằng cách
  phân tích cặp frame "cuộn thuần" (chrome/status bar/overlay đứng yên, nội dung dịch) -> chạy
  thẳng cả layout khác hẳn (điện thoại dọc ↔ desktop ngang) mà không cần `--config`. Detect
  bất thường -> fallback tỉ lệ cố định. Tắt bằng `--no-auto-crop`.
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
- Header không còn bị xén nửa trên: `_pick_source` bỏ frame có header sát mép content
  (header vắt qua mép trên -> cắt mất chữ), ưu tiên frame header nguyên vẹn.
- Đệm trên ảnh thoáng hơn, bao trọn viền info box: `F_TOP_MARGIN` 0.006 → 0.03 (đủ chừa
  viền khung "Question N" + khoảng trắng phía trên, không dính sát mép).
- Hỗ trợ layout desktop 2 cột: nới `F_HEAD_SPAN` 0.13 → 0.20 (header→marker giãn hơn theo
  tỉ lệ H ở màn ngang) để header không bị anchor loại nhầm. Vẫn nhỏ hơn khoảng cách tới
  marker câu kế ở layout dọc nên không sinh header giả.
- Bỏ "Question 0" giả (header bị crop xén -> OCR đọc số thành 0): chỉ nhận số câu >= 1.
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
