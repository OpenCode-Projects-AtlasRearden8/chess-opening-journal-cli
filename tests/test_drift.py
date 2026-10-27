import pytest

from chess_opening_journal.drift import common_prefix_len, drift_report, pending_continuation


def _game(gid, family, side, moves, date="2026-10-24"):
    return {
        "id": gid,
        "date": date,
        "opening_family": family,
        "you_color": side,
        "moves": moves,
    }


def _line(lid, family, side, moves, name=None):
    return {"id": lid, "family": family, "side": side, "moves": moves, "name": name or lid}


def test_common_prefix_len():
    assert common_prefix_len([], []) == 0
    assert common_prefix_len(["e4"], ["e4", "c5"]) == 1
    assert common_prefix_len(["e4", "c5", "Nf3"], ["e4", "c5", "d4"]) == 2
    assert common_prefix_len(["e4", "e5"], ["e4", "c5"]) == 1


def test_pending_continuation_count_default():
    assert pending_continuation(["a", "b", "c", "d"], 1) == "b c d"
    assert pending_continuation(["a"], 1) == ""


def test_off_book_row_details():
    repertoire = [
        _line("l1", "Sicilian Defense", "white", ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "a6"]),
    ]
    games = [
        _game("g1", "Sicilian Defense", "white", ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "e5"]),
    ]
    report = drift_report(games, repertoire)
    assert report["checked"] == 1
    assert report["skipped_color"] == 0
    assert len(report["off_book"]) == 1
    row = report["off_book"][0]
    assert row["game"]["id"] == "g1"
    assert row["ply"] == 10
    assert row["expected"] == "a6"
    assert row["played"] == "e5"
    assert row["matched_prefix"] == "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3"
    assert row["continuation"] == "a6"


def test_on_book_when_game_runs_past_line_end():
    repertoire = [
        _line("l1", "French Defense", "black", ["e4", "e6", "d4", "d5", "Nc3"]),
    ]
    games = [
        _game("g2", "French Defense", "black", ["e4", "e6", "d4", "d5", "Nc3", "Nf6", "e5"]),
    ]
    report = drift_report(games, repertoire)
    assert report["off_book"] == []
    assert len(report["on_book"]) == 1


def test_uncovered_family_and_unknown_color_skip():
    repertoire = [
        _line("l1", "French Defense", "black", ["e4", "e6", "d4", "d5", "Nc3"]),
    ]
    games = [
        _game("g3", "Scandinavian Defense", "white", ["e4", "d5"]),
        _game("g4", "French Defense", "unknown", ["e4", "e6"]),
    ]
    report = drift_report(games, repertoire)
    assert report["checked"] == 0
    assert report["skipped_color"] == 1
    assert not report["off_book"]
    assert report["uncovered"] == ["Scandinavian Defense (white)"]


def test_best_matching_line_is_longest_prefix():
    repertoire = [
        _line("short", "Sicilian Defense", "white", ["e4", "c5"]),
        _line("long", "Sicilian Defense", "white", ["e4", "c5", "Nf3", "d6"]),
    ]
    games = [
        _game("g5", "Sicilian Defense", "white", ["e4", "c5", "Nf3", "e5", "d4", "cxd4", "Nxd4", "Qc7"]),
    ]
    report = drift_report(games, repertoire)
    assert [row["line"]["id"] for row in report["off_book"]] == ["long"]
    row = report["off_book"][0]
    assert row["ply"] == 4
    assert row["expected"] == "d6"
