import argparse
import datetime
import json
import os
import sys

from . import __version__
from .card import render_practice_card
from .drift import drift_report
from .game import (
    fingerprint_game,
    make_game_record,
    new_id,
    recommended_result_hint,
)
from .openings import detect_family
from .pgn import parse_pgn, tokenize_movetext
from .summary import family_rows, overall_row
from .storage import (
    JournalError,
    backup_journal,
    backups_dir_for,
    list_backups,
    load_journal,
    normalize_journal,
    save_journal,
)

DEFAULT_JOURNAL_NAME = "chess_opening_journal.json"
ENV_JOURNAL = "CHESS_OPENING_JOURNAL"

RESULT_CHOICES = ("win", "loss", "draw")
SIDE_CHOICES = ("white", "black")
RESULT_ORDER = {"win": 0, "draw": 1, "loss": 2, "unknown": 3}


def resolve_journal_path(cli_value):
    if cli_value:
        return os.path.abspath(cli_value)
    env_value = os.environ.get(ENV_JOURNAL)
    if env_value:
        return os.path.abspath(env_value)
    return os.path.abspath(DEFAULT_JOURNAL_NAME)


def fit(text, width):
    text = str(text)
    if len(text) <= width:
        return text.ljust(width)
    return text[: width - 3] + "..."


def confirm_restore(prompt):
    try:
        answer = input(prompt)
    except EOFError:
        return False
    return answer.strip().upper() == "RESTORE"


def build_parser():
    parser = argparse.ArgumentParser(
        prog="chess-opening-journal",
        description=(
            "Local chess opening journal: parse PGN games, log your opening families"
            " with results and effort notes, and print a practice-focus card."
            " Pure Python standard library, no engines, no accounts, no network."
        ),
        epilog="Your journal is one JSON file with automatic backups next to it.",
    )
    parser.add_argument(
        "--journal",
        default=None,
        metavar="PATH",
        help="path to the journal JSON file (default: ./{} or ${})".format(
            DEFAULT_JOURNAL_NAME, ENV_JOURNAL
        ),
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="command")

    config = subparsers.add_parser(
        "configure", help="set journal-wide settings (player name used for PGN matching)"
    )
    config.add_argument("--player", required=True)

    add = subparsers.add_parser(
        "add", help="log games from PGN files (pass '-' to paste PGN on stdin)"
    )
    add.add_argument("targets", nargs="+", metavar="PGN",
                     help="one or more .pgn files, or '-' for stdin (paste)")
    add.add_argument("--result", choices=RESULT_CHOICES, help="force your result (win/loss/draw)")
    add.add_argument("--color", choices=SIDE_CHOICES, help="force which side you played")
    add.add_argument("--player", help="your name as written in the PGN White/Black tags")
    add.add_argument("--note", help="your own effort note, e.g. 'rushed, morning blitz'")
    add.add_argument("--confidence", type=int, choices=[1, 2, 3, 4, 5],
                     help="how solid the opening felt, 1 (shaky) .. 5 (solid)")

    log = subparsers.add_parser(
        "log", help="log a game without a PGN file (result + opening family + note)"
    )
    log.add_argument("--family", required=True, help="opening family name, e.g. 'French Defense'")
    log.add_argument("--result", required=True, choices=RESULT_CHOICES)
    log.add_argument("--color", choices=SIDE_CHOICES, help="your color (defaults to unknown)")
    log.add_argument("--moves", help="opening moves as SAN text, e.g. 'e4 e6 d4 d5'")
    log.add_argument("--date", metavar="YYYY-MM-DD")
    log.add_argument("--note", help="your own effort note")
    log.add_argument("--confidence", type=int, choices=[1, 2, 3, 4, 5])
    log.add_argument("--eco", help="optional ECO code like C02")

    games = subparsers.add_parser("games", help="list logged games")
    games.add_argument("--limit", type=int, default=15, help="show this many, 0 for all (default 15)")
    games.add_argument("--family", help="only games whose opening family contains this text")

    show = subparsers.add_parser("show", help="show details for one game")
    show.add_argument("id", help="game id (or a unique id prefix)")

    remove = subparsers.add_parser("remove", help="remove one logged game by id prefix")
    remove.add_argument("id", help="game id (or a unique id prefix)")
    remove.add_argument("--yes", action="store_true", help="skip the confirmation prompt")

    repertoire = subparsers.add_parser("repertoire", help="manage your known opening lines")
    repertoire_sub = repertoire.add_subparsers(dest="repertoire_command", required=True, metavar="command")
    rep_add = repertoire_sub.add_parser("add", help="register a known line from a PGN or raw moves")
    rep_add.add_argument("--pgn", nargs="+", metavar="PGN",
                         help="PGN file(s) with the line(s) as games, or '-' for stdin")
    rep_add.add_argument("--moves", help="raw SAN moves, e.g. 'e4 c5 Nf3 d6 d4 cxd4 Nxd4'")
    rep_add.add_argument("--side", choices=SIDE_CHOICES, default="white",
                         help="your side in this line (default white)")
    rep_add.add_argument("--name", help="name for the line (defaults to the opening family)")
    rep_add.add_argument("--family", help="override the detected opening family")
    rep_add.add_argument("--note", help="small reminder, e.g. 'watch out for ...b5 push'")
    rep_list = repertoire_sub.add_parser("list", help="list known lines")
    rep_remove = repertoire_sub.add_parser("remove", help="remove a known line by its list number")
    rep_remove.add_argument("index", type=int, help="line number as shown by 'repertoire list'")
    rep_remove.add_argument("--yes", action="store_true", help="skip the confirmation prompt")

    summary = subparsers.add_parser("summary", help="W/D/L per opening family")
    summary.add_argument("--family", help="only families whose name contains this text")

    drift = subparsers.add_parser(
        "drift", help="compare games with your known lines (only runs when you ask)"
    )
    drift.add_argument("--family", help="only families whose name contains this text")

    card = subparsers.add_parser("card", help="export a Markdown practice-focus card")
    card.add_argument("--out", metavar="FILE", help="write card to a Markdown file instead of stdout")
    card.add_argument("--family", help="only count families whose name contains this text")
    card.add_argument("--with-drift", action="store_true",
                      help="include drift vs known lines in the card")

    backup = subparsers.add_parser("backup", help="list backups or restore one")
    backup.add_argument("--restore", metavar="PATH_OR_latest",
                        help="restore from a backup file path, or 'latest'")
    backup.add_argument("--yes", action="store_true", help="skip the RESTORE confirmation")

    return parser


def commit(journal, journal_path):
    limit = journal["settings"].get("max_backups", 30)
    backup_path = backup_journal(journal_path, limit=limit)
    save_journal(journal, journal_path)
    if backup_path:
        print("Auto-backup: {}".format(os.path.relpath(backup_path)))
    return backup_path


def run_add_batch(journal, sources, player_name, explicit_result, explicit_color, note, confidence):
    added_now = 0
    skipped = 0
    added_iso = datetime.datetime.now().isoformat(timespec="seconds")
    existing_fingerprints = [fingerprint_game(g.get("headers", {}), g.get("moves", []), g.get("raw_result", "*")) for g in journal["games"]]
    existing_set = set(existing_fingerprints)
    parsed_total = 0
    for label, parsed_games in sources:
        for parsed in parsed_games:
            parsed_total += 1
            moves = parsed["moves"]
            headers = parsed["headers"]
            fingerprint = fingerprint_game(headers, moves, headers.get("Result", "*"))
            if fingerprint in existing_set:
                skipped += 1
                continue
            record = make_game_record(
                headers,
                moves,
                source=label,
                player_name=player_name,
                date_added_iso=added_iso,
                explicit_result=explicit_result,
                explicit_color=explicit_color,
                note=note,
                confidence=confidence,
            )
            if record["result"] == "unknown" and explicit_result is None:
                hint = recommended_result_hint(record["you_color"], record["raw_result"])
                if hint:
                    print("  note ({}): {}".format(record["id"], hint))
            journal["games"].append(record)
            existing_set.add(fingerprint)
            added_now += 1
    return added_now, skipped, parsed_total


def cmd_add(args, journal, journal_path):
    player_name = args.player or journal["settings"].get("player_name", "")
    sources = []
    for target in args.targets:
        if target == "-":
            sources.append(("pasted", parse_pgn(sys.stdin.read())))
        else:
            try:
                with open(target, "r", encoding="utf-8") as fh:
                    sources.append((os.path.basename(target), parse_pgn(fh.read())))
            except OSError as exc:
                print("could not read {}: {}".format(target, exc))
    if not sources:
        print("No PGN text read; nothing added.")
        return 1
    parsed_total = sum(len(parsed_games) for _, parsed_games in sources)
    if parsed_total > 1 and (args.result or args.color):
        print("Note: more than one game parsed; --result/--color applies to all of them.")
    added, skipped, parsed_total = run_add_batch(
        journal,
        sources,
        player_name,
        args.result,
        args.color,
        args.note,
        args.confidence,
    )
    if parsed_total == 0:
        print("No games found in the given PGN sources; nothing added.")
        return 0
    commit(journal, journal_path)
    pieces = []
    if added:
        pieces.append("added {} game{}".format(added, "" if added == 1 else "s"))
    if skipped:
        pieces.append("skipped {} duplicate{}".format(skipped, "" if skipped == 1 else "s"))
    print("; ".join(pieces) if pieces else "no changes")
    print("Journal now holds {} game{}.".format(len(journal["games"]), "" if len(journal["games"]) == 1 else "s"))
    if args.note and added:
        print("Note attached to the new game(s).")
    return 0


def cmd_log(args, journal, journal_path):
    moves, _ = tokenize_movetext(args.moves or "")
    headers = {}
    today = datetime.date.today().isoformat()
    if args.date:
        headers["Date"] = args.date.replace("-", ".") if re_all_digits(args.date) else args.date
        date_for_record = args.date
    else:
        date_for_record = today
    if args.color == "white":
        friendly = journal["settings"].get("player_name") or "You"
        headers["White"] = friendly
        headers["Black"] = "Unknown opponent"
    elif args.color == "black":
        friendly = journal["settings"].get("player_name") or "You"
        headers["White"] = "Unknown opponent"
        headers["Black"] = friendly
    if args.eco:
        headers["ECO"] = args.eco
    record = make_game_record(
        headers,
        moves,
        source="log",
        player_name=journal["settings"].get("player_name", ""),
        date_added_iso=datetime.datetime.now().isoformat(timespec="seconds"),
        explicit_result=args.result,
        explicit_color=args.color,
        note=args.note,
        confidence=args.confidence,
        family_override=args.family,
    )
    record["date"] = date_for_record
    journal["games"].append(record)
    commit(journal, journal_path)
    print("Logged: {} as {}/{} on {} ({} plies).".format(record["id"], args.family, args.color or "?", record["date"], record["ply_count"]))
    print("Journal now holds {} game{}.".format(len(journal["games"]), "" if len(journal["games"]) == 1 else "s"))
    return 0


def re_all_digits(value):
    try:
        int(value.replace("-", ""))
    except ValueError:
        return False
    return True


def filter_games(games, family_text):
    if not family_text:
        return games
    needle = family_text.casefold()
    return [g for g in games if needle in (g.get("opening_family") or "").casefold()]


def ids_starting_with(games, prefix):
    matches = [g for g in games if g.get("id", "").startswith(prefix)]
    return matches


def cmd_games(args, journal, journal_path):
    games = filter_games(journal["games"], args.family)
    if not games:
        print("No games logged{} yet. Try `add` (from a PGN file) or `log`.".format(" for that family" if args.family else ""))
        return 0
    ordered = sorted(games, key=lambda g: (g.get("date") or "", g.get("added") or ""), reverse=True)
    limit = max(0, args.limit)
    if limit:
        ordered = ordered[:limit]
    shown_total = len(journal["games"])
    qualifier = " family-filtered" if args.family else ""
    print("Showing {} of {} logged game(s){}.".format(len(ordered), shown_total, qualifier))
    header = "id       date        color  result    plies  opening family{}"
    header = header.format("  note" if any(g.get("note") for g in ordered) else "")
    print(header)
    print("-" * len(header))
    for game in ordered:
        color = game.get("you_color") or "?"
        result = "no result" if (game.get("result") or "unknown") == "unknown" else game["result"]
        note_col = "  " + fit(game.get("note") or "", 24) if game.get("note") else ""
        print(
            "{}  {}  {:<6} {:<9} {:5d}  {}".format(
                game.get("id", "?"),
                fit(game.get("date") or "?", 10),
                color,
                result,
                game.get("ply_count", len(game.get("moves", []))),
                fit(game.get("opening_family") or "?", 24),
            )
            + note_col
        )
    return 0


def cmd_show(args, journal, journal_path):
    matches = ids_starting_with(journal["games"], args.id)
    if not matches:
        print("No game with id starting '{}'.".format(args.id))
        return 1
    if len(matches) > 1:
        print("'{}' matches several ids: {}".format(args.id, ", ".join(g['id'] for g in matches)))
        return 1
    game = matches[0]
    headers = game.get("headers", {})
    print("Game {}".format(game.get("id")))
    print("Source: {} | added: {}".format(game.get("source"), game.get("added")))
    print("Date: {} (tag {})".format(game.get("date"), game.get("date_tag") or "-"))
    print("White: {} | Black: {}".format(game.get("white") or "-", game.get("black") or "-"))
    if game.get("eco") or game.get("opening_name"):
        print("ECO: {} | Opening: {}".format(game.get("eco") or "-", game.get("opening_name") or "-"))
    print("You played: {} | Your result: {} (raw {})".format(
        game.get("you_color") or "unknown", game.get("result"), game.get("raw_result")
    ))
    print("Family: {}".format(game.get("opening_family")))
    print("Plies: {}".format(game.get("ply_count")))
    if game.get("confidence"):
        print("Effort confidence: {}/5".format(game["confidence"]))
    if game.get("note"):
        print("Note: {}".format(game["note"]))
    moves = game.get("moves", [])
    if moves:
        print("Moves:")
        for start in range(0, len(moves), 8):
            tokens = []
            for ply in range(start, min(start + 8, len(moves))):
                move_no = ply // 2 + 1
                label = "{}... {}".format(move_no, moves[ply]) if ply % 2 else "{}. {}".format(move_no, moves[ply])
                tokens.append(label)
            print("  " + " ".join(tokens))
    return 0


def cmd_remove(args, journal, journal_path):
    matches = ids_starting_with(journal["games"], args.id)
    if not matches:
        print("No game with id starting '{}'.".format(args.id))
        return 1
    if len(matches) > 1:
        print("'{}' matches several ids: {}".format(args.id, ", ".join(g["id"] for g in matches)))
        return 1
    game = matches[0]
    if not args.yes:
        try:
            answer = input("Remove {} ({} {}) [y/N]? ".format(game["id"], game.get("date"), game.get("opening_family")))
        except EOFError:
            answer = ""
        if answer.strip().lower() not in ("y", "yes"):
            print("Cancelled; nothing removed.")
            return 0
    journal["games"].remove(game)
    commit(journal, journal_path)
    print("Removed game {}.".format(game["id"]))
    return 0


def sanitize_line_moves(moves_text):
    moves, _ = tokenize_movetext(moves_text or "")
    return moves


def cmd_repertoire(args, journal, journal_path):
    if args.repertoire_command == "add":
        return repertoire_add(args, journal, journal_path)
    if args.repertoire_command == "list":
        return repertoire_list(journal)
    if args.repertoire_command == "remove":
        return repertoire_remove(args, journal, journal_path)
    print("Unknown repertoire command.")
    return 2


def repertoire_add(args, journal, journal_path):
    lines = []
    if args.moves:
        moves = sanitize_line_moves(args.moves)
        if not moves:
            print("No valid SAN moves in --moves; nothing added.")
            return 1
        lines.append({
            "moves": moves,
            "headers": {},
            "label": "moves text",
        })
    if args.pgn:
        for target in args.pgn:
            if target == "-":
                text = sys.stdin.read()
                label = "pasted"
            else:
                try:
                    with open(target, "r", encoding="utf-8") as fh:
                        text = fh.read()
                except OSError as exc:
                    print("could not read {}: {}".format(target, exc))
                    continue
                label = os.path.basename(target)
            for parsed in parse_pgn(text):
                lines.append({"moves": parsed["moves"], "headers": parsed["headers"], "label": label})
    if not lines:
        print("Nothing to add: pass --moves 'e4 c5 ...' or --pgn FILE.")
        return 1
    if len(lines) > 1 and args.name:
        print("Note: --name applies only to the first line added; others get family-based names.")
    added = 0
    skipped = 0
    existing_keys = {
        (line.get("family") or "", line.get("side") or "", tuple(line.get("moves", [])))
        for line in journal["repertoire"]
    }
    for index, item in enumerate(lines):
        moves = item["moves"]
        family = args.family or detect_family(moves, item["headers"])
        name = args.name if index == 0 else None
        name = name or (family if len(lines) == 1 else "{} line {}".format(family, index + 1))
        key = (family, args.side, tuple(moves))
        if key in existing_keys:
            skipped += 1
            continue
        entry = {
            "id": new_id(),
            "name": name,
            "side": args.side,
            "family": family,
            "moves": moves,
            "note": args.note or "",
            "added": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        journal["repertoire"].append(entry)
        existing_keys.add(key)
        added += 1
    if added:
        commit(journal, journal_path)
    print(
        "Known lines: added {}, skipped {}. Repertoire holds {} line{} now.".format(
            added, skipped, len(journal["repertoire"]), "" if len(journal["repertoire"]) == 1 else "s"
        )
    )
    return 0


def repertoire_list(journal):
    repertoire = journal["repertoire"]
    if not repertoire:
        print("No known lines yet. Add one with `repertoire add --pgn FILE --side white` or `repertoire add --moves 'e4 e6 d4 d5' --side black`.")
        return 0
    print("{} known line(s):".format(len(repertoire)))
    for index, line in enumerate(repertoire, start=1):
        preview = " ".join(line.get("moves", [])[:8])
        if len(line.get("moves", [])) > 8:
            preview += " ..."
        print(
            "{}. [{}] {} - {} ({} plies){}".format(
                index,
                line.get("side", "?"),
                line.get("family", "?"),
                line.get("name", ""),
                len(line.get("moves", [])),
                "  note: {}".format(line["note"]) if line.get("note") else "",
            )
        )
        print("     {}".format(preview))
    return 0


def repertoire_remove(args, journal, journal_path):
    repertoire = journal["repertoire"]
    if not repertoire:
        print("No known lines to remove.")
        return 0
    if args.index < 1 or args.index > len(repertoire):
        print("No line number {}; use `repertoire list` to see 1..{}.".format(args.index, len(repertoire)))
        return 1
    line = repertoire[args.index - 1]
    if not args.yes:
        try:
            answer = input("Remove known line {} '{}' [y/N]? ".format(args.index, line.get("name")))
        except EOFError:
            answer = ""
        if answer.strip().lower() not in ("y", "yes"):
            print("Cancelled; nothing removed.")
            return 0
    removed = repertoire.pop(args.index - 1)
    commit(journal, journal_path)
    print("Removed known line '{}' ({}).".format(removed.get("name"), removed.get("side")))
    return 0


def cmd_summary(args, journal, journal_path):
    games = filter_games(journal["games"], args.family)
    if not games:
        print("No games logged{}; run `add` or `log` to start.".format(" in that family" if args.family else ""))
        return 0
    rows = family_rows(games)
    overall = overall_row(games)
    locale = "[TOTAL] {} games: {} W / {} D / {} L / {} no result".format(
        overall["games"], overall["wins"], overall["draws"], overall["losses"], overall["unknown"]
    )
    if overall["score"] is not None:
        locale += " - {:.0f}% decided score".format(overall["score"])
    print(locale)
    print("")
    print("{:32} {:5} {:3} {:3} {:3} {:4} {:7}".format("opening family", "gms", "W", "D", "L", "noR", "score"))
    for row in rows:
        score = "{:.0f}%".format(row["score"]) if row["score"] is not None else "-"
        print(
            "{:32} {:5} {:3} {:3} {:3} {:4} {:7}".format(
                fit(row["family"], 32), row["games"], row["wins"], row["draws"], row["losses"], row["unknown"], score
            )
        )
    return 0


def cmd_drift(args, journal, journal_path):
    repertoire = journal["repertoire"]
    if not repertoire:
        print("No known lines registered yet - nothing to compare against.")
        print("Register one with: repertoire add --pgn yourlines.pgn --side white")
        return 0
    games = filter_games(journal["games"], args.family)
    if not games:
        print("No games logged{}.".format(" in that family" if args.family else ""))
        return 0
    report = drift_report(games, repertoire)
    print("Checked {} game{} against {} known line{}.".format(
        report["checked"], "" if report["checked"] == 1 else "s",
        len(repertoire), "" if len(repertoire) == 1 else "s",
    ))
    if report["skipped_color"]:
        print("Skipped {} game{} where your color is unknown; log with --player/--color to include.".format(
            report["skipped_color"], "" if report["skipped_color"] == 1 else "s"
        ))
    grouped = {}
    for row in report["off_book"]:
        grouped.setdefault((row["family"], row["side"]), []).append(row)
    if grouped:
        print("")
        print("Off your lines:")
        for (family, side), rows in sorted(grouped.items()):
            print("  {} as {} ({} game{}):".format(family, side, len(rows), "" if len(rows) == 1 else "s"))
            for row in sorted(rows, key=lambda r: r["ply"]):
                game = row["game"]
                played = row.get("played") or "(game ended earlier)"
                expected = row.get("expected") or "-"
                continuation = row.get("continuation") or "(your line ends)"
                print(
                    "    {} {}: at ply {} after `{}` you played `{}`; your line expects `{}`, then `{}`".format(
                        game.get("id"), game.get("date"), row["ply"],
                        row.get("matched_prefix") or "(start)",
                        played, expected, continuation,
                    )
                )
    else:
        print("All checked games stayed on your known lines. Solid.")
    if report["on_book"]:
        print("{} stayed fully on-book (played past your whole known line).".format(len(report["on_book"])))
    if report["uncovered"]:
        print("Families without a known line for that side: {}.".format(", ".join(report["uncovered"])))
        print("Register lines for them with `repertoire add`.")
    return 0


def cmd_card(args, journal, journal_path):
    if not journal["games"]:
        print("No games logged yet; log a game with `add` or `log` first.")
        return 0
    drift_data = None
    if args.with_drift and journal["repertoire"]:
        drift_data = drift_report(filter_games(journal["games"], args.family), journal["repertoire"])
    elif args.with_drift:
        print("(no known lines yet, so the drift section starts empty)")
    card_text = render_practice_card(journal, drift_data, today=datetime.date.today().isoformat())
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(card_text + "\n")
        print("Practice card written to {}.".format(os.path.abspath(args.out)))
    else:
        print(card_text)
    return 0


def cmd_backup(args, journal, journal_path):
    backups = list_backups(journal_path)
    if args.restore is None:
        if not backups:
            print("No backups yet. Backups start appearing after your first change.")
            print("Location: {}".format(os.path.relpath(backups_dir_for(journal_path))))
            return 0
        print("Backups in {}:".format(os.path.relpath(backups_dir_for(journal_path))))
        for path in backups:
            print("  {} ({} bytes)".format(os.path.basename(path), os.path.getsize(path)))
        print("Restore with: chess-opening-journal backup --restore latest")
        return 0
    if not backups:
        print("No backups found; nothing to restore.")
        return 1
    if args.restore == "last":
        chosen = backups[-1]
    elif args.restore in ("latest",):
        chosen = backups[-1]
    else:
        candidates = [p for p in backups if os.path.basename(p) == os.path.basename(args.restore)]
        if not candidates and os.path.exists(args.restore):
            if os.path.abspath(args.restore) in [os.path.abspath(p) for p in backups]:
                candidates = [args.restore]
            elif os.path.dirname(os.path.abspath(args.restore)) == os.path.abspath(backups_dir_for(journal_path)):
                candidates = [args.restore]
        if not candidates:
            print("Backup '{}' not found; run `backup` to list valid files.".format(args.restore))
            return 1
        chosen = candidates[0]
    try:
        with open(chosen, "r", encoding="utf-8") as fh:
            restored = normalize_journal(json.load(fh))
    except (OSError, ValueError) as exc:
        print("Could not read backup {}: {}".format(chosen, exc))
        return 1
    if not args.yes:
        if not confirm_restore("Type RESTORE to replace your journal with {} (anything else cancels): ".format(os.path.basename(chosen))):
            print("Restore cancelled; journal untouched.")
            return 0
    if os.path.exists(journal_path):
        pre_restore = os.path.join(backups_dir_for(journal_path), "{}.pre-restore.bak".format(os.path.basename(journal_path)))
        os.makedirs(backups_dir_for(journal_path), exist_ok=True)
        with open(journal_path, "r", encoding="utf-8") as src, open(pre_restore, "w", encoding="utf-8") as dst:
            dst.write(src.read())
        print("Current journal saved aside as {}.".format(os.path.basename(pre_restore)))
    save_journal(restored, journal_path)
    print("Restored journal from {}.".format(os.path.basename(chosen)))
    return 0


def cmd_configure(args, journal, journal_path):
    journal["settings"]["player_name"] = args.player.strip()
    commit(journal, journal_path)
    print("Journal remembers your name as '{}'; PGN headers matching it set your color.".format(args.player.strip()))
    return 0


HANDLERS = {
    "configure": cmd_configure,
    "add": cmd_add,
    "log": cmd_log,
    "games": cmd_games,
    "show": cmd_show,
    "remove": cmd_remove,
    "repertoire": cmd_repertoire,
    "summary": cmd_summary,
    "drift": cmd_drift,
    "card": cmd_card,
    "backup": cmd_backup,
}


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    journal_path = resolve_journal_path(args.journal)
    try:
        journal = load_journal(journal_path)
    except JournalError as exc:
        print("Journal problem: {}".format(exc), file=sys.stderr)
        return 1
    journal["journal_name"] = os.path.basename(journal_path)
    journal["settings"] = journal.get("settings") or {}
    journal["games"] = journal.get("games") or []
    journal["repertoire"] = journal.get("repertoire") or []
    handler = HANDLERS[args.command]
    try:
        return handler(args, journal, journal_path)
    except KeyboardInterrupt:
        print("", file=sys.stderr)
        print("Interrupted; nothing saved.", file=sys.stderr)
        return 130
