from app.services import display_format


def test_format_score_zero_pads_and_groups() -> None:
    assert display_format.format_score(9123456) == "09'123'456"
    assert display_format.format_score(10000000) == "10'000'000"
    assert display_format.format_score(0) == "00'000'000"


def test_format_score_renders_no_text_for_null_and_negative() -> None:
    assert display_format.format_score(None) is None
    assert display_format.format_score(-1) is None


def test_format_high_score_renders_zero_unpadded() -> None:
    assert display_format.format_high_score(0) == "0"


def test_format_high_score_renders_other_values_like_a_score() -> None:
    assert display_format.format_high_score(9123456) == "09'123'456"
    assert display_format.format_high_score(10000000) == "10'000'000"
    assert display_format.format_high_score(None) is None
    assert display_format.format_high_score(-1) is None


def test_format_score_delta_signs_a_padded_score() -> None:
    assert display_format.format_score_delta(1234) == "+00'001'234"
    assert display_format.format_score_delta(-1234) == "-00'001'234"
    assert display_format.format_score_delta(0) == "+00'000'000"


def test_format_score_delta_renders_no_text_for_null() -> None:
    assert display_format.format_score_delta(None) is None


def test_format_early_late_rebuilds_the_line_with_pure_parts() -> None:
    assert display_format.format_early_late(12, 34, 56, 78) == "L12(P34) E56(P78)"


def test_format_early_late_renders_without_pure_parts_when_incomplete() -> None:
    assert display_format.format_early_late(12, None, 56, None) == "L12 E56"
    # incomplete PURE data cannot occur on a real screenshot, so any
    # missing pure value drops the whole PURE info
    assert display_format.format_early_late(12, 34, 56, None) == "L12 E56"
    assert display_format.format_early_late(12, None, 56, 78) == "L12 E56"


def test_format_early_late_requires_both_far_values() -> None:
    assert display_format.format_early_late(None, 1, 2, 3) is None
    assert display_format.format_early_late(1, None, None, None) is None
