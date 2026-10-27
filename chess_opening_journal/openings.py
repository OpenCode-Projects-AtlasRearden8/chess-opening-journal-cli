FAMILY_PREFIXES = [
    (("e4", "e5", "Nf3", "Nc6", "Bb5"), "Ruy Lopez"),
    (("e4", "e5", "Nf3", "Nc6", "Bc4"), "Italian Game"),
    (("e4", "e5", "Nf3", "Nf6"), "Open Game"),
    (("e4", "e5", "Nf3", "Nc6"), "Open Game"),
    (("e4", "e5", "Nf3"), "Open Game"),
    (("e4", "e5"), "Open Game"),
    (("e4", "c5"), "Sicilian Defense"),
    (("e4", "c6"), "Caro-Kann Defense"),
    (("e4", "e6"), "French Defense"),
    (("e4", "d6"), "Pirc Defense"),
    (("e4", "d5"), "Scandinavian Defense"),
    (("e4", "Nf6"), "Alekhine's Defense"),
    (("e4", "Nc6"), "Nimzowitsch Defense"),
    (("e4", "g6"), "Modern Defense"),
    (("e4", "b6"), "Owen's Defense"),
    (("e4",), "King's Pawn (Semi-Open)"),
    (("d4", "f5"), "Dutch Defense"),
    (("d4", "Nf6", "c4", "g6"), "King's Indian / Gruenfeld"),
    (("d4", "Nf6", "c4", "e6"), "Nimzo-Indian / Queen's Indian"),
    (("d4", "Nf6", "c4"), "Indian Defense"),
    (("d4", "Nf6"), "Indian Defense"),
    (("d4", "d5", "c4"), "Queen's Gambit"),
    (("d4", "d5"), "Queen's Pawn Game"),
    (("d4", "Nf3"), "Queen's Pawn Game"),
    (("d4",), "Queen's Pawn Game"),
    (("c4", "e5"), "English Opening"),
    (("c4",), "English Opening"),
    (("Nf3", "d5"), "Reti Opening"),
    (("Nf3",), "Reti Opening"),
    (("g3",), "King's Fianchetto"),
    (("b3",), "Larsen's Opening"),
    (("f4",), "Bird's Opening"),
    (("b4",), "Polish (Sokolsky) Opening"),
]


def _root_of_opening_name(name):
    root = name.split(":")[0]
    root = root.split(",")[0].strip()
    root = root.replace("Defence", "Defense")
    return root


def find_prefix_family(moves):
    prefix = tuple(moves)
    if not prefix:
        return None
    for pattern, label in FAMILY_PREFIXES:
        if len(pattern) <= len(prefix) and prefix[: len(pattern)] == pattern:
            return label
    return None


def detect_family(moves, headers):
    if headers.get("FEN") or headers.get("SetUp") == "1":
        return "Custom start position"
    opening_name = (headers.get("Opening") or "").strip()
    if opening_name:
        return _root_of_opening_name(opening_name)
    fallback = find_prefix_family(moves)
    if fallback:
        return fallback
    eco = (headers.get("ECO") or "").strip()
    if eco and len(eco) >= 2 and eco[:1].isalpha() and eco[1].isdigit():
        return "ECO {}{}x".format(eco[0], eco[1])
    return "Other opening"

