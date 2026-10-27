import re

RESULT_TOKENS = ("1-0", "0-1", "1/2-1/2", "*")

HEADER_RE = re.compile(r'^\[\s*(\w+)\s+"((?:[^"\\]|\\.)*)"\s*\]$')
ESCAPE_LINE_RE = re.compile(r"^%")
LINE_COMMENT_RE = re.compile(r";[^\n]*")
PLAIN_NUMBER_RE = re.compile(r"^\d+(?:\.{1,3})?$")
DOT_PREFIX_RE = re.compile(r"^(\d+)\.{1,3}(.*)$")
NAG_RE = re.compile(r"^\$\d+$")
SAN_RE = re.compile(
    r"^(?:O-O-O|O-O|"
    r"[KQRBNA](?:[a-h][1-8]|[a-h]|[1-8])?x?[a-h][1-8]|"
    r"[a-h]x[a-h][1-8]|"
    r"[a-h][1-8]"
    r")(?:=[QNRBKA])?$"
)


def strip_pgn_comments(text):
    text = _drop_braced(text)
    text = LINE_COMMENT_RE.sub(" ", text)
    return _drop_parenthesised(text)


def _drop_braced(text):
    out = []
    in_brace = False
    for ch in text:
        if in_brace:
            if ch == "}":
                in_brace = False
        elif ch == "{":
            in_brace = True
        else:
            out.append(ch)
    return "".join(out)


def _drop_parenthesised(text):
    out = []
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            if depth:
                depth -= 1
            else:
                out.append(ch)
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def unwrap_move_token(token):
    m = DOT_PREFIX_RE.match(token)
    if m and m.group(2):
        return m.group(2)
    return token


def sanitize_move_token(token):
    while token and token[-1] in "!?":
        token = token[:-1]
    while token and token[-1] in "+#":
        token = token[:-1]
    return token


def is_san_token(cleaned):
    if not cleaned or len(cleaned) > 8:
        return False
    return bool(SAN_RE.match(cleaned))


def tokenize_movetext(text):
    moves = []
    result = None
    text = strip_pgn_comments(text)
    for raw in re.split(r"\s+", text):
        if not raw:
            continue
        token = unwrap_move_token(raw)
        if token in RESULT_TOKENS:
            result = token
            continue
        token = unwrap_move_token(token)
        if token in RESULT_TOKENS:
            result = token
            continue
        if PLAIN_NUMBER_RE.match(token) or NAG_RE.match(token):
            continue
        cleaned = sanitize_move_token(token)
        if cleaned and is_san_token(cleaned):
            moves.append(cleaned)
    return moves, result


def parse_pgn(text):
    games = []
    headers = {}
    movetext_lines = []
    in_movetext = False

    def flush():
        if headers or movetext_lines:
            moves, result = tokenize_movetext("\n".join(movetext_lines))
            effective_headers = dict(headers)
            if result and "Result" not in effective_headers:
                effective_headers["Result"] = result
            games.append(
                {"headers": effective_headers, "moves": moves, "movetext_commented": bool(movetext_lines)}
            )

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ESCAPE_LINE_RE.match(line):
            continue
        header_match = HEADER_RE.match(line)
        if header_match:
            if in_movetext:
                flush()
                headers = {}
                movetext_lines = []
                in_movetext = False
            headers[header_match.group(1)] = header_match.group(2).replace('\\"', '"')
            continue
        movetext_lines.append(line)
        in_movetext = True

    flush()
    games = [g for g in games if g["moves"]]
    return games
