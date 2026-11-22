"""Number-field display formats, matching what the screenshot renders.

Port of the frontend's `src/features/annotate/lib/displayFormat.ts`;
`tests/test_display_format.py` pins the port to the frontend test's
assertions. The two must stay in sync: the preview a user confirms
against and the exported `text` describe the same rendering.
"""


def _group_digits(value: int) -> str:
    """8-digit zero-padded, apostrophe-grouped digits: 9123456 ->
    "09'123'456"."""
    padded = str(value).zfill(8)
    parts = []
    while len(padded) > 3:
        parts.append(padded[-3:])
        padded = padded[:-3]
    parts.append(padded)
    return "'".join(reversed(parts))


def format_score(value: int | None) -> str | None:
    """The score text as the screenshot renders it. None for null and
    negative values (the frontend renders no text there)."""
    if value is None or value < 0:
        return None
    return _group_digits(value)


def format_high_score(value: int | None) -> str | None:
    """The high score text as the screenshot renders it: a zero high
    score (no record yet) shows unpadded. Other values render like a
    score."""
    if value == 0:
        return "0"
    return format_score(value)


def format_score_delta(value: int | None) -> str | None:
    """format_score with a leading sign: 1234 -> "+00'001'234". Zero
    carries "+"."""
    if value is None:
        return None
    sign = "-" if value < 0 else "+"
    return f"{sign}{_group_digits(abs(value))}"


def format_early_late(
    far_late: int | None,
    pure_late: int | None,
    far_early: int | None,
    pure_early: int | None,
) -> str | None:
    """The screenshot's early/late line rebuilt from its four values:
    "L12(P34) E56(P78)". The (P…) parts exist only when the PURE
    early/late display is on — both or neither: incomplete PURE data
    cannot occur on a real screenshot, so any missing pure value drops
    the whole PURE info. None unless both far values are set."""
    if far_late is None or far_early is None:
        return None
    show_pure = pure_late is not None and pure_early is not None
    late = f"L{far_late}(P{pure_late})" if show_pure else f"L{far_late}"
    early = f"E{far_early}(P{pure_early})" if show_pure else f"E{far_early}"
    return f"{late} {early}"
