import datetime
import json
import os

JOURNAL_NAME = "chess_opening_journal.json"
BACKUP_DIRNAME = "backups"

SETTINGS_DEFAULTS = {"player_name": "", "max_backups": 30}


class JournalError(Exception):
    pass


def now_iso():
    return datetime.datetime.now().isoformat(timespec="seconds")


def timestamp_slug():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S%f")


def fresh_journal():
    return {
        "version": 1,
        "created": now_iso(),
        "updated": now_iso(),
        "settings": dict(SETTINGS_DEFAULTS),
        "games": [],
        "repertoire": [],
    }


def normalize_journal(data):
    if not isinstance(data, dict):
        raise JournalError("journal file does not contain a JSON object")
    journal = fresh_journal()
    journal["version"] = data.get("version", 1)
    journal["created"] = data.get("created", journal["created"])
    journal["updated"] = data.get("updated", journal["updated"])
    settings = data.get("settings", {})
    if not isinstance(settings, dict):
        raise JournalError("journal settings are not an object")
    for key, default in SETTINGS_DEFAULTS.items():
        settings.setdefault(key, default)
    journal["settings"] = settings
    games = data.get("games", [])
    repertoire = data.get("repertoire", [])
    if not isinstance(games, list) or not isinstance(repertoire, list):
        raise JournalError("journal games or repertoire are not lists")
    journal["games"] = games
    journal["repertoire"] = repertoire
    return journal


def load_journal(path):
    if not os.path.exists(path):
        return fresh_journal()
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise JournalError(
            "{} looks corrupted ({}); a backup copy can be restored with: "
            "chess-opening-journal backup --restore latest".format(path, exc)
        ) from exc
    return normalize_journal(data)


def save_journal(journal, path):
    journal["updated"] = now_iso()
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    tmp_path = "{}.tmp-{}".format(path, os.getpid())
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(journal, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp_path, path)
    return path


def backups_dir_for(path):
    return os.path.join(os.path.dirname(os.path.abspath(path)), BACKUP_DIRNAME)


def backup_naming(path):
    base = os.path.basename(path)
    return "{}.{}.bak".format(base, timestamp_slug())


def backup_journal(path, limit=None):
    if not os.path.exists(path):
        return None
    backup_dir = backups_dir_for(path)
    file_name = backup_naming(path)
    os.makedirs(backup_dir, exist_ok=True)
    destination = os.path.join(backup_dir, file_name)
    with open(path, "r", encoding="utf-8") as src, open(destination, "w", encoding="utf-8") as dst:
        dst.write(src.read())
    prune_backups(path, limit)
    return destination


def prune_backups(path, limit=None):
    if limit is None:
        try:
            limit = int(SETTINGS_DEFAULTS.get("max_backups", 30))
        except (TypeError, ValueError):
            limit = 30
    backup_dir = backups_dir_for(path)
    base = os.path.basename(path)
    if not os.path.isdir(backup_dir):
        return []
    names = [n for n in os.listdir(backup_dir) if n.startswith(base) and n.endswith(".bak")]
    names.sort()
    excess = names[:-limit] if len(names) > limit else []
    for name in excess:
        try:
            os.remove(os.path.join(backup_dir, name))
        except OSError:
            pass
    return excess


def list_backups(path):
    backup_dir = backups_dir_for(path)
    base = os.path.basename(path)
    if not os.path.isdir(backup_dir):
        return []
    names = [n for n in os.listdir(backup_dir) if n.startswith(base) and n.endswith(".bak")]
    full = []
    for name in names:
        full.append(os.path.join(backup_dir, name))
    full.sort()
    return full
