"""detect_content_band: tự suy vùng nội dung (loại chrome tĩnh trên + overlay dưới)."""

import cv2
import numpy as np
import pytest

from quiz_extractor.ocr import detect_content_band

H, W = 1000, 480
CHROME_BOT = 100  # [0:100] = chrome tĩnh (status bar / thanh trình duyệt)
OVERLAY_TOP = 880  # [880:1000] = overlay tĩnh đáy (nav bar)


def _make_scrolling_video(path, frames=40, scroll=8):
    """Video: dải trên/dưới tĩnh, vùng giữa là 'tài liệu' nhiễu cuộn dần (nội dung).

    Dùng nhiễu cố định (không tuần hoàn) để mọi cặp frame cuộn đều khác nhau, tránh
    aliasing (sọc đều + bước cuộn = bội chu kỳ -> 2 frame trùng -> không thấy động).
    """
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 30, (W, H))
    if not vw.isOpened():
        pytest.skip("Không có codec MJPG để tạo video test")
    content_h = OVERLAY_TOP - CHROME_BOT
    rng = np.random.default_rng(0)
    doc = rng.integers(0, 256, (content_h + frames * scroll + 1, W, 3), dtype=np.uint8)
    for k in range(frames):
        frame = np.full((H, W, 3), 255, np.uint8)
        frame[:CHROME_BOT] = 60  # chrome cố định (không đổi giữa các frame)
        frame[OVERLAY_TOP:] = 40  # overlay cố định
        off = k * scroll
        frame[CHROME_BOT:OVERLAY_TOP] = doc[off : off + content_h]
        vw.write(frame)
    vw.release()


def test_detect_band_loai_chrome_va_overlay(tmp_path):
    video = tmp_path / "scroll.avi"
    _make_scrolling_video(video)

    band = detect_content_band(video)

    assert band is not None
    f_top, f_bot = band
    # Vùng nội dung phải nằm gọn giữa chrome (0.1) và overlay (0.88), sai số nhỏ.
    assert 0.08 <= f_top <= 0.18
    assert 0.80 <= f_bot <= 0.90


def test_detect_band_video_tinh_tra_none(tmp_path):
    # Mọi frame giống hệt (không cuộn) -> không suy được vùng -> None (fallback config).
    video = tmp_path / "static.avi"
    vw = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 30, (W, H))
    if not vw.isOpened():
        pytest.skip("Không có codec MJPG để tạo video test")
    for _ in range(20):
        vw.write(np.full((H, W, 3), 255, np.uint8))
    vw.release()

    assert detect_content_band(video) is None
