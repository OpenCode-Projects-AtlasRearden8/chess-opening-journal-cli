import pytest

from chess_opening_journal.card import render_practice_card


def _journal(games=None, repertoire=None):
    return {
        "games": games or [],
        "repertoire": repertoire or [],
        "journal_name": "chip.json",
        "settings": {"player_name": "Dylan Asdale"},
    }


def test_card_without_games_gives_guidance():
    card = render_practice_card(_journal(), drift=None, today="2026-10-27")
    assert "Practice Focus Card" in card
    assert "no logged games" in card


def test_card_sections_and_family_table():
    games = [
        {
            "id": "aaa1",
            "date": "2026-10-20",
            "opening_family": "Sicilian Defense",
            "you_color": "white",
            "result": "loss",
            "note": "rushed morning",
            "confidence": 2,
            "ply_count": 20,
        },
        {
            "id": "bbb2",
            "date": "2026-10-21",
            "opening_family": "French Defense",
            "you_color": "black",
            "result": "draw",
            "note": "",
            "confidence": None,
            "ply_count": 30,
        },
    ]
    card = render_practice_card(_journal(games), drift=None, today="2026-10-27")
    assert "## Snapshot" in card
    assert "| Sicilian Defense | 1 | 0 | 0 | 1 | 0 | 0% |" in card
    assert 'note: "rushed morning"' in card
    assert "Review queue (recent games)" in card
    assert "no engines, no network" in card
    assert "Not checked. Run" in card


def test_card_focus_and_drift_lines():
    games = [
        {"id": "c%d" % i, "date": "2026-10-2%d" % i, "opening_family": "Sicilian Defense",
         "you_color": "white", "result": "loss", "note": "", "confidence": None, "ply_count": 10}
        for i in range(3)
    ]
    repertoire = [
        {
            "id": "line1",
            "family": "Sicilian Defense",
            "side": "white",
            "name": "Najdorf",
            "moves": ["e4", "c5", "Nf3", "d6"],
            "note": "",
        }
    ]
    drift = {
        "checked": 3,
        "skipped_color": 0,
        "off_book": [
            {
                "game": games[0],
                "family": "Sicilian Defense",
                "side": "white",
                "line": repertoire[0],
                "line_name": "Najdorf",
                "ply": 4,
                "expected": "d6",
                "played": "e5",
                "continuation": "d6 d4",
                "matched_prefix": "e4 c5 Nf3",
            }
        ],
        "on_book": [],
        "uncovered": ["French Defense (black)"],
    }
    card = render_practice_card(_journal(games, repertoire), drift=drift, today="2026-10-27")
    assert "Sicilian Defense" in card
    assert "after `e4 c5 Nf3`, you played `e5`" in card
    assert "continues with `d6` and later `d6 d4`" in card
    assert "wandered off" in card
    assert "**Sicilian Defense**" in card


def test_card_drift_not_checked_vs_no_lines_messages():
    games = [
        {"id": "x1", "date": "2026-10-20", "opening_family": "Sicilian Defense",
         "you_color": "white", "result": "win", "note": "", "confidence": None, "ply_count": 6},
    ]
    card_none = render_practice_card(_journal(games), None, today="2026-10-27")
    card_empty_drift = render_practice_card(
        _journal(games), {"checked": 0, "skipped_color": 0, "off_book": [], "on_book": [], "uncovered": []},
        today="2026-10-27",
    )
    assert "Not checked." in card_none
    assert "repertoire add" in card_empty_drift
