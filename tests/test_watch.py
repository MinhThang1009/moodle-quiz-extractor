"""watch._outputs ánh xạ video -> thư mục kết quả (logic thuần)."""

from pathlib import Path

from quiz_extractor.watch import _outputs


def test_outputs_paths():
    out_dir, questions_dir, cache = _outputs(Path("output"), Path("data/1.mp4"))
    assert out_dir == Path("output/1")
    assert questions_dir == Path("output/1/questions")
    assert cache == Path("output/1/ocr_cache.pkl")


def test_outputs_uses_video_stem():
    out_dir, _, _ = _outputs(Path("out"), Path("/x/Bai Quiz 2.mp4"))
    assert out_dir == Path("out/Bai Quiz 2")
