"""watch._outputs ánh xạ video -> thư mục kết quả (logic thuần)."""

from pathlib import Path

from quiz_extractor.watch import _already_done, _outputs


def test_already_done_true_when_pngs_exist(tmp_path):
    video = tmp_path / "1.mp4"
    qdir = tmp_path / "1" / "questions"
    qdir.mkdir(parents=True)
    (qdir / "question-01.png").write_bytes(b"x")
    assert _already_done(tmp_path, video, reprocess=False) is True
    assert _already_done(tmp_path, video, reprocess=True) is False  # --reprocess


def test_already_done_false_when_no_output(tmp_path):
    assert _already_done(tmp_path, tmp_path / "2.mp4", reprocess=False) is False


def test_outputs_paths():
    out_dir, questions_dir, cache = _outputs(Path("output"), Path("data/1.mp4"))
    assert out_dir == Path("output/1")
    assert questions_dir == Path("output/1/questions")
    assert cache == Path("output/1/ocr_cache.pkl")


def test_outputs_uses_video_stem():
    out_dir, _, _ = _outputs(Path("out"), Path("/x/Bai Quiz 2.mp4"))
    assert out_dir == Path("out/Bai Quiz 2")
