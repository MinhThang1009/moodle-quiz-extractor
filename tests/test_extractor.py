"""_collect_candidates + _pick_source: logic thuần (không đọc frame)."""

from quiz_extractor.extractor import _collect_candidates, _pick_source
from quiz_extractor.geometry import Geom


def test_collect_candidates_pairs_and_tail():
    # data: (idx, [(num, y, sharp)]). f0: câu1@100 + câu2@500; f4: câu2@120 (cuối)
    data = [(0, [(1, 100, 9.0), (2, 500, 5.0)]), (4, [(2, 120, 7.0)])]
    cand = _collect_candidates(data, height=800)

    # Câu 1 có header kế -> (idx, y1, y2, has_next, sharp)
    assert cand[1] == [(0, 100, 500, True, 9.0)]
    # Câu 2: cả 2 frame đều là header dưới cùng -> y2=height, has_next=False
    assert (0, 500, 800, False, 5.0) in cand[2]
    assert (4, 120, 800, False, 7.0) in cand[2]


def test_collect_candidates_empty():
    assert _collect_candidates([], height=800) == {}


def test_pick_source_clean_picks_sharpest():
    geo = Geom(800, 480)  # pair_min=240, pair_max=592
    # 2 ứng viên câu có header kế, block 300px hợp lệ; chọn cái sharp cao hơn (frame 4)
    cands = [(0, 50, 350, True, 3.0), (4, 50, 350, True, 8.0)]
    assert _pick_source(cands, geo) == (4, 50, 350)


def test_pick_source_tail_picks_highest_header():
    geo = Geom(800, 480)
    # không có header kế -> chọn y1 nhỏ nhất (chỗ trống nhiều nhất)
    cands = [(0, 600, 800, False, 5.0), (8, 90, 800, False, 2.0)]
    assert _pick_source(cands, geo) == (8, 90, 800)


def test_pick_source_bo_qua_header_sat_mep():
    geo = Geom(800, 480)  # top_margin = 16
    # header sát mép (y1=3, sẽ bị xén) bị bỏ -> chọn frame header nguyên vẹn (y1=250)
    cands = [(0, 3, 800, False, 9.0), (8, 250, 800, False, 2.0)]
    assert _pick_source(cands, geo) == (8, 250, 800)


def test_pick_source_tail_fallback_khi_moi_header_sat_mep():
    geo = Geom(800, 480)
    # mọi frame đều sát mép -> đành chọn y1 nhỏ nhất (không còn lựa chọn nào nguyên vẹn)
    cands = [(0, 5, 800, False, 9.0), (8, 10, 800, False, 2.0)]
    assert _pick_source(cands, geo) == (0, 5, 800)


def test_pick_source_clean_sat_mep_roi_xuong_tail():
    geo = Geom(800, 480)  # top_margin=24, pair_min=240
    # clean candidate (frame 0) header kế hợp lệ nhưng y1=5 < 24 -> bị loại khỏi clean;
    # rơi xuống tail, chọn frame có header nguyên vẹn (frame 4, y1=250)
    cands = [(0, 5, 300, True, 9.0), (4, 250, 800, False, 2.0)]
    assert _pick_source(cands, geo) == (4, 250, 800)
