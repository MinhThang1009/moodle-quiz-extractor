"""_collect_candidates: gom ứng viên block theo số câu (logic thuần)."""

from quiz_extractor.extractor import _collect_candidates


def test_collect_candidates_pairs_and_tail():
    # frame 0: câu 1 (y=100) + câu 2 (y=500); frame 4: câu 2 (y=120, dưới cùng)
    data = [(0, [(1, 100), (2, 500)]), (4, [(2, 120)])]
    cand = _collect_candidates(data, height=800)

    # Câu 1 có header kế (câu 2) -> block [100, 500], has_next=True
    assert cand[1] == [(0, 100, 500, True)]

    # Câu 2: ở frame 0 là header dưới cùng -> y2=height(800), has_next=False
    #        ở frame 4 cũng dưới cùng -> y2=800, has_next=False
    assert (0, 500, 800, False) in cand[2]
    assert (4, 120, 800, False) in cand[2]


def test_collect_candidates_empty():
    assert _collect_candidates([], height=800) == {}
