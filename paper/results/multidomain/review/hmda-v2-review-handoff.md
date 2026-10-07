# HMDA macro review handoff for Leila Jalali

**Status:** Corrected materials prepared for independent review. Leila Jalali is the designated reviewer, but no approval has been signed, and no provider call has run. The approval template remains `approved: false` with an empty review timestamp.

## Issue found before approval

The old macro and gold constructor agreed on all 420 records but both misread public HMDA code `1111`. The [public LAR field definitions](https://ffiec.cfpb.gov/documentation/publications/loan-level-datasets/lar-data-fields/) identify `1111` as Exempt for `reverse_mortgage` and `open-end_line_of_credit`; the [2024 filing instructions](https://files.ffiec.cfpb.gov/documentation/2024-hmda-fig.pdf) also identify `1111` as Exempt for the first denial reason. The old output marked the first two fields `NA` and omitted the denial-reason exemption. The retained pool has 39 rows with `1111` in each requested field and 37 with `1111` in `denial_reason-1`, spanning 43 distinct cases.

The old `effect_catalog_digest` covered only the generated macro tool catalog. It did not bind the reviewed `benchmarks/contracts/effects/hmda.yaml` file. The approval check now hashes the source YAML bytes along with the macro catalog, so editing the reviewed effect file changes the expected digest.

## Corrected candidate and checksums

The macro and independent gold constructor now report `EXEMPT` for `1111`, while preserving `NA` and `NOT_APPLICABLE` as distinct states. The retained HMDA gold, pool report, validation report, review bundles, and unsigned approval template were regenerated. The 420 case identities and the frozen snapshot digest remain unchanged. The shared gold-constructor checksum in the vulnerability pool report was refreshed because `benchmarks/gold.py` changed; its retained answers did not change.

| Approval field | Current value |
| --- | --- |
| `implementation_digest` | `c885b7ed0ec88a4d6ebb829e2930115e3f33067bf8126833682cc9577e09c33b` |
| `schema_digest` | `9aa8507c01ba77cbb284826fa298b528f28fa77ab3b2633476cf4d39d2b08c3c` |
| `effect_catalog_digest` | `f30ebb869f2b71b1446ef8179e34e8124283b6b761240c9936ef0ec9d3326edd` |
| `evaluator_digest` | `151a0d8c7e01dfd8ce242a9de512183a9697d8916023b153c003175c29551121` |

The provider-free review bundle reports 420 cases, 420 exact independent-gold passes, and `provider_calls_executed: 0`. This agreement is a check of the two implementations, not independent approval.

The retained gold differs from the previous version in exactly 43 cases, and only in `special_states`. Provider-free multidomain validation passes for the available vulnerability and HMDA pools; SEC remains unavailable. Thirty focused integration and unit tests pass, including retained-row exemption semantics and a byte-change check for the effect catalog digest.

The full Python test suite, release audit, paper artifact validator, Pages build, and package build also pass locally. The Pages build includes the regenerated benchmark explorer; the publication manifest was refreshed after all review artifacts were written.

## Suggested spot checks

- `hmda-2023-5493009TVPZT8PYBF879-885702da0c260b3e`: `1111` in both requested fields and `denial_reason-1` now yields three `EXEMPT` states.
- `hmda-2024-549300N5GF79IZ5Y7G10-532441b632690a70`: denial reasons `3` and `1` retain their distinct labels, with no special state.
- `hmda-2023-X05BVSK68TQ7YTOSNR22-fee080c1842e7277`: denial reason `10` remains `NOT_APPLICABLE`.

Leila should review the exact corrected files, retained rows and gold, schema, effect catalog, and common oracle/runtime path. If she approves, she can copy `hmda-v2-macro-approval.TEMPLATE.json` to `hmda-v2-macro-approval.json`, enter her own timestamp and notes, and set `approved: true` through a PR. Any subsequent digest change requires another review.
