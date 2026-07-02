"""CLI validators reject invalid numeric arguments before the pipeline runs."""

import pytest

from quiz_extractor.__main__ import build_parser
from quiz_extractor.watch import main as watch_main


def test_main_cli_rejects_non_positive_step():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--step", "0"])
    with pytest.raises(SystemExit):
        parser.parse_args(["--step", "-1"])


@pytest.mark.parametrize(
    "args",
    [
        ["--step", "0"],
        ["--workers", "0"],
        ["--interval", "0"],
        ["--stable", "-1"],
    ],
)
def test_watch_cli_rejects_invalid_numeric_args(monkeypatch, args):
    monkeypatch.setattr("sys.argv", ["quiz_extractor.watch", *args])
    with pytest.raises(SystemExit):
        watch_main()
