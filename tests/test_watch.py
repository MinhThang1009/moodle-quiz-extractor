"""watch._outputs ánh xạ video -> thư mục kết quả (logic thuần)."""

import json
from pathlib import Path

from quiz_extractor import config as cfg
from quiz_extractor.watch import _already_done, _outputs, process_video


def test_already_done_true_when_pngs_exist(tmp_path):
    video = tmp_path / "1.mp4"
    qdir = tmp_path / "1" / "questions"
    qdir.mkdir(parents=True)
    (qdir / "question-01.png").write_bytes(b"x")
    assert _already_done(tmp_path, video, reprocess=False) is True
    assert _already_done(tmp_path, video, reprocess=True) is False  # --reprocess


def test_already_done_false_when_no_output(tmp_path):
    assert _already_done(tmp_path, tmp_path / "2.mp4", reprocess=False) is False


def test_already_done_ignores_non_question_png(tmp_path):
    video = tmp_path / "1.mp4"
    qdir = tmp_path / "1" / "questions"
    qdir.mkdir(parents=True)
    (qdir / "logo.png").write_bytes(b"x")
    assert _already_done(tmp_path, video, reprocess=False) is False


def test_outputs_paths():
    out_dir, questions_dir, cache = _outputs(Path("output"), Path("data/1.mp4"))
    assert out_dir == Path("output/1")
    assert questions_dir == Path("output/1/questions")
    assert cache == Path("output/1/ocr_cache.pkl")


def test_outputs_uses_video_stem():
    out_dir, _, _ = _outputs(Path("out"), Path("/x/Bai Quiz 2.mp4"))
    assert out_dir == Path("out/Bai Quiz 2")


def test_process_video_loads_config_before_extracting(tmp_path, monkeypatch):
    config_path = tmp_path / "cfg.json"
    config_path.write_text(
        json.dumps({"QUESTION_RE": r"cau\s*(\d+)"}), encoding="utf-8"
    )
    video = tmp_path / "quiz.mp4"
    video.write_bytes(b"x")

    def fake_extract(video_path, questions_dir, cache, step):
        assert video_path == video
        assert questions_dir == tmp_path / "out" / "quiz" / "questions"
        assert cache == tmp_path / "out" / "quiz" / "ocr_cache.pkl"
        assert step == 4
        assert cfg.QUESTION_RE.pattern == r"cau\s*(\d+)"
        return {"saved": [], "missing": [], "incomplete": []}

    monkeypatch.setattr("quiz_extractor.watch.extract_questions", fake_extract)
    monkeypatch.setattr("quiz_extractor.watch.log_report", lambda result, out: None)

    original = cfg.QUESTION_RE
    try:
        process_video(video, tmp_path / "out", 4, "none", "unused", config_path)
    finally:
        cfg.QUESTION_RE = original
