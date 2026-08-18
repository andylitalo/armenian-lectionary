"""DEV-ONLY: derive ``dev/feast_name_review_atomic.tsv`` from ``dev/feast_name_review.tsv``,
for reviewing one saint/feast at a time.

Why. A handful of ``feast_name_review.tsv`` rows are not one feast: the SOURCE itself
concatenates two independent, otherwise-standalone commemorations with ", and " (or "; and
") when they fall on the same day (e.g. the 2008-01-21 row is literally "<Sargis's own
row>, and <Atom's own row>", each of which is ALSO its own row elsewhere, unglued).
Reviewing the glued row is redundant with reviewing its parts, and doubles the reviewer's
work on the exact same text.

Two ways a row turns out to be glued:

  1. Straightforward -- the row splits into pieces that are EACH, byte for byte, some
     OTHER row's ``source``. That is what catches Sargis+Atom.
  2. Mined -- one piece never appears alone anywhere in 2001-2026, but the SAME piece
     recurs, verbatim, as one side of a ", and " split in >=2 DIFFERENT rows, with the
     OTHER side resolving (directly or by further splitting) to known rows every time. Two
     independent sightings of the identical clause is strong evidence it names a real,
     distinct commemoration the source just never happened to publish solo -- e.g. "The
     Holy Virgins Juliana and Basilla" is never alone in the cache, but shows up prefixed
     to two otherwise-unrelated rows verbatim. Mining is intentionally restricted to ", and
     "/"; and " (never a bare ", " or " and ") -- those are the only connectors that
     reliably mean "the source glued two independent commemorations" rather than sitting
     inside one saint's own name ("Joachim and Anna") or an Oxford-comma list (the Twelve
     Doctors). Mining also runs to a fixed point: a newly mined piece can itself unlock
     further splits (this is how "Theodoron the Martyr" -- the tail of an "and" list, so it
     never carries its own "Saint" -- was found sitting inside a row that ALSO glues on
     "The Holy Virgins Juliana and Basilla").

A mined piece that is just an existing row's text missing its title ("Theodoron the
Martyr" vs. the row "Saint Theodoron the Martyr") is folded into that row via
``TITLE_ALIASES`` rather than kept as a separate one -- same person, same review question.

Every atomic row's ``days``/``last`` are summed/maxed across EVERY occurrence, standalone
or embedded, so the count reflects true commemoration frequency (Theodoron: 4 standalone +
18 combined-with-Abraham's-group + 4 combined-with-Juliana's-group = 26, i.e. every year).

This file is DERIVED, not a second ground truth: review and edit ``approved``/``note`` in
the ATOMIC file, then hand-apply the same edit to the matching row(s) in
``feast_name_review.tsv`` (by ``source``) before registering fixes -- ``tests.
test_feast_name_review`` only ever reads the parent file. A row synthesized purely from
mining (never attested alone) has no independent Armenian witness, so its ``armenian``
column is left blank with a note.

Once atomic names are approved, the glued rows need their OWN registered fix in
the row's ``approved_en``: replace the source's ", and " (or whichever
connector) with ``armenian_lectionary.engine._FEAST_SEP`` (an em dash, " -- " here only
because this docstring is plain ASCII) between the two approved atomic names. That is a
separate, later step -- this script only produces the file to review against.

Usage:
    python dev/feast_name_review_atomic.py             # write the atomic-view TSV
"""

import collections
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.feast_name_review import (                                    # noqa: E402
    FIELDS, HERE, armenian_map, build_rows, corrected, source_components,
)

ATOMIC_PATH = os.path.join(HERE, "feast_name_review_atomic.tsv")

# Only these connectors reliably mean "the source glued two independent commemorations".
CONNECTORS = (", and ", "; and ")

# mined piece -> the existing row it is the same person/group as, just missing a title.
TITLE_ALIASES = {
    "Theodoron the Martyr": "Saint Theodoron the Martyr",
}

# Rows that are NOT textually identical but name the same saint(s) in different wording
# across different years -- found by comparing each row's significant proper-noun tokens.
# Left as separate rows (the text differs, unlike TITLE_ALIASES) but cross-flagged for
# review: is this the source being inconsistent, or two genuinely distinct occasions?
CROSS_REFERENCE_PAIRS = (
    ("Saint Virgins Juliana and Basilla", "The Holy Virgins Juliana and Basilla"),
    ("Saints Cornelius the Centurion, Simeon the Relative of Christ, martyred in "
     "Jerusalem, Polycarp the Bishop of Smyrna, and the Martyrs that perished in the East",
     "Saints Cornelius the Centurion, Simeon, martyred in Jerusalem, Polycarp the Bishop "
     "of Smyrna, and the Martyrs that perished in the East"),
    ("Saints Gregory and Nicholas the Wonderworkers, and other Nicholas the Bishop and "
     "Myron the Bishop",
     "Saints Gregory the Wonderworker, Nicholas the Bishop and Myron the Bishop"),
)


def _split_points(s):
    for glue in CONNECTORS:
        idx = s.find(glue)
        while idx != -1:
            left, right = s[:idx], s[idx + len(glue):]
            if left and right:
                yield left, right
            idx = s.find(glue, idx + 1)


def _is_full(s, vocab, memo):
    if s in memo:
        return memo[s]
    if s in vocab:
        memo[s] = True
        return True
    memo[s] = False  # guard recursion
    for left, right in _split_points(s):
        if _is_full(left, vocab, memo) and _is_full(right, vocab, memo):
            memo[s] = True
            return True
    return False


def mine_atomic_fragments(base):
    """Fragments that recur (verbatim) as one side of a ", and "/"; and " split across
    >=2 different base rows, with the other side always resolving to base -- run to a
    fixed point. Returns the set of newly discovered atomic fragment texts."""
    vocab = set(base)
    discovered = set()
    while True:
        memo = {}
        left_cand = collections.defaultdict(set)
        right_cand = collections.defaultdict(set)
        for s in base:
            for left, right in _split_points(s):
                if _is_full(right, vocab, memo) and left not in vocab:
                    left_cand[left].add(s)
                if _is_full(left, vocab, memo) and right not in vocab:
                    right_cand[right].add(s)
        new = {f for f, rows in left_cand.items() if len(rows) >= 2}
        new |= {f for f, rows in right_cand.items() if len(rows) >= 2}
        if not new:
            return discovered
        discovered |= new
        vocab |= new


def leaves(s, vocab, memo):
    """Fully decompose ``s`` into its atomic leaf texts (title-aliased), using ``vocab``
    (base rows + mined fragments) as the set of valid split points."""
    if s in memo:
        return memo[s]
    full_memo = {}
    for left, right in _split_points(s):
        if _is_full(left, vocab, full_memo) and _is_full(right, vocab, full_memo):
            result = leaves(left, vocab, memo) + leaves(right, vocab, memo)
            memo[s] = result
            return result
    result = [TITLE_ALIASES.get(s, s)]
    memo[s] = result
    return result


def build_atomic_rows():
    rows, _drift = build_rows()
    by_source = {r["source_en"]: r for r in rows}
    days, last = source_components()
    base = set(days)

    mined = mine_atomic_fragments(base)
    vocab = base | mined

    leaf_memo = {}
    leaf_days = collections.Counter()
    leaf_last = {}
    leaf_origin = collections.defaultdict(set)   # atomic leaf -> raw rows it came from
    for s in base:
        for leaf in set(leaves(s, vocab, leaf_memo)):
            leaf_days[leaf] += days[s]
            if leaf not in leaf_last or last[s] > leaf_last[leaf]:
                leaf_last[leaf] = last[s]
            leaf_origin[leaf].add(s)

    hy = armenian_map()
    atomic_rows = []
    for leaf in sorted(leaf_days):
        prior = by_source.get(leaf)
        if prior is not None:
            row = dict(prior)
            row["days"] = leaf_days[leaf]
            row["last"] = leaf_last[leaf]
        else:
            approved = corrected(leaf)
            row = {
                "status": "ok",
                "days": leaf_days[leaf],
                "last": leaf_last[leaf],
                "source_en": leaf,
                "id": "",
                "approved_en": approved,
                "source_hy": hy.get(leaf, ""),
                "approved_hy": hy.get(leaf, ""),
                "note": ("" if hy.get(leaf) else
                         "inferred atomic unit (never published alone in 2001-2026; "
                         "recurs verbatim inside >=1 combined-day rows) -- no independent "
                         "Armenian witness"),
            }
        atomic_rows.append(row)

    by_atomic_source = {r["source_en"]: r for r in atomic_rows}
    for a, b in CROSS_REFERENCE_PAIRS:
        ra, rb = by_atomic_source.get(a), by_atomic_source.get(b)
        if ra is None or rb is None:
            continue  # one side got folded elsewhere (e.g. a TITLE_ALIAS); nothing to flag
        for r in (ra, rb):
            other = b if r is ra else a
            note = (f"possible duplicate: same saint(s) worded differently elsewhere in "
                    f"the corpus -- see the \"{other}\" row. Same commemoration "
                    "published inconsistently across years, or genuinely two different "
                    "occasions?")
            r["status"] = "review"
            r["note"] = (r["note"] + " | " + note) if r["note"] else note

    return atomic_rows, mined, leaf_origin


def main():
    atomic_rows, mined, leaf_origin = build_atomic_rows()
    write_path(atomic_rows)
    print(f"wrote {ATOMIC_PATH}")
    print(f"{len(atomic_rows)} atomic rows ({len(mined)} newly mined, not present as their "
          "own row in dev/feast_name_review.tsv):")
    for f in sorted(mined):
        canon = TITLE_ALIASES.get(f, f)
        print(f"  {f}" + (f"  [folded into existing row: {canon}]" if canon != f else ""))
        for r in sorted(leaf_origin[f]):
            print(f"    from: {r}")


def write_path(rows):
    with open(ATOMIC_PATH, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, delimiter="\t",
                            lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
