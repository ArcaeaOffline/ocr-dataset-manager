"""Text parsing helpers shared by the device and B30 OCR chains."""

import re

# rec sometimes renders lone digits as look-alike letters (O -> 0)
_DIGIT_FIXES = str.maketrans({"O": "0", "o": "0", "D": "0"})

# "P: 1439 (+1358)": pure count with its shiny count in parens
_PURE_SHINY = re.compile(r"P?\s*(\d+)\s*(?:\(\s*\+?(\d+)\s*\))?")


def parse_int(text: str | None) -> int | None:
    if not text:
        return None
    digits = text.replace("'", "").replace(" ", "").lstrip("+")
    if not digits.isdigit():
        digits = digits.translate(_DIGIT_FIXES)
    return int(digits) if digits.isdigit() else None


def parse_pure_shiny(text: str | None) -> tuple[int | None, int | None]:
    """Split a pure counter into (pure, pure_shiny); shiny is None when
    the parens part is missing or unparsable."""
    if not text:
        return None, None
    match = _PURE_SHINY.search(text)
    if match is None:
        return None, None
    pure = parse_int(match.group(1))
    shiny = parse_int(match.group(2)) if match.group(2) else None
    return pure, shiny
