import pytest

from chess_opening_journal.openings import detect_family, find_prefix_family


def _f(moves_text, headers=None):
    return detect_family(moves_text.split(), headers or {})


def test_prefix_table_common_families():
    assert _f("e4 c5") == "Sicilian Defense"
    assert _f("e4 e6") == "French Defense"
    assert _f("e4 c6") == "Caro-Kann Defense"
    assert _f("e4 d5") == "Scandinavian Defense"
    assert _f("d4 Nf6 c4 g6") == "King's Indian / Gruenfeld"
    assert _f("d4 Nf6 c4 e6") == "Nimzo-Indian / Queen's Indian"
    assert _f("d4 d5 c4") == "Queen's Gambit"
    assert _f("c4 e5") == "English Opening"
    assert _f("Nf3 d5") == "Reti Opening"
    assert _f("g3") == "King's Fianchetto"


def test_ruy_lopez_beats_generic_open_game():
    assert _f("e4 e5 Nf3 Nc6 Bb5") == "Ruy Lopez"
    assert _f("e4 e5 Nf3") == "Open Game"


def test_pawn_only_fallbacks():
    assert _f("e4 a6") == "King's Pawn (Semi-Open)"
    assert _f("e4 Nh6") == "King's Pawn (Semi-Open)"
    assert _f("a4") == "Other opening"
    assert _f("") == "Other opening"


def test_opening_header_root_wins():
    headers = {"Opening": "Sicilian Defense: Najdorf Variation"}
    assert _f("e4 c5 Nf3", headers) == "Sicilian Defense"
    headers = {"Opening": "French Defence, Advance Variation"}
    assert _f("e4 e6", headers) == "French Defense"


def test_eco_bucket_fallback():
    assert _f("a3", {"ECO": "A00"}) == "ECO A0x"
    assert _f("h4", {"ECO": "K02"}) == "ECO K0x"


def test_custom_start_position_marks_custom():
    headers = {"FEN": "rnbq... w - 0 1", "SetUp": "1"}
    assert _f("e4", headers) == "Custom start position"
    assert _f("e4", {"SetUp": "1"}) == "Custom start position"


def test_prefix_family_helper_direct():
    from chess_opening_journal.openings import find_prefix_family

    assert find_prefix_family(["e4", "c5"]) == "Sicilian Defense"
    assert find_prefix_family(["e4"]) == "King's Pawn (Semi-Open)"