import pytest

from chess_opening_journal.game import (
    fingerprint_game,
    make_game_record,
    recommended_result_hint,
    resolve_color,
    resolve_date,
    resolve_result,
)
from chess_opening_journal.openings import detect_family


def test_resolve_color_matches_names_case_insensitively():
    headers = {"White": "Dylan Asdale", "Black": "Rival"}
    assert resolve_color(headers, "dylan asdale") == "white"
    assert resolve_color({"White": "Rival", "Black": "Dylan Asdale"}, "DYLAN ASDALE ") == "black"
    assert resolve_color(headers, "Nobody") == "unknown"
    assert resolve_color(headers, "") == "unknown"


def test_resolve_result_by_color():
    assert resolve_result("1-0", "white") == "win"
    assert resolve_result("1-0", "black") == "loss"
    assert resolve_result("0-1", "black") == "win"
    assert resolve_result("0-1", "white") == "loss"
    assert resolve_result("1/2-1/2", "white") == "draw"
    assert resolve_result("*", "white") == "unknown"
    assert resolve_result("1-0", "unknown") == "unknown"


def test_resolve_date_accepts_and_falls_back():
    iso, tag = resolve_date({"Date": "2026.10.24"}, "2026-01-01T0:00:00")
    assert iso == "2026-10-24"
    assert tag == "2026.10.24"
    iso, tag = resolve_date({"Date": "??.??.??"}, "2026-02-03T12:00:00")
    assert iso == "2026-02-03"
    assert tag == "??.??.??"
    iso, tag = resolve_date({}, "2026-02-03T12:00:00")
    assert iso == "2026-02-03"
    assert tag is None


def test_fingerprint_game_is_stable():
    headers = {"White": "Dylan Asdale", "Black": "Rival", "UTCDate": "2026.10.24"}
    fp1 = fingerprint_game(headers, ["e4", "c5"], "1-0")
    fp2 = fingerprint_game(dict(headers), ["e4", "c5"], "1-0")
    assert fp1 == fp2
    fp3 = fingerprint_game(headers, ["e4", "c5", "Nf3"], "1-0")
    assert fp1 != fp3


def test_make_game_record_full_flow_white_win():
    headers = {
        "Event": "Rated blitz",
        "White": "Dylan Asdale",
        "Black": "Rival One",
        "Result": "1-0",
        "Opening": "Sicilian Defense: Najdorf Variation",
        "ECO": "B90",
        "Date": "2026.10.20",
    }
    record = make_game_record(
        headers,
        ["e4", "c5"],
        source="games.pgn",
        player_name="Dylan Asdale",
        date_added_iso="2026-10-27T09:00:00",
        note="sharp confidence",
        confidence=4,
    )
    assert record["you_color"] == "white"
    assert record["result"] == "win"
    assert record["date"] == "2026-10-20"
    assert record["date_tag"] == "2026.10.20"
    assert record["opening_family"] == "Sicilian Defense"
    assert record["opening_name"] == "Sicilian Defense: Najdorf Variation"
    assert record["eco"] == "B90"
    assert record["note"] == "sharp confidence"
    assert record["confidence"] == 4
    assert record["ply_count"] == 2


def test_make_game_record_explicit_overrides_missing_info():
    record = make_game_record(
        {},
        ["e4", "e6"],
        source="log",
        player_name="",
        date_added_iso="2026-10-27T09:00:00",
        explicit_result="loss",
        explicit_color="black",
        family_override="French Defense",
    )
    assert record["you_color"] == "black"
    assert record["result"] == "loss"
    assert record["opening_family"] == "French Defense"
    assert record["note"] == ""
    assert record["confidence"] is None


def test_recommended_result_hint_conditions():
    assert recommended_result_hint("white", "1-0") is None
    hint = recommended_result_hint("unknown", "1-0")
    assert "result" in hint
    hint = recommended_result_hint("white", "nonsense")
    assert "--result" in hint


def test_family_override_and_eco_fallback_in_record():
    record_no_name = make_game_record(
        {"ECO": "C02"},
        ["e4", "e6"],
        source="x",
        player_name="",
        date_added_iso="2026-10-27T00:00:00",
    )
    assert record_no_name["opening_family"] == "French Defense"
    assert record_no_name["eco"] == "C02"
    assert detect_family(["a4"], {"ECO": "A00"}) == "ECO A0x"