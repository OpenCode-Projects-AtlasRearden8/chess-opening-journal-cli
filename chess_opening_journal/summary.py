def decided_of(row):
    return row["wins"] + row["draws"] + row["losses"]


def score_percent(row):
    decided = decided_of(row)
    if decided <= 0:
        return None
    return round((row["wins"] + 0.5 * row["draws"]) / decided * 100, 1)


def family_rows(games):
    rows = {}
    for game in games:
        family = game.get("opening_family") or "Other opening"
        entry = rows.setdefault(
            family,
            {"family": family, "games": 0, "wins": 0, "draws": 0, "losses": 0, "unknown": 0},
        )
        entry["games"] += 1
        result = game.get("result") or "unknown"
        if result == "win":
            entry["wins"] += 1
        elif result == "loss":
            entry["losses"] += 1
        elif result == "draw":
            entry["draws"] += 1
        else:
            entry["unknown"] += 1
    for entry in rows.values():
        entry["decided"] = decided_of(entry)
        entry["score"] = score_percent(entry)
    return [rows[key] for key in sorted(rows.keys())]


def overall_row(games):
    entry = {"family": "TOTAL", "games": len(games), "wins": 0, "draws": 0, "losses": 0, "unknown": 0}
    for game in games:
        result = game.get("result") or "unknown"
        if result == "win":
            entry["wins"] += 1
        elif result == "loss":
            entry["losses"] += 1
        elif result == "draw":
            entry["draws"] += 1
        else:
            entry["unknown"] += 1
    entry["decided"] = decided_of(entry)
    entry["score"] = score_percent(entry)
    return entry


def focus_families(games, min_decided=2, limit=3):
    rows = [row for row in family_rows(games) if row["decided"] >= min_decided]
    rows.sort(key=lambda row: (row["score"], -row["games"], row["family"]))
    return rows[:limit]


def recent_games(games, limit=3):
    ordered = sorted(games, key=lambda g: (g.get("date") or "", g.get("added") or ""), reverse=True)
    return ordered[:limit]
