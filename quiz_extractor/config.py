"""Cấu hình: đường dẫn mặc định, marker template Moodle, tỉ lệ layout, hằng số ảnh.

CHỖ DUY NHẤT phụ thuộc template = QUESTION_RE + QUIZ_MARKERS. Đổi LMS khác chỉ cần
sửa 2 thứ đó. Mọi ngưỡng kích thước đều là FRACTION của H/W nên độc lập độ phân giải.
"""

import re
from pathlib import Path

# --- Đường dẫn mặc định (override qua CLI) ---
DEFAULT_VIDEO = Path("data/1.mp4")
DEFAULT_OUTPUT = Path("output/questions")
DEFAULT_CACHE = Path("output/ocr_cache.pkl")
DEFAULT_STEP = 4  # OCR mỗi STEP frame

# --- Template Moodle (chỗ DUY NHẤT phụ thuộc LMS) ---
QUESTION_RE = re.compile(r"question\s*(\d{1,3})", re.I)  # header "Question N"
QUIZ_MARKERS = ("marked out of", "flag question", "not yet answered")
OCR_LANGS = ("vi", "en")

# --- Tỉ lệ layout Moodle (độc lập độ phân giải) ---
# Vùng nội dung web (bỏ status bar trên + thanh browser dưới của screen-recording điện
# thoại). OCR trên vùng này sạch hơn full-frame. Chỉnh nếu chrome máy khác tỉ lệ.
F_CONTENT_TOP = 0.067  # mép trên vùng content (tỉ lệ H)
F_CONTENT_BOT = 0.827  # mép dưới vùng content (tỉ lệ H)
F_PAIR_MIN, F_PAIR_MAX = 0.30, 0.74  # chiều cao block hợp lệ khi có header kế (theo H)
F_HEAD_YTOL = 0.02  # dung sai y khi ghép 'Question'+số (theo H)
F_HEAD_XDIST = 0.31  # khoảng cách x tối đa khi ghép 'Question'+số (theo W)
F_FEAT_X0, F_FEAT_X1 = 0.03, 0.83  # cột tính sharpness, né nút record nổi (theo W)
F_TOP_MARGIN = 0.006  # chừa mép trên header khi cắt (theo H)

# --- Hằng số ảnh (màu tuyệt đối / số frame, mọi độ phân giải) ---
WHITE = 250  # hàng có mean >= WHITE coi là trắng
INK = 235  # pixel < INK coi là có chữ/nội dung
NEIGHBOR_R = 3  # refine sharpness trong ±N frame lân cận
STILL_DIFF = 4.0  # frame lân cận = CÙNG nội dung nếu diff trung bình < ngưỡng
