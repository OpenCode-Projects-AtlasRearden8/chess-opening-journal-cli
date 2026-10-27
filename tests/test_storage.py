import json
import os

import pytest

from chess_opening_journal.storage import (
    JournalError,
    backup_journal,
    backups_dir_for,
    fresh_journal,
    list_backups,
    load_journal,
    normalize_journal,
    save_journal,
)


def test_fresh_journal_shape():
    journal = fresh_journal()
    assert journal["version"] == 1
    assert journal["games"] == []
    assert journal["repertoire"] == []
    assert journal["settings"]["max_backups"] == 30
    assert journal["settings"]["player_name"] == ""


def test_save_and_load_roundtrip(tmp_path):
    path = str(tmp_path / "journal.json")
    journal = fresh_journal()
    journal["games"].append({"id": "abc12345", "opening_family": "Sicilian Defense"})
    save_journal(journal, path)
    loaded = load_journal(path)
    assert loaded["games"][0]["id"] == "abc12345"
    assert loaded["games"][0]["opening_family"] == "Sicilian Defense"
    assert os.path.exists(path)


def test_load_missing_file_returns_fresh(tmp_path):
    loaded = load_journal(str(tmp_path / "nope.json"))
    assert loaded["games"] == []
    assert loaded["repertoire"] == []


def test_corrupt_json_raises_journalerror_with_hint(tmp_path):
    path = tmp_path / "journal.json"
    path.write_text("{ not json", encoding="utf-8")
    with pytest.raises(JournalError) as excinfo:
        load_journal(str(path))
    assert "backup" in str(excinfo.value)


def test_normalize_journal_resets_missing_keys():
    journal = normalize_journal({"games": [{"id": 1}]})
    assert journal["repertoire"] == []
    assert journal["settings"]["player_name"] == ""
    with pytest.raises(JournalError):
        normalize_journal({"games": "not a list"})
    with pytest.raises(JournalError):
        normalize_journal([1, 2, 3])


def test_backup_journal_creates_and_prunes(tmp_path):
    path = str(tmp_path / "journal.json")
    journal = fresh_journal()
    save_journal(journal, path)
    for index in range(35):
        backup_journal(path)
    backups = list_backups(path)
    assert len(backups) == 30
    backup_dir = backups_dir_for(path)
    assert os.path.isdir(backup_dir)
    first = backups[0]
    assert os.path.basename(first).startswith("journal.json.")
    assert first.endswith(".bak")


def test_backup_journal_without_file_returns_none(tmp_path):
    assert backup_journal(str(tmp_path / "nothing.json")) is None
