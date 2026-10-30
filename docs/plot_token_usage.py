"""Plot daily token usage from docs/token-usage.jsonl as a stacked SVG bar chart.

Each bar is one GMT day. Segments bottom-up are cache-read input, cache-write
input, non-cached input, and output. Bars aggregate all sources and models of
that day, placed on a real calendar axis. Each bar is labeled with its total
tokens and its cache-hit rate (cache-read / input).

Usage:
    uv run --with matplotlib python docs/plot_token_usage.py \
        docs/token-usage.jsonl -o docs/token-usage.svg
"""

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

FIELDS = ("cache_read_tokens", "cache_write_tokens", "output_tokens")


def load_days(path: Path) -> list[dict]:
    days: dict[str, dict[str, int]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        day = days.setdefault(
            row["date"], {"input_tokens": 0, **{f: 0 for f in FIELDS}}
        )
        for key in ("input_tokens", *FIELDS):
            day[key] += row[key]
    return [dict(date=d, **days[d]) for d in sorted(days)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", type=Path, help="token-usage.jsonl path")
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()

    import matplotlib.pyplot as plt

    days = load_days(args.jsonl)
    if not days:
        raise SystemExit(f"no records in {args.jsonl}")

    cache_read = [day["cache_read_tokens"] for day in days]
    cache_write = [day["cache_write_tokens"] for day in days]
    # input_tokens contains the cached parts. The remainder is plain input
    plain_input = [
        max(0, day["input_tokens"] - day["cache_read_tokens"] - day["cache_write_tokens"])
        for day in days
    ]
    output = [day["output_tokens"] for day in days]

    def bar_label(day: dict, total: int) -> str:
        rate = day["cache_read_tokens"] / day["input_tokens"] * 100 if day["input_tokens"] else 0.0
        return f"{total / 1e6:.1f}M\n(CH {rate:.1f}%)"

    segments = [
        ("input: cache read", cache_read, "C0"),
        ("input: cache write", cache_write, "C5"),
        ("input: non-cached", plain_input, "C4"),
        ("output", output, "C1"),
    ]

    import matplotlib.dates as mdates
    import matplotlib.patheffects as pe

    xs = [date.fromisoformat(day["date"]) for day in days]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bottom = [0] * len(days)
    for name, values, color in segments:
        ax.bar(xs, values, bottom=bottom, label=name, color=color, width=1.0)
        bottom = [b + v for b, v in zip(bottom, values, strict=True)]
    # on the calendar axis, active days can be adjacent and a label is wider
    # than one day of axis space. The white halo keeps it legible where it
    # crosses a neighboring bar
    label_style = dict(
        ha="center", va="bottom", fontsize=8,
        path_effects=[pe.withStroke(linewidth=2.5, foreground="white")],
    )
    for x, day, total in zip(xs, days, bottom, strict=True):
        ax.text(x, total, bar_label(day, total), **label_style)

    # two-line bar labels need headroom above the tallest bar
    ax.set_ylim(0, max(bottom) * 1.18)
    ax.set_xlim(xs[0] - timedelta(days=2), xs[-1] + timedelta(days=2))
    ax.set_title("Daily LLM token usage (GMT day, all sources)")
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=10))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax.yaxis.set_major_formatter(lambda v, _: f"{v / 1e6:.0f}M")
    ax.set_ylabel("tokens / day")
    ax.legend(reverse=True)
    ax.set_axisbelow(True)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(args.output)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
