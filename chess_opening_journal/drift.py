def common_prefix_len(a, b):
    limit = min(len(a), len(b))
    for index in range(limit):
        if a[index] != b[index]:
            return index
    return limit


def pending_continuation(line_moves, index, count=3):
    chunk = line_moves[index : index + count]
    return " ".join(chunk)


def drift_report(games, repertoire):
    lines_by_key = {}
    for line in repertoire:
        key = (line.get("family") or "Other opening", line.get("side") or "white")
        lines_by_key.setdefault(key, []).append(line)
    checked = 0
    skipped_color = 0
    off_book = []
    on_book = []
    uncovered_families = set()
    for game in games:
        family = game.get("opening_family") or "Other opening"
        color = game.get("you_color") or "unknown"
        if color == "unknown":
            skipped_color += 1
            continue
        candidates = lines_by_key.get((family, color), [])
        if not candidates:
            uncovered_families.add((family, color))
            continue
        best = None
        best_index = 0
        for line in candidates:
            index = common_prefix_len(game.get("moves", []), line.get("moves", []))
            if best is None or index > best_index:
                best = line
                best_index = index
        checked += 1
        known_moves = best.get("moves", [])
        if best_index >= len(known_moves):
            on_book.append({"game": game, "line": best, "ply": best_index})
            continue
        played_moves = game.get("moves", [])
        row = {
            "game": game,
            "line": best,
            "line_name": best.get("name") or "",
            "family": family,
            "side": color,
            "ply": best_index + 1,
            "expected": known_moves[best_index] if best_index < len(known_moves) else None,
            "played": played_moves[best_index] if best_index < len(played_moves) else None,
            "continuation": pending_continuation(known_moves, best_index),
            "matched_prefix": " ".join(known_moves[:best_index]),
        }
        off_book.append(row)
    return {
        "checked": checked,
        "skipped_color": skipped_color,
        "off_book": off_book,
        "on_book": on_book,
        "uncovered": sorted(f"{family} ({side})" for family, side in uncovered_families),
    }
