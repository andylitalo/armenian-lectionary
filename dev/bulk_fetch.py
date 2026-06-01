"""DEV-ONLY concurrent bulk fetcher (reuses fetch_reference caching).

Pulls a wide range of years of ground truth from sacredtradition.am into
dev/reference_data/ so we have many Easter-date / weekday alignments to
reverse-engineer the lectionary rules. NOT used by the app at runtime.

    python dev/bulk_fetch.py 2014-01-01 2027-12-31 [workers]
"""

import concurrent.futures as cf
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_reference import fetch_day  # noqa: E402


def daterange(start, end):
    d = start
    while d <= end:
        yield d
        d += datetime.timedelta(days=1)


def main(argv):
    start = datetime.date.fromisoformat(argv[0])
    end = datetime.date.fromisoformat(argv[1])
    workers = int(argv[2]) if len(argv) > 2 else 8
    days = list(daterange(start, end))
    done = err = 0
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fetch_day, d): d for d in days}
        for fut in cf.as_completed(futs):
            d = futs[fut]
            try:
                fut.result()
                done += 1
            except Exception as e:  # noqa: BLE001
                err += 1
                if err <= 10:
                    print(f"  ERR {d}: {e}")
            if done % 250 == 0:
                print(f"  ...{done}/{len(days)} fetched")
    print(f"DONE: {done} fetched, {err} errors, range {start}..{end}")


if __name__ == "__main__":
    main(sys.argv[1:])
