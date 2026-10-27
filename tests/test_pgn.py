import pytest

from chess_opening_journal.pgn import parse_pgn, tokenize_movetext


def _moves(text):
    games = parse_pgn(text)
    assert len(games) == 1
    return games[0]


def test_parse_simple_game():
    text = '[White "Dylan Asdale"]\n[Black "Rival"]\n[Result "1-0"]\n\n1. e4 c5 2. Nf3 d6 1-0'
    game = _moves(text)
    assert game["headers"]["White"] == "Dylan Asdale"
    assert game["headers"]["Result"] == "1-0"
    assert game["moves"] == ["e4", "c5", "Nf3", "d6"]


def test_parse_strips_comments_variations_and_nags():
    text = (
        '[White "You"]\n[Black "Me"]\n\n'
        "1. e4! {great move} (1. d4 {also fine} 2. Nf3) 1... c5 2. Nf3!? {main plan} "
        "2... d6 $1 3. d4 cxd4 4. Nxd4 *"
    )
    games = parse_pgn(text)
    assert len(games) == 1
    assert games[0]["moves"] == ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4"]
    assert games[0]["headers"]["Result"] == "*"


def test_result_token_without_result_header_is_captured():
    text = '[White "A"]\n[Black "B"]\n\n1. d4 d5 2. c4 0-1'
    game = _moves(text)
    assert game["headers"]["Result"] == "0-1"
    assert game["moves"] == ["d4", "d5", "c4"]


def test_glued_move_numbers_and_ellipses():
    text = '[White "A"]\n[Black "B"]\n\n1.e4 1...c5 2.Nf3 2... d6 1-0'
    assert _moves(text)["moves"] == ["e4", "c5", "Nf3", "d6"]


def test_line_comment_and_escapes():
    text = '[White "D. \\"Dash\\" Asdale"]\n[Black "B"]\n\n1. e4 e5 ; quick line comment\n1-0'
    game = _moves(text)
    assert game["headers"]["White"] == 'D. "Dash" Asdale'
    assert game["moves"] == ["e4", "e5"]


def test_multiple_games_and_header_only_filtered():
    text = (
        '[White "A"]\n[Black "B"]\n\n1. e4 e5 1-0\n'
        '[White "C"]\n[Black "D"]\n\n1. d4 0-1\n'
        '[White "E"]\n[Black "F"]\n[Result "*"]\n\n'
    )
    games = parse_pgn(text)
    assert len(games) == 2
    assert games[0]["moves"] == ["e4", "e5"]
    assert games[1]["moves"] == ["d4"]
    assert games[1]["headers"]["Result"] == "0-1"


def test_malformed_text_is_tolerated():
    assert parse_pgn("") == []
    assert parse_pgn("no headers, no moves") == []
    assert parse_pgn('[White "A"]\n\n((( 1. e4') == []


def test_tokenizer_direct():
    moves, result = tokenize_movetext("1. e4 {note} c5 2. Nf3 d6 (2... Nc6) *")
    assert moves == ["e4", "c5", "Nf3", "d6"]
    assert result == "*"


def test_promotion_and_castling_shapes():
    text = '[White "A"]\n[Black "B B"]\n\n1. e4 e5 2. Nf3 Nf6 3. Nxe5 d6 4. Nf3 Nxe4 5. O-O 5... d5 6. exd5 e8=Q+ 6... exd5 1-0'
    game = _moves(text)
    assert "O-O" in game["moves"]
    assert "e8=Q" in game["moves"]
    assert "Nxe5" in game["moves"]
    assert game["moves"][-1] == "exd5"
