"""Console entry point for the Armenian lectionary engine.

Prints the computed lectionary for a date as JSON (native Armenian script).

    armenian-lectionary [YYYY-MM-DD]

With no argument, uses today's date.
"""

import argparse
import datetime
import json

from .engine import compute_armenian_lectionary


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="armenian-lectionary",
        description="Print the Armenian Church lectionary readings for a date "
                    "as JSON. Offline; no network access.",
    )
    parser.add_argument(
        "date",
        nargs="?",
        help="Target date as YYYY-MM-DD (default: today).",
    )
    args = parser.parse_args(argv)

    if args.date:
        try:
            target = datetime.date.fromisoformat(args.date)
        except ValueError:
            parser.error(f"could not parse date {args.date!r}; expected YYYY-MM-DD")
    else:
        target = datetime.date.today()

    result = compute_armenian_lectionary(target)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
