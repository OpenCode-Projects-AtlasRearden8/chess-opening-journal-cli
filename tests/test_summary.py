import pytest

from chess_opening_journal.summary import family_rows, focus_families, overall_row, recent_games


def _row(family, wins=0, draws=0, losses=0, unknown=0):
    games = []
    games += [{"opening_family": family, "result": "win"} for _ in range(wins)]
    games += [{"opening_family": family, "result": "draw"} for _ in range(draws)]
    games += [{"opening_family": family, "result": "loss"} for _ in range(losses)]
    games += [{"opening_family": family, "result": "unknown"} for _ in range(unknown)]
    return games


def test_family_rows_counts_and_scores():
    games = _row("Sicilian Defense", wins=1, draws=1, losses=1)
    games += _row("French Defense", losses=2)
    games += [{"opening_family": "French Defense", "result": "unknown"}]
    rows = {row["family"]: row for row in family_rows(games)}
    sic = rows["Sicilian Defense"]
    assert sic["games"] == 3 and sic["decided"] == 3
    assert sic["score"] == 50.0
    french = rows["French Defense"]
    assert french["games"] == 3 and french["decided"] == 2
    assert french["score"] == 0.0
    assert len(family_rows(games)) == 2


def test_overall_row_totals():
    games = _row("A", wins=2, draws=1, losses=1, unknown=2)
    overall = overall_row(games)
    assert overall["games"] == 6
    assert overall["decided"] == 4
    assert overall["unknown"] == 2
    assert overall["score"] == 62.5


def test_focus_families_weakest_first_with_minimum():
    games = _row("Sicilian Defense", wins=1, draws=1, losses=3)
    games += _row("French Defense", wins=2, losses=1)
    games += _row("Caro-Kann Defense", losses=1)
    focus = focus_families(games)
    assert [row["family"] for row in focus] == ["Sicilian Defense", "French Defense"]
    assert focus[0]["score"] == 30.0
    assert all(row["decided"] >= 2 for row in focus)


def test_recent_games_orders_by_date_desc():
    games = [
        {"date": "2026-10-01", "added": "2026-10-01T00:00:00", "id": "old"},
        {"date": "2026-10-20", "added": "2026-10-20T00:00:00", "id": "new"},
        {"date": "2026-10-10", "added": "2026-10-10T00:00:00", "id": "mid"},
    ]
    ordered = recent_games(games, 2)
    assert [g["id"] for g in ordered] == ["new", "mid"]