import datetime
import re
import uuid

from .openings import detect_family

RESULT_FOR_WHITE = {"1-0": "win", "0-1": "loss", "1/2-1/2": "draw"}
RESULT_FOR_BLACK = {"1-0": "loss", "0-1": "win", "1/2-1/2": "draw"}

PGN_DATE_SLASHES = re.compile(r"^\d{4}\.\d{2}\.\d{2}$")


def new_id():
    return uuid.uuid4().hex[:8]


def resolve_date(headers, added_iso):
    tag = (headers.get("Date") or "").strip()
    if tag and PGN_DATE_SLASHES.match(tag):
        try:
            parsed = datetime.date.fromisoformat(tag.replace(".", "-"))
            return parsed.isoformat(), tag
        except ValueError:
            pass
    return added_iso.split("T")[0], tag or None


def resolve_color(headers, player_name):
    name = (player_name or "").strip()
    if not name:
        return "unknown"
    white = (headers.get("White") or "").strip()
    black = (headers.get("Black") or "").strip()
    if name.casefold() == white.casefold():
        return "white"
    if name.casefold() == black.casefold():
        return "black"
    return "unknown"


def resolve_result(raw_result, color):
    if raw_result not in RESULT_FOR_WHITE:
        return "unknown"
    if color == "white":
        return RESULT_FOR_WHITE[raw_result]
    if color == "black":
        return RESULT_FOR_BLACK[raw_result]
    return "unknown"


def recommended_result_hint(color, raw_result):
    resolved = resolve_result(raw_result, color)
    if resolved == "unknown":
        if raw_result == "*":
            if color == "white":
                return "if you were White, ask the result or set --result"
            if color == "black":
                return "if you were Black, ask the result or set --result"
        return "pass --result win|loss|draw to record your result"
    return None


def fingerprint_game(headers, moves, raw_result):
    white = (headers.get("White") or "").casefold()
    black = (headers.get("Black") or "").casefold()
    utc_date = (headers.get("UTCDate") or headers.get("Date") or "")
    return (white, black, utc_date, tuple(moves), raw_result)


def make_game_record(
    headers,
    moves,
    source,
    player_name,
    date_added_iso,
    raw_result=None,
    explicit_result=None,
    explicit_color=None,
    note=None,
    confidence=None,
    family_override=None,
):
    moves = list(moves)
    headers = dict(headers)
    raw = raw_result or headers.get("Result") or "*"
    added = date_added_iso or datetime.datetime.now().isoformat(timespec="seconds")
    record_date, date_tag = resolve_date(headers, added)
    color = explicit_color or resolve_color(headers, player_name)
    if explicit_result:
        result = explicit_result
    else:
        result = resolve_result(raw, color)
    family = family_override or detect_family(moves, headers)
    record = {
        "id": new_id(),
        "added": added,
        "date": record_date,
        "date_tag": date_tag,
        "source": source,
        "headers": headers,
        "white": headers.get("White", ""),
        "black": headers.get("Black", ""),
        "moves": moves,
        "ply_count": len(moves),
        "raw_result": raw,
        "you_color": color,
        "result": result,
        "opening_family": family,
        "opening_name": headers.get("Opening", ""),
        "eco": headers.get("ECO", ""),
        "note": note or "",
        "confidence": confidence,
    }
    return record
