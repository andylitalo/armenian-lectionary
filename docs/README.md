# Lectionary documentation

Primary-source rubrics and liturgical rules behind the Armenian lectionary engine.

The engine (`lectionary.py`) reproduces the Armenian Church's readings by *algorithm*,
but the algorithm encodes rules that originate in the authoritative liturgical books —
chiefly the **Տօնացոյց** (*Tōnats'oyts'*, the Calendar/Typikon) and the **Ճաշոց**
(*Chashots*, the Lectionary). This directory preserves the relevant primary-source
passages, with provenance, so each modeling decision can be traced back to the rubric
that governs it.

## Contents

| File | Source | What it governs |
|------|--------|-----------------|
| [`sources/tonatsooyts-annunciation-canon.md`](sources/tonatsooyts-annunciation-canon.md) | Տօնացոյց, pp. 482–483 | The Annunciation (Apr 7) + its eve (Apr 6): the deterministic collision rule by which the feast's readings combine with the movable Lent / Holy Week / Eastertide day it lands on. |

## Why these matter to the engine

A passage is recorded here when it explains an otherwise-opaque modeling rule —
especially the "embedded irregular feasts" whose readings *looked* unpredictable to a
cross-year statistical build but are in fact prescribed by a rubric. The Annunciation
canon is the first such case: it turns the single largest residual block of
`algorithmic-estimate` days (Apr 7 + Apr 6, ~55 days in the 2001–2026 cache) into a
computable **composite** — see `lectionary.py` (`_annunciation_composite`) and the
audit in `reports/certainty_2027.md`.
