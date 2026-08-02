# Oratsouyts reconciliation

This is the review queue for places where annual sources, extraction representations, or the current public classifier do not line up. No item in this file is resolved by majority vote. An omitted source marker remains unknown unless a reviewed calendar rule establishes the value.

## Printed-source irregularities

These are accepted records. Alignment uses day-number sequence, so a printed weekday typo or punctuation omission cannot shift later dates.

| Date | Kind | Printed | Independent expectation | Page |
|---|---|---|---|---:|
| 2013-11-18 | printed_weekday | `Դշ` | `Բշ` | 158 |
| 2014-11-17 | printed_weekday | `Դշ` | `Բշ` | 170 |
| 2016-08-02 | printed_weekday | `Բշ` | `Գշ` | 120 |
| 2016-10-13 | mode_period_missing | `ԱՁ` | `.` | 156 |
| 2016-10-27 | printed_weekday | `Գշ` | `Եշ` | 161 |

## Independent extraction disagreements

Poppler layout and raw-order output are intentionally compared. Raw-order text is canonical for semantic clauses only after both streams independently pass the complete-date gate. Full paired excerpts are in the local `.work/oratsouyts/records/<year>.json` files; `audit.json` contains only aggregate counts and example dates.

| Year | Records flagged | Flag counts | Examples |
|---:|---:|---|---|
| 2013 | 154 | `calendar_clause_text`: 154 | 2013-01-01, 2013-01-05, 2013-01-06, 2013-01-07, 2013-01-13 |
| 2014 | 157 | `calendar_clause_text`: 157 | 2014-01-01, 2014-01-04, 2014-01-05, 2014-01-06, 2014-01-07 |
| 2015 | 163 | `calendar_clause_text`: 163 | 2015-01-01, 2015-01-03, 2015-01-05, 2015-01-06, 2015-01-07 |
| 2016 | 178 | `calendar_clause_text`: 178 | 2016-01-01, 2016-01-02, 2016-01-05, 2016-01-06, 2016-01-07 |
| 2017 | 160 | `calendar_clause_text`: 160 | 2017-01-05, 2017-01-06, 2017-01-07, 2017-01-13, 2017-01-14 |
| 2018 | 173 | `calendar_clause_text`: 173 | 2018-01-05, 2018-01-06, 2018-01-07, 2018-01-13, 2018-01-15 |
| 2019 | 150 | `calendar_clause_text`: 150 | 2019-01-01, 2019-01-05, 2019-01-06, 2019-01-07, 2019-01-13 |
| 2020 | 169 | `calendar_clause_text`: 169 | 2020-01-01, 2020-01-04, 2020-01-05, 2020-01-06, 2020-01-07 |
| 2022 | 171 | `calendar_clause_text`: 171 | 2022-01-01, 2022-01-05, 2022-01-06, 2022-01-07, 2022-01-13 |
| 2023 | 166 | `calendar_clause_text`: 166 | 2023-01-01, 2023-01-05, 2023-01-06, 2023-01-07, 2023-01-13 |
| 2024 | 166 | `calendar_clause_text`: 166 | 2024-01-01, 2024-01-05, 2024-01-06, 2024-01-07, 2024-01-13 |
| 2025 | 169 | `calendar_clause_text`: 169 | 2025-01-01, 2025-01-04, 2025-01-05, 2025-01-06, 2025-01-07 |
| 2026 | 172 | `calendar_clause_text`: 172 | 2026-01-01, 2026-01-03, 2026-01-05, 2026-01-06, 2026-01-07 |

## Extraction-level semantic differences

This is the smaller, field-aware view of the text differences above. `raw_only` means raw order retained a positive fact that layout lost; `layout_only` means the reverse; `different` means both produced non-null but unequal values. Raw order remains canonical. Layout may augment saint descriptors only after raw order independently establishes a saints day, preventing broken Marian titles from becoming saints days. Complete paired values and clauses are in local `.work/oratsouyts/reconciliation.json`.

| Year | Records | Field/direction counts | Examples |
|---:|---:|---|---|
| 2013 | 19 | `fast_context:raw_only`: 1, `is_cross_feast:raw_only`: 3, `is_fast_day:raw_only`: 1, `is_marian_feast:raw_only`: 2, `is_saints_day:raw_only`: 1, `saint_classes:different`: 4, `saint_classes:raw_only`: 8 | 2013-01-14, 2013-02-04, 2013-04-28, 2013-05-10, 2013-05-27 |
| 2014 | 22 | `fast_context:raw_only`: 3, `is_cross_feast:raw_only`: 1, `is_fast_day:raw_only`: 2, `is_marian_feast:raw_only`: 4, `is_saints_day:layout_only`: 1, `saint_classes:different`: 3, `saint_classes:layout_only`: 1, `saint_classes:raw_only`: 11 | 2014-02-01, 2014-02-04, 2014-02-18, 2014-02-24, 2014-03-23 |
| 2015 | 29 | `fast_context:raw_only`: 5, `is_cross_feast:raw_only`: 2, `is_fast_day:raw_only`: 1, `is_marian_feast:raw_only`: 5, `is_saints_day:raw_only`: 1, `saint_classes:different`: 4, `saint_classes:layout_only`: 1, `saint_classes:raw_only`: 11 | 2015-01-15, 2015-02-03, 2015-02-09, 2015-03-01, 2015-03-08 |
| 2016 | 39 | `fast_context:raw_only`: 15, `is_cross_feast:raw_only`: 1, `is_fast_day:raw_only`: 11, `is_marian_feast:raw_only`: 4, `is_saints_day:raw_only`: 1, `saint_classes:different`: 4, `saint_classes:raw_only`: 14 | 2016-01-01, 2016-01-14, 2016-01-19, 2016-01-20, 2016-01-22 |
| 2017 | 25 | `fast_context:raw_only`: 3, `is_cross_feast:raw_only`: 2, `is_fast_day:raw_only`: 1, `is_marian_feast:raw_only`: 5, `is_saints_day:layout_only`: 1, `is_saints_day:raw_only`: 1, `saint_classes:different`: 4, `saint_classes:layout_only`: 1, `saint_classes:raw_only`: 10 | 2017-01-14, 2017-01-28, 2017-01-31, 2017-02-20, 2017-03-19 |
| 2018 | 33 | `fast_context:raw_only`: 8, `is_cross_feast:raw_only`: 1, `is_fast_day:raw_only`: 4, `is_marian_feast:raw_only`: 4, `is_saints_day:layout_only`: 1, `is_saints_day:raw_only`: 2, `saint_classes:different`: 4, `saint_classes:layout_only`: 1, `saint_classes:raw_only`: 15 | 2018-01-15, 2018-01-30, 2018-02-05, 2018-02-24, 2018-02-25 |
| 2019 | 18 | `fast_context:raw_only`: 1, `is_cross_feast:raw_only`: 3, `is_fast_day:raw_only`: 1, `is_marian_feast:raw_only`: 3, `is_saints_day:raw_only`: 1, `saint_classes:different`: 4, `saint_classes:raw_only`: 6 | 2019-01-14, 2019-02-02, 2019-02-25, 2019-05-19, 2019-05-31 |
| 2020 | 29 | `fast_context:raw_only`: 7, `is_cross_feast:raw_only`: 1, `is_fast_day:raw_only`: 4, `is_marian_feast:raw_only`: 4, `is_saints_day:raw_only`: 1, `saint_classes:different`: 4, `saint_classes:raw_only`: 12 | 2020-01-14, 2020-02-01, 2020-02-07, 2020-02-11, 2020-02-17 |
| 2022 | 30 | `fast_context:raw_only`: 8, `is_cross_feast:raw_only`: 1, `is_fast_day:raw_only`: 6, `is_marian_feast:raw_only`: 4, `is_saints_day:raw_only`: 1, `saint_classes:different`: 4, `saint_classes:raw_only`: 12 | 2022-01-01, 2022-01-15, 2022-01-29, 2022-02-01, 2022-02-21 |
| 2023 | 26 | `fast_context:raw_only`: 4, `is_cross_feast:raw_only`: 1, `is_fast_day:raw_only`: 4, `is_marian_feast:raw_only`: 3, `is_saints_day:layout_only`: 1, `is_saints_day:raw_only`: 1, `saint_classes:different`: 3, `saint_classes:layout_only`: 3, `saint_classes:raw_only`: 12 | 2023-01-14, 2023-01-28, 2023-02-07, 2023-05-07, 2023-05-19 |
| 2024 | 30 | `fast_context:raw_only`: 7, `is_cross_feast:raw_only`: 1, `is_fast_day:raw_only`: 4, `is_marian_feast:raw_only`: 3, `is_saints_day:raw_only`: 1, `saint_classes:different`: 3, `saint_classes:raw_only`: 15 | 2024-01-15, 2024-01-26, 2024-01-30, 2024-02-05, 2024-03-03 |
| 2025 | 31 | `fast_context:raw_only`: 6, `is_cross_feast:raw_only`: 1, `is_fast_day:raw_only`: 3, `is_marian_feast:raw_only`: 4, `is_saints_day:raw_only`: 2, `saint_classes:different`: 3, `saint_classes:raw_only`: 16 | 2025-01-14, 2025-02-01, 2025-02-04, 2025-02-14, 2025-02-18 |
| 2026 | 34 | `fast_context:raw_only`: 10, `is_cross_feast:raw_only`: 1, `is_fast_day:raw_only`: 6, `is_marian_feast:raw_only`: 5, `is_saints_day:raw_only`: 1, `saint_classes:different`: 4, `saint_classes:raw_only`: 13 | 2026-01-15, 2026-01-28, 2026-01-29, 2026-02-03, 2026-02-09 |

## Annual canonical-occurrence presence variations

These rows mean a reviewed occurrence matcher found a feast or memorial in some annual clauses but not all available years. Possible causes include a collision, transfer, editorial wording, or matcher coverage. Absence is not automatically false.

| Occurrence ID | Present years | Missing years | Counts by year |
|---|---|---|---|
| — | — | — | — |

## Source-fact variants under one canonical runtime identity

These are positive source assertions that differ even though the current English runtime identity is the same. They require either an era/occurrence variant or a correction to the canonical identity; merging their values would erase source information.

| Runtime identity | Field | Source variants |
|---|---|---|
| Holy Fathers Saints Athanasius and Cyril of Alexandria | `saint_classes` | `['hierarch']` in 2013, 2014, 2016, 2017, 2019, 2020, 2022, 2023, 2024, 2025; `['hierarch', 'vartapet']` in 2018 |

## April 24 editorial change point

This fixed commemoration is a concrete reason not to flatten thirteen years into one majority value. The source wording changes by era; that change must remain explicit in any canonical rule.

| Year | Holy-martyrs wording | Explicit requiem | Rest-hymn rubric | Source excerpt |
|---:|---|---|---|---|
| 2013 | no | yes | no | 24 † Դշ. ԱՁ. ԻԵ. օր Յինանց։ Օրհ. աձ. Երգեսցուք երգ: Հրց. բկ. Ե. Կամաւորութեամբ: Ղկ. 10.1-24։ Գրծ. 14.18-27։ Բ. Պտ. 1.20-2.8։ Յհ. 6.15-21։ Մտ. 12.38-50։ Մր. 5.35-43։ Հմբ. աձ. Որ ան… |
| 2014 | no | yes | no | 24 † Եշ. ԳՁ. Ե օր Ս. Զատկի: Օրհ. գձ. Իւղաբեր եւ սուրբ: Հրց. աձ. Դ. Ընդ երիս մանկունսն: Գրծ 4.13—31։ Յկ. 1.13—27։ Մտ 5.1—12: Հմբ. գձ. Իւղաբեր եւ սուրբ կանայք: 99-րդ տարելից Մեծի Եղ… |
| 2015 | no | yes | no | 24 † Ուր. ԲԿ. Ի օր Յինանց: Օրհ. բկ. Փարաւօն հանդերձ: Հրց. բձ. Զ. Որ զարդարեալ: Գրծ. 4.1331։ Յկ. 1.1327։ Մտ. 5.112։ Հմբ. բկ. Առաւօտեան սուրբ: 100րդ տարելից Մեծի Եղեռնի բիւրաւոր նահ… |
| 2016 | yes | no | yes | 24 † Կիր. ԳՁ. Ե կիր. Տօն Երեւման Ս. Խաչի: Յիշատակ սրբոց նահատակաց մերոց, որք կատարեցան յընթացս Հայոց Ցեղասպանութեանն վասն հաւատոյ եւ վասն հայրենեաց: Ի տեղի Հանգստեան շարականի Նահա… |
| 2017 | yes | no | yes | 24 † Բշ. ԱՁ. Թ օր Յինանց: Յիշատակ սրբոց նահատակաց մերոց, որք կատարեցան յընթացս Հայոց Ցեղասպանութեանն վասն հաւատոյ եւ վասն հայրենեաց: Ի տեղի Հանգստեան շարականի զաւուր օրհ. աձ. Երգե… |
| 2018 | yes | no | yes | 24 † Գշ. ԴԿ. ԻԴ օր Յինանց: Յիշատակ սրբոց նահատակաց մերոց, որք կատարեցան յընթացս Հայոց Ցեղասպանութեանն վասն հաւատոյ եւ վասն հայրենեաց: Ի տեղի Հանգստեան շարականի զաւուր օրհ. դկ. Յաղ… |
| 2019 | yes | no | yes | 24 † Դշ. ԲԿ. Դ օր Զատկի: Յիշատակ սրբոց նահատակաց մերոց, որք կատարեցան յընթացս Հայոց Ցեղասպանութեանն վասն հաւատոյ եւ վասն հայրենեաց: Ի տեղի Հանգստեան շարականի զաւուր օրհ.բկ.Քոյարու… |
| 2020 | yes | no | yes | 24 † Ուր. ԳՁ. ԺԳ օր Յինանց: Յիշատակ սրբոց նահատակաց մերոց, որք կատարեցան յընթացս Հայոց Ցեղասպանութեանն վասն հաւատոյ եւ վասն հայրենեաց: Ի տեղի Հանգստեան շարականի զաւուր օրհ. գձ. Օգ… |
| 2022 | yes | no | yes | 24 † Կիր. ԴԿ. Ը օր Ս. Զատկի: Կրկնազատիկ (Նոր Կիւրակէ): Յիշատակ սրբոց նահատակաց մերոց, որք կատարեցան յընթացս Հայոց Ցեղասպանութեանն վասն հաւատոյ եւ վասն հայրենեաց: Ի գիշերին հսկումն… |
| 2023 | yes | no | yes | 24 † Բշ. ԴԿ. ԺԶ. օր Յինանց: Յիշատակ սրբոց նահատակաց մերոց, որք կա76 ԱՊՐԻԼ Օ Լ 5 6 7 տարեցան յընթացս Հայոց Ցեղասպանութեանն վասն հաւատոյ եւ վասն հայրենեաց: Ի տեղի Հանգստեան շարականի… |
| 2024 | yes | no | yes | 24 † Դշ. ԱՁ. ԻԵ օր Յինանց: Յիշատակ սրբոց նահատակաց մերոց, որք կատարեցան յընթացս Հայոց Ցեղասպանութեանն վասն հաւատոյ եւ վասն հայրենեաց: Ի տեղի Հանգստեան շարականի զաւուր օրհ. աձ. Երգ… |
| 2025 | yes | no | yes | 24 † Եշ. ԳՁ. Ե օր Ս. Զատկի: Յիշատակ սրբոց նահատակաց մերոց, որք կատարեցան յընթացս Հայոց Ցեղասպանութեանն վասն հաւատոյ և վասն հայրենեաց: Ի տեղի Հանգստեան շարականի զաւուր Օրհ. գձ. Իւղ… |
| 2026 | yes | no | yes | 24 † Ուր. ԲԿ. Ի օր Յինանց: Յիշատակ սրբոց նահատակաց մերոց, որք կատարեցան յընթացս Հայոց Ցեղասպանութեանն վասն հաւատոյ և վասն հայրենեաց: Ի տեղի Հանգստեան շարականի զաւուր Օրհ. բկ. Փարա… |

## Current runtime versus explicit positive source facts

This comparison is directional: it reports when the source explicitly says a fact that the current `Calendar` response loses. It does not call source silence a runtime error. The build fails unless this exact set matches `dev/oratsouyts/runtime_reconciliation_allowlist.json`.

| Field | Mismatched source records |
|---|---:|
| `saint_classes` | 1 |

Representative records (the complete list is in `.work/oratsouyts/reconciliation.json`):

| Date | Field | Source | Runtime | Calendar clause |
|---|---|---|---|---|
| 2018-07-28 | `saint_classes` | `['hierarch', 'vartapet']` | `['hierarch']` | Սրբոց հայրապետացն Աթանասի եւ Կիւրղի եւ Գրիգորի Աստուածաբանին: |

## Review decisions still required

- Define the non-Sunday Dominical occurrence taxonomy; never substitute the dagger.
- Consider whether the national memorial attached to Vardanants also needs a narrower subtype; its explicit marker is already retained in public `Is Memorial`.
- Add reviewed canonical identity mappings where a saint class is biographical rather than explicit in the annual title.
- Expand the Armenian descriptor patterns for declined or extraction-spaced forms such as `առաքելոցն` and `միայնակեցւոյն`; the runtime currently derives those classes from the canonical English identity, but the independent source evidence parser does not yet corroborate them.
- Decide whether `illuminator` names only Saint Gregory himself or also his family and descendants. The current English-title matcher classifies the July 25 sons-and-grandsons commemoration because its possessive title contains `Gregory the Illuminator`.
- Reconcile annual omissions of fast markers around Assumption and Cross post-feasts before treating those omissions as negative assertions.
