import json
import os
import shutil

import pytest

from chess_opening_journal.cli import main

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture()
def env_tmp(tmp_path, monkeypatch, capsys):
    journal_path = tmp_path / "journal.json"
    return journal_path


def _run(env_tmp, *argv):
    code = main(["--journal", str(env_tmp)] + list(argv))
    return code


def _output(capsys):
    captured = capsys.readouterr()
    return captured.out


def test_configure_then_add_file(tmp_path, env_tmp, capsys):
    assert _run(env_tmp, "configure", "--player", "Dylan Asdale") == 0
    assert "Dylan Asdale" in _output(capsys)
    assert _run(
        env_tmp,
        "add",
        "--note",
        "felt sharp",
        os.path.join(FIXTURES, "games_mix.pgn"),
    ) == 0
    out = _output(capsys)
    assert "added 4 game" in out
    assert os.path.exists(str(env_tmp))
    with open(str(env_tmp), encoding="utf-8") as fh:
        journal = json.load(fh)
    assert len(journal["games"]) == 4
    results = sorted(g["result"] for g in journal["games"])
    assert results == ["draw", "loss", "win", "win"]
    colors = sorted(g["you_color"] for g in journal["games"])
    assert colors == ["black", "white", "white", "white"]
    families = sorted(g["opening_family"] for g in journal["games"])
    assert families == [
        "French Defense",
        "Scandinavian Defense",
        "Sicilian Defense",
        "Sicilian Defense",
    ]
    assert "Auto-backup" in out


def test_add_duplicate_games_skip(tmp_path, env_tmp, capsys):
    _run(env_tmp, "configure", "--player", "Dylan Asdale")
    _run(env_tmp, "add", os.path.join(FIXTURES, "games_dupe.pgn"))
    _run(env_tmp, "add", os.path.join(FIXTURES, "games_dupe.pgn"))
    out = _output(capsys)
    assert "skipped 3 duplicate" in out
    with open(str(env_tmp), encoding="utf-8") as fh:
        journal = json.load(fh)
    assert len(journal["games"]) == 2

def test_log_and_games_listing(tmp_path, env_tmp, capsys):
    _run(env_tmp, "log", "--family", "French Defense", "--result", "draw", "--color", "white",
         "--moves", "e4 e6 d4 d5", "--note", "forgot the b5 push", "--confidence", "2",
         "--date", "2026-10-15")
    out = _output(capsys)
    assert "Logged:" in out
    _run(env_tmp, "games")
    out = _output(capsys)
    assert "French Defense" in out
    assert "draw" in out
    assert "forgot the b5 push" in out
    _run(env_tmp, "games", "--family", "sicilian")
    assert "No games logged" in _output(capsys)


def test_show_and_remove_id_prefixes(tmp_path, env_tmp, capsys, monkeypatch):
    _run(env_tmp, "log", "--family", "English Opening", "--result", "win", "--color", "white")
    out = _output(capsys)
    with open(str(env_tmp), encoding="utf-8") as fh:
        journal = json.load(fh)
    game_id = journal["games"][0]["id"]
    assert "Logged:" in out
    assert _run(env_tmp, "show", game_id) == 0
    out = _output(capsys)
    assert "English Opening" in out
    assert "win" in out
    assert _run(env_tmp, "show", "zzzzzz") == 1
    assert _run(env_tmp, "remove", "zzzzzz", "--yes") == 1
    assert _run(env_tmp, "remove", game_id[:4], "--yes") == 0
    with open(str(env_tmp), encoding="utf-8") as fh:
        journal = json.load(fh)
    assert journal["games"] == []


def test_summary_command(tmp_path, env_tmp, capsys):
    _run(env_tmp, "configure", "--player", "Dylan Asdale")
    _run(env_tmp, "add", os.path.join(FIXTURES, "games_mix.pgn"))
    _run(env_tmp, "summary")
    out = _output(capsys)
    assert "TOTAL" in out
    assert "Sicilian Defense" in out
    assert "50%" in out
    _run(env_tmp, "summary", "--family", "french")
    out = _output(capsys)
    assert "French Defense" in out
    assert "Sicilian Defense" not in out


def test_repertoire_add_list_remove_and_drift(tmp_path, env_tmp, capsys, monkeypatch):
    _run(env_tmp, "configure", "--player", "Dylan Asdale")
    _run(env_tmp, "add", os.path.join(FIXTURES, "games_mix.pgn"))
    assert _run(env_tmp, "drift") == 0
    first = _output(capsys)
    assert "No known lines registered yet" in first
    _run(env_tmp, "repertoire", "add", "--pgn", os.path.join(FIXTURES, "repertoire_white.pgn"), "--side", "white")
    _run(env_tmp, "repertoire", "add", "--pgn", os.path.join(FIXTURES, "repertoire_french_black.pgn"), "--side", "black")
    _run(env_tmp, "repertoire", "list")
    listing = _output(capsys)
    assert "[white]" in listing
    assert "[black]" in listing
    assert "French Defense" in listing
    assert _run(env_tmp, "drift") == 0
    out = _output(capsys)
    assert "Checked 3 game" in out
    assert "Off your lines" in out
    assert "Scandinavian Defense (white)" in out
    assert "at ply 10" in out
    assert "`e5`" in out
    assert "`a6`" in out
    _run(env_tmp, "repertoire", "remove", "1", "--yes")
    assert "Removed known line" in _output(capsys)
    _run(env_tmp, "repertoire", "remove", "9", "--yes")
    assert "No line number" in _output(capsys)


def test_card_export_to_file(tmp_path, env_tmp, capsys):
    _run(env_tmp, "configure", "--player", "Dylan Asdale")
    _run(env_tmp, "add", os.path.join(FIXTURES, "games_mix.pgn"))
    card_path = tmp_path / "practice-card.md"
    assert _run(env_tmp, "card", "--out", str(card_path)) == 0
    assert card_path.exists()
    text = card_path.read_text(encoding="utf-8")
    assert "Practice Focus Card" in text
    assert "## Snapshot" in text
    assert "Dylan" not in text
    _run(env_tmp, "card")
    stdout_card = _output(capsys)
    assert "Practice Focus Card" in stdout_card
    assert "Not checked." in stdout_card


def test_card_with_drift(tmp_path, env_tmp, capsys):
    _run(env_tmp, "configure", "--player", "Dylan Asdale")
    _run(env_tmp, "add", os.path.join(FIXTURES, "games_mix.pgn"))
    _run(env_tmp, "repertoire", "add", "--pgn", os.path.join(FIXTURES, "repertoire_white.pgn"), "--side", "white")
    card_path = tmp_path / "with-drift.md"
    assert _run(env_tmp, "card", "--with-drift", "--out", str(card_path)) == 0
    text = card_path.read_text(encoding="utf-8")
    assert "wandered off" in text


def test_paste_stdin_add(tmp_path, env_tmp, capsys, monkeypatch):
    _run(env_tmp, "configure", "--player", "Dylan Asdale")
    capsys.readouterr()
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(
        '[Event "pasted"]\n[White "Dylan Asdale"]\n[Black "Riv"]\n[Result "1-0"]\n\n'
        '1. e4 c5 2. Nf3 d6 1-0\n'))
    assert _run(env_tmp, "add", "-") == 0
    out = _output(capsys)
    assert "added 1 game" in out
    with open(str(env_tmp), encoding="utf-8") as fh:
        journal = json.load(fh)
    game = journal["games"][0]
    assert game["source"] == "pasted"
    assert game["result"] == "win"


def test_add_missing_file_reports_readable_error(tmp_path, env_tmp, capsys):
    code = _run(env_tmp, "add", os.path.join(FIXTURES, "missing.pgn"))
    out = _output(capsys)
    assert code == 1
    assert "could not read" in out


def test_add_no_games(tmp_path, env_tmp, capsys):
    empty_pgn = tmp_path / "empty.pgn"
    empty_pgn.write_text('[White "A"]\n[Black "B"]\n[Result "*"]\n\n', encoding="utf-8")
    code = _run(env_tmp, "add", str(empty_pgn))
    out = _output(capsys)
    assert code == 0
    assert "No games found" in out


def test_opening_tags_defence_and_eco(tmp_path, env_tmp, capsys):
    _run(env_tmp, "configure", "--player", "Dylan Asdale")
    _run(env_tmp, "add", os.path.join(FIXTURES, "games_opening_tags.pgn"))
    with open(str(env_tmp), encoding="utf-8") as fh:
        journal = json.load(fh)
    game = journal["games"][0]
    assert game["opening_family"] == "French Defense"
    assert game["eco"] == "C02"
    assert game["you_color"] == "black"
    assert game["result"] == "win"


def test_fen_fixture_flags_custom_family(tmp_path, env_tmp, capsys):
    _run(env_tmp, "configure", "--player", "Dylan Asdale")
    _run(env_tmp, "add", os.path.join(FIXTURES, "games_fen.pgn"))
    with open(str(env_tmp), encoding="utf-8") as fh:
        journal = json.load(fh)
    game = journal["games"][0]
    assert game["opening_family"] == "Custom start position"


def test_backup_restore_roundtrip(tmp_path, env_tmp, capsys):
    _run(env_tmp, "log", "--family", "English Opening", "--result", "win", "--color", "white")
    _run(env_tmp, "backup")
    listing = _output(capsys)
    assert "No backups yet" in listing
    capsys.readouterr()
    _run(env_tmp, "log", "--family", "King's Fianchetto", "--result", "loss", "--color", "white")
    capsys.readouterr()
    with open(str(env_tmp), encoding="utf-8") as fh:
        before = json.load(fh)
    assert len(before["games"]) == 2
    assert _run(env_tmp, "backup", "--restore", "latest", "--yes") == 0
    out = _output(capsys)
    assert "Restored journal from" in out
    with open(str(env_tmp), encoding="utf-8") as fh:
        after = json.load(fh)
    assert len(after["games"]) == 1
    assert after["games"][0]["opening_family"] == "English Opening"
    backups_dir = os.path.join(os.path.dirname(str(env_tmp)), "backups")
    assert "journal.json.pre-restore.bak" in os.listdir(backups_dir)


def test_backup_restore_prompt_cancels(tmp_path, env_tmp, capsys, monkeypatch):
    _run(env_tmp, "log", "--family", "King's Fianchetto", "--result", "loss", "--color", "white")
    _run(env_tmp, "log", "--family", "Bird's Opening", "--result", "loss", "--color", "white")
    capsys.readouterr()
    monkeypatch.setattr("builtins.input", lambda *a, **k: "no way")
    assert _run(env_tmp, "backup", "--restore", "latest") == 0
    out = _output(capsys)
    assert "Restore cancelled" in out
    with open(str(env_tmp), encoding="utf-8") as fh:
        journal = json.load(fh)
    assert len(journal["games"]) == 2


def test_temp_file_cleanup_after_save(tmp_path, env_tmp, capsys):
    _run(env_tmp, "log", "--family", "English Opening", "--result", "win")
    leftovers = [name for name in os.listdir(tmp_path) if ".tmp-" in name]
    assert leftovers == []
