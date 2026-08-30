# Why `_tier_generative_saint` still exists, and what it serves

`_tier_generative_saint` wins on **no date** in `MIN_YEAR`–`MAX_YEAR`. It applies on 1,904
days and is shadowed on every one — 1,835 by `_tier_validated_table`, 69 by
`_tier_cycle_saint`. That reads like scaffolding left behind, and the history half-supports
it: the tier arrived in `485fa26` as part of the generative confidence ladder, whose job
was filling in-range blanks, and `f64284e` ("Add Second-Volume cycle tier: +16
floating-saint days, 0 wrong") took that job away, explicitly because the fixed-order
laydown "is systematically wrong on the floating-saint days."

Its original job is gone. It acquired a different one, and that one is structural.

## Its territory is the complement of two conservatism rules

**The table's two-year rule.** `dev/build_table.py` harvests an anchored keyspace key only
through `_consistent(items, 2)` — two distinct years must agree on the readings. A
liturgical coordinate that occurs exactly once in 2001–2027 is dropped on purpose, however
good the single observation was.

**The Second Volume's truncated pages.** `_CYCLE_SAINTS` covers all 35 possible Gregorian
Easter dates — it is not range-limited — but each cycle carries only the days that
year-type's page actually prints, and the pages stop short. The Easter-`04-11` cycle's last
post-Nativity entry is January 28/29; the Easter-`04-01` cycle holds nine entries in total.

A saint-weekday that falls in both holes is served by neither tier above. That is what
`_tier_generative_saint` covers, and there is nothing beneath it but the empty fallback.

## What it actually serves

Over 2028–2130 — 103 years — it wins on **five days**, collapsing to **two coordinates**:

| coordinate | days | verified by |
|---|---|---|
| `TrSaintMD = cyricus_and_his:07-30` | 2040-07-30, 2108-07-30 | **twin.** 2018-07-30 carries the same coordinate and is served from the validated table. Name and all five readings are byte-identical. |
| `PnSaintMD = gregory_of_theologian:01-30` | 2066-01-30, 2077-01-30, 2123-01-30 | **attestation.** The coordinate occurs nowhere in range, so there is no twin — but the identity's reading set is served on 14 validated-table days in range, and the tier serves exactly that set. |

`2018-07-30` is itself the reason the first coordinate is unstored: it is the *only*
in-range occurrence, so the two-year rule refused it. The engine has seen the right answer
and declined to keep it; the generative laydown reconstructs it.

One detail worth recording, because it looks like a defect and is not. The raw tier result
for 2040-07-30 packs a third canon, `St. Vahan of Goghtn`, which the validated 2018 day does
not carry. `_drop_owned_companions` removes it — Vahan has his own day that liturgical year,
so the preface-Sixth abbreviation warrant does not apply (see
`sources/tonatsooyts-packed-saint-pools.md`). The **served** name matches; the raw tier
result does not. Verification compares the served output for exactly this reason.

## The shadow-agreement rates are about days it does not serve

On its 1,904 shadowed days the tier agrees with what was served on 1,481 (readings) and
1,336 (label). Split by shadower those are 1,470/1,835 against the validated table and
**11/69** against `_tier_cycle_saint`.

That 16% is real, and it is the measurement behind `_tier_cycle_saint`'s own comment. It is
also the wrong denominator for the question "is what this tier serves trustworthy": those
69 days are floating-saint days the cycle tier covers, which is precisely the set this tier
is never allowed to serve. The five days it does serve are not sampled from that set —
they are march continuations past where a page stops, on coordinates no other tier holds.

Reported by `dev/audit_shadowed_tiers.py`; the win days are asserted by
`tests/test_shadowed_tiers.py`, which needs no ground-truth cache and so runs in CI.

## `_tier_fallback`

The ladder's terminator wins on no date in range either, for a different reason — every day
in range is claimed earlier — and it needs no accuracy work, because it claims nothing. It
names the season, serves an empty reading list and flags the day as not yet modeled.
`tests/test_shadowed_tiers.py` pins that: every day it wins must serve no readings, so a
future edit cannot quietly turn the terminator into an unvalidated reading source with no
tier below it to be filtered down to.

It wins 29 days out to 2130, in two clusters, both genuinely unmodeled:

- **2038-02-13** — the Easter-April-25 winter hinge, the extrapolation cliff already noted
  in `dev/certainty_audit.py`'s 2027 report.
- **Wednesday/Friday pairs in early August** of the earliest-Easter years (2042, 2051, 2053,
  2056, 2064, 2067, 2075, 2078, 2080, 2089, 2110, 2113, 2121, 2124) — the
  after-Transfiguration weekly fasts, where no grid slot reaches.

Both are gaps to model, not defects in the fallback. Neither is addressed here.
