# HMDA macro review: what the independent reviewer checks and how to sign

Written for a colleague who did not write the comparator. Takes about an afternoon; no project
knowledge needed. The study (`hmda-real-records-2026-10`, protocol digest `44843ccb…`) compares
the unchanged agent, a compiled program and a hand-written macro on 420 public HMDA lender
records. It is fair only if someone other than the macro's author confirms the macro and the
grader are fair. The runner refuses an approval whose reviewer matches the author.

## Read these five files, in order

| File | What it is | What to look for |
|---|---|---|
| `benchmarks/adapters/hmda_public_lar.py` | Loads the records into the frozen snapshot; defines `hmda_macro`, the hand-written baseline | Reads only through the declared read-only tools; no access to gold or grader; a careful engineer's solution, neither sabotaged nor test-aware |
| `benchmarks/gold.py` (`hmda_gold_from_records`) | Builds the gold answer directly from the normalized record | Shares no code path with the macro; field logic matches the schema; spot-check three records by hand |
| `benchmarks/contracts/hmda_record.schema.json` | The answer schema every arm must satisfy | Asks for the task's fields; nothing only one arm could produce; no protected demographic field |
| `benchmarks/contracts/effects/hmda.yaml` | The effect catalog | Every tool is `READ_LOCAL`; keys name the snapshot digest |
| `benchmarks/oracles.py`, `benchmarks/runtime.py` | The grader and the runtime that gives each arm its tools | Grader treats all arms identically; the macro arm gets only its one declared tool and the same records |

## Spot-check three records

Records: `paper/results/multidomain/preflight/hmda/{cases.jsonl,gold.jsonl,report.json}`. Pick three
cases, find their gold lines, confirm the gold fields follow from the record. The provider-free
agreement check (no network, no model):

```
PYTHONPATH=src .venv/bin/python -c "from guarded_agentic_compaction.cli import main; import sys; sys.argv=['gac','benchmark','prepare-macro-review','--pool','hmda=paper/results/multidomain/preflight/hmda','--out','/tmp/hmda-review-check.json']; raise SystemExit(main())"
```

Expected: 420 cases, 420 exact independent gold passes, `provider_calls_executed: 0`. Agreement is
evidence, not proof: two implementations can agree and both be wrong the same way.

## Checklist

- [ ] The macro uses only the declared read-only tools and nothing from the gold or grader.
- [ ] The macro is a reasonable engineer's solution, neither sabotaged nor given test-specific knowledge.
- [ ] The gold constructor is independent of the macro; its field logic is correct on three records checked by hand.
- [ ] The schema asks for the task's fields and exposes no protected demographic field.
- [ ] Every tool in the effect catalog is a pinned read.
- [ ] The grader treats all three arms identically.
- [ ] The provider-free check reports 420 of 420 with zero provider calls.

## How to sign

1. Copy `hmda-v2-macro-approval.TEMPLATE.json` (this folder) to `hmda-v2-macro-approval.json`.
2. Fill in `reviewer` (your name; must differ from the author), `reviewed_at` (ISO-8601 with a
   timezone, e.g. `2026-10-09T15:00:00+00:00`), `approved: true`, and `notes` (what you checked).
3. Leave the four digest fields alone; the runner recomputes them and refuses a mismatch:
   `implementation_digest f81fd5e3…`, `schema_digest 9aa8507c…`, `effect_catalog_digest 5706c995…`,
   `evaluator_digest 943c5150…`.
4. Hand the file back; the author commits it through a pull request, and the run starts only then.

## If something is wrong

Do not sign. Send the author a short note of what you found. A flaw in the macro or the gold
constructor must be fixed and the digests regenerated before anyone signs. "Not yet" is a normal
outcome of this review.
