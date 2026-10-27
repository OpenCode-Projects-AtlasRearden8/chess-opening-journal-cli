# Chess Opening Journal

A command-line journal for getting better at chess **openings** — not puzzles, not clocks. Paste or point it at PGN files, and it remembers which opening family you played, whether you won / drew / lost, and what *you* noticed about your effort. From there it summarizes your results per opening family and, **only when you ask**, checks whether your recent games drifted away from the opening lines you want to play. It finishes with a Markdown "practice-focus card" you can keep or pin to your notes.

No engine, no accounts, no network — ever. Everything lives in one JSON file with automatic backups next to it. Python standard library only, no third-party packages at runtime.

Built by [Asdale Dynamics, LLC](https://dylanasdale.github.io) in the same friendly, local-first spirit as *The Massive AI Manual*: plain English, step by step, never condescending. Tools you own and understand.

- **Distinct from [chess-puzzle-drills](../chess-puzzle-drills):** that app trains tactical calculation from puzzle sets. This one journals *your real games* so you can see which openings actually need work.
- **Distinct from [chess-clock-trainer-webapp](../chess-clock-trainer-webapp):** that is a browser clock trainer for time management. This is a text journal about *which openings you chose and how they scored*.

## What it does

- **Log games** — `add` reads PGN files (many tools export these; both players' events OK, `-` reads a PGN you paste on stdin). It knows multiple games per file, skips duplicates, and stores your result (`win` / `draw` / `loss`) from *your* perspective once it knows which side you played.
- **Your color, automatically** — run `configure --player "Dylan Asdale"` once and the PGN `White`/`Black` tags tell the journal which side you played. You can also pass `--result win` or `--color black` explicitly on `add`.
- **Effort notes** — `--note "rushed the morning, still deep"` and `--confidence 1..5` (how solid the opening felt) ride along with every game. Notes show up in lists, details, and the practice card.
- **Summaries** — `summary` crunches W/D/L per opening family (Sicilian, French, Queen's Gambit, ...). The family comes from the PGN's `Opening`/`ECO` headers when they exist, and from a built-in move-prefix table otherwise.
- **Drift, only when you ask** — register the lines you actually want to play with `repertoire add` (from a PGN or raw moves). Then `drift` compares recent games against those lines and shows: which game, at which ply, what you played, what your line expects, and how your line continues. It never nags you; it does nothing until you call it.
- **Practice card** — `card` writes a Markdown snapshot: results by family, weakest families worth drilling (with 2+ decided games), a drift section (only with `--with-drift`), and a queue of your most recent games with notes.
- **Data safety** — every change snapshots the previous journal into `backups/` (timestamped `.bak` files, oldest pruned). `backup` lists them; `backup --restore latest` restores (CLI asks you to type RESTORE; add `--yes` to skip).

## Install & run

Requires Python 3.10+ (tested on 3.13). Zero runtime dependencies.

```bash
# run straight from this folder, no install:
python3 -m chess_opening_journal --help

# optional pipx/pip install for a `chess-opening-journal` command:
pipx install .
```

Journal by default: `./chess_opening_journal.json` (current directory). Use `--journal PATH` or the `CHESS_OPENING_JOURNAL` environment variable.

## A first session, step by step

```bash
# 0) once: remember who you are (matches PGN White/Black tags)
python3 -m chess_opening_journal configure --player "Dylan Asdale"

# 1) log games from a PGN file (works for files with many games)
python3 -m chess_opening_journal add games.pgn --note "morning blitz, felt sharp" --confidence 4

# ...or paste one directly
printf '[Event "casual"]\n[White "Dylan Asdale"]\n[Black "Rival"]\n[Result "1-0"]\n\n1. e4 c5 2. Nf3 d6 1-0\n' \
  | python3 -m chess_opening_journal add -

# no PGN handy? log by hand:
python3 -m chess_opening_journal log --family "French Defense" --result draw --color white \
  --moves "e4 e6 d4 d5" --note "forgot the ...b5 push" --confidence 2

# 2) see everything you logged
python3 -m chess_opening_journal games
python3 -m chess_opening_journal games --family sicilian
python3 -m chess_opening_journal show e81d076a     # your id prefix
python3 -m chess_opening_journal remove e81d0 --yes  # careful: with --yes there is no prompt

# 3) results per opening family
python3 -m chess_opening_journal summary

# 4) register the lines you want to play (then check drift *on demand*)
python3 -m chess_opening_journal repertoire list
python3 -m chess_opening_journal repertoire add --pgn mylines.pgn --side white \
  --name "Najdorf main" --note "watch ...b5"
python3 -m chess_opening_journal repertoire add --moves "e4 e6 d4 d5 Nc3" --side black
python3 -m chess_opening_journal drift
python3 -m chess_opening_journal drift --family sicilian
python3 -m chess_opening_journal repertoire remove 1

# 5) the printable takeaway
python3 -m chess_opening_journal card
python3 -m chess_opening_journal card --with-drift --out practice-focus.md

# 6) your data, your files
python3 -m chess_opening_journal backup          # list backups
python3 -m chess_opening_journal backup --restore latest --yes
```

Helpful extras: `add e4games.pgn classics.pgn -` reads several sources at once; `--journal ~/chess/journal.json` keeps data where you like it.

## How it decides things (plain English)

- **Which side is "you"?** From the configured player name vs PGN headers, `--color`, or `--player`.
- **Did you win?** The PGN `Result` tag plus your color: `1-0` is a win if you were White, a loss if you were Black, and so on. Games without a result show `no result` and don't pollute percentages. `*` (unplayed/ongoing games) means no result too.
- **Which opening family?** The PGN's `Opening` header, trimmed to its root (so `Sicilian Defense: Najdorf Variation` counts as **Sicilian Defense**); else its `ECO` code bucket; else a small built-in table of common move prefixes; else `Other opening`.
- **Drift** = first ply where a game's moves stop matching your registered line. Nothing more mystical than that.

## Privacy & data

- One local JSON file (human-readable if you look inside) + `backups/` next to it.
- No network calls anywhere in the code. No accounts. No chess.com/lichess fetches; export the PGN yourself.
- No secrets or personal data are stored by the tool — only what you deliberately log.

## Tests

```bash
pytest
```

The suite (61 tests) covers the PGN parser (comments, variations, NAGs, annotations, glued move numbers, escaped quotes, multiple games), opening-family mapping, result/color inference, JSON storage + auto-backup/restore, W/D/L aggregation, drift detection, card rendering, and full CLI flows — using fixture PGNs in `tests/fixtures/`.

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Asdale Dynamics, LLC.

Part of the Asdale Dynamics, LLC family of friendly, local-first tools. Chess is for fun and growth; this tool gives no playing advice and no medical-style guarantees — just open, honest bookkeeping of the games you already played.
