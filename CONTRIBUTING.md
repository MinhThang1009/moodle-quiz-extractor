# Đóng góp cho moodle-quiz-extractor

Cảm ơn bạn đã quan tâm! Tài liệu này mô tả quy trình đóng góp. Khi tham gia, vui lòng
tuân thủ [Quy tắc ứng xử](CODE_OF_CONDUCT.md).

## Thiết lập môi trường

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  •  Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"         # công cụ dev: black, ruff, mypy, pytest
```

## Quy chuẩn code

- **Format**: [black](https://black.readthedocs.io/) (`line-length = 88`).
- **Lint**: [ruff](https://docs.astral.sh/ruff/).
- Comment/docstring/thông báo: **tiếng Việt**. Tên biến/hàm/class/file: **English**, `snake_case`.
- Trước khi mở PR:

  ```bash
  black .
  ruff check .
  mypy quiz_extractor
  pytest
  python -m quiz_extractor --help    # smoke test
  ```

## Commit

Theo [Conventional Commits](https://www.conventionalcommits.org/), **subject tiếng Việt**:

```
feat(ocr): thêm hỗ trợ template Azota
fix(extractor): sửa cắt hụt câu cuối trang
```

Type: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`.

## Pull Request

1. Fork → tạo branch `feat/...` hoặc `fix/...`.
2. Đảm bảo `black .` và `ruff check .` sạch (CI sẽ kiểm tra).
3. Viết commit theo Conventional Commits — release-please tự sinh `CHANGELOG.md`, không cần sửa tay.
4. Mô tả PR rõ: làm gì, vì sao, cách test.

## Báo lỗi / đề xuất

Mở [issue](../../issues) theo template có sẵn. Với lỗi trích xuất, nêu rõ độ phân giải
video, template LMS, và mô tả câu bị sót/sai.
