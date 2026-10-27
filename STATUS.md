# STATUS - chess-opening-journal-cli

Updated: 2026-10-27

## What was built

**chess-opening-journal** - a pure-stdlib (Python 3.10+, zero runtime dependencies)
command-line journal for chess **openings** training, built as a friendly, local-first
tool by Asdale Dynamics, LLC:

- Parses PGN files (or pasted stdin PGN) into games: headers, SAN moves, results.
  Handles `{...}` line comments, `( ... )` variations, `$n` NAGs, `!?+#` annotations,
  glued move numbers (`1.e4`, `2...c5`), escaped quotes in header values, percentage-escape
  lines, and multiple games per file. Header-only "games" with no moves are skipped.
- Logs games with **your** perspective: result (`win`/`draw`/`loss`) derived from the PGN
  `Result` tag + which side you played; your side comes from `configure --player` matching
  `White`/`Black` tags, or explicit `--color`/`--result`. No result (`*` or missing tag)
  is stored as `no result` and never pollutes percentages.
- Effort notes (`--note "rushed morning, still sharp"`) and confidence 1-5
  (`--confidence`) attach to every game; they surface in lists, `show`, and the card.
- Duplicate import protection: identical (players, UTC/Date tag, moves, result)
  fingerprints are skipped with an explicit count message.
- **Opening families**: `Opening` header root (so `Sicilian Defense: Najdorf Variation`
  groups as *Sicilian Defense*, and British `Defence` spellings normalize), else a
  built-in move-prefix table (Sicilian, French, Caro-Kann, Scandinavian, Open/Semi-Open,
  Queen's Pawn, Queen's Gambit, Indian families, English, Reti, Dutch, Pirc, Modern,
  Alekhine, Nimzowitsch, Owen, KID/Gruenfeld, Nimzo/QID, King's/Queen's Fianchetto,
  Bird, Larsen, Polish), else an `ECO` bucket (`A0x`-style), else `Other opening`;
  `FEN`/`SetUp "1"` games are tagged `Custom start position`.
- `summary` prints W/D/L per family with a score percentage plus a TOTAL line.
- **Drift detection is strictly on-demand**: you register the lines you want to play with
  `repertoire add` (from PGN game(s) or `--moves` raw SAN text; `--side white|black`),
  and only `drift` (or `card --with-drift`) compares games against those lines. The
  report shows, per game: the matched prefix, the offending ply, what you played, what
  your line expects, and how your known line continues. Fully on-book games are counted;
  families with no registered line for that side are reported as uncovered.
- `card` exports a Markdown **practice-focus card** (stdout or `--out FILE`): snapshot
  totals, family table sorted weakest-first, focus picks (families with 2+ decided
  games), an optional drift section, and a review queue of your most recent games with
  notes/effort. Generated only when you ask; drift appears only with `--with-drift`.
- Storage: one human-readable JSON file (default `./chess_opening_journal.json`,
  override with `--journal PATH` or `CHESS_OPENING_JOURNAL` env var). Every mutation
  (`add`, `log`, `remove`, `configure`, `repertoire add/remove`) snapshots the previous
  file into `backups/` as timestamped `.bak` (microsecond resolver prevents same-second
  collisions); oldest pruned to `settings.max_backups` (default 30). `backup` lists
  backups; `backup --restore latest|PATH` restores - validates the JSON before writing,
  keeps the pre-restore state as `*.pre-restore.bak`, and asks you to type RESTORE
  (skippable with `--yes`). Saves are atomic (temp file + `os.replace`).
- CLI UX: IDs match by unique prefix; nonexistent files, bad ids, corrupted journals
  produce plain-English errors with exit code 1 (corrupt journal points at backups).

Distinct from sibling projects **chess-puzzle-drills** (tactics puzzles) and
**chess-clock-trainer-webapp** (clock/time training) - this one journals real games and
opening-line discipline. Noted in the README.

## Layout

```text
chess_opening_journal/
  __init__.py / __main__.py   package + python -m entry
  cli.py                      argparse, all commands, backups/restore UX
  pgn.py                      stdlib PGN parser + move tokenizer/sanitizer
  openings.py                 family mapping (Opening root -> prefix table -> ECO)
  game.py                     record builder, color/result/date/name resolution, fingerprints
  storage.py                  JSON load/save (atomic), backup+prune+restore helpers
  summary.py                  family rows, overall, focus picks, recency queue
  drift.py                    best-line matching, off-book rows, uncovered families
  card.py                     Markdown practice card renderer
tests/
  fixtures/                   repertoire_white.pgn, repertoire_french_black.pgn,
                              games_mix.pgn, games_dupe.pgn, games_no_result.pgn,
                              games_opening_tags.pgn, games_fen.pgn
  test_pgn.py, test_openings.py, test_game.py, test_storage.py,
  test_summary.py, test_drift.py, test_card.py, test_cli.py (end-to-end via main(argv))
conftest.py                  sys.path bootstrap
pyproject.toml               setuptools metadata; optional console script chess-opening-journal
LICENSE                      MIT, Copyright (c) 2026 Asdale Dynamics, LLC
README.md                    friendly guide; credits Asdale Dynamics, LLC
.gitignore
```

## How to run

```bash
# no install needed:
python3 -m chess_opening_journal --help
python3 -m chess_opening_journal configure --player "Your Name"
python3 -m chess_opening_journal add games.pgn --note "..." --confidence 4
python3 -m chess_opening_journal summary
python3 -m chess_opening_journal card --with-drift --out practice-focus.md

# optional install (verified locally with pip wheel):
pipx install .
```

## Verification results (all run 2026-10-27, Python 3.13.5, pytest 9.1.1)

- `python3 -m pytest`: **61 passed** (0.2s) - parser, openings, game, storage (incl.
  backup prune to 30 and corrupt-JSON recovery path), summary math, drift rows,
  card rendering, and 13 end-to-end CLI tests driving `main(argv)` against a tmp
  journal (configure -> add file -> duplicates skipped -> games/summary/show/remove ->
  repertoire add/list/remove -> drift -> card to file -> stdin paste -> backup restore
  roundtrip -> cancel prompt -> temp-file cleanup).
- End-to-end smoke in a scratch dir: `add sample.pgn --player ... --note ...` added 2
  games with correct white-win/black-win mapping from `1-0`/`0-1`; `games`, `summary`,
  `show`, `log`, `remove`, `card --out`, `repertoire add/list/remove`, `drift` (off-book
  at ply 10 with expected/played/continuation, on-book count, uncovered family),
  `backup`, `backup --restore latest --yes`, and stdin paste all behaved as documented.
- Wheel build offline: `python3 -m pip wheel . --no-deps` produced
  `chess_opening_journal-1.0.0-py3-none-any.whl` (setuptools metadata valid).
- `python3 -m compileall` clean; no third-party imports at runtime (stdlib only).

## Known gaps

- PGN parser is pragmatic, not exhaustive: exotic tags are preserved but unused; no move
  legality validation (SAN sequences are trusted after token sanitization); games played
  from an unusual starting point are journaled but family/drift use only the standard
  mapping (they get `Custom start position` and skip drift).
- Family detection uses a curated prefix table, not the full ECO encyclopedia; umbrella
  names (e.g. `King's Indian / Gruenfeld`) intentionally group beginners' needs.
- Drift is prefix-based against your registered lines only - it never evaluates whether a
  deviation was good or bad (no engine, by design).
- `repertoire add --pgn` applies one `--side` to all lines in that call (run separate
  commands per side); `--name` applies only to first line added.
- No CSV/JSON export of the whole journal beyond printing; no `repertoire edit` (remove +
  re-add instead). Filenames/sizes assume UTF-8 plain-text PGN.
- Windows console friendliness is untested (paths are handled via `os.path`; output is ASCII).

Backups protect against accidental loss, but the pre-restore copy + restore validation is
the main safety net; delete `backups/` only if you truly mean it.
