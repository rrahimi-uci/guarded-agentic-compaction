# Matched compiler study: first-phase feasibility and power report

**Decision: NO-GO for confirmatory provider execution; proceed with source acquisition and design preparation.**
No new model calls were made. No final cohort, candidate set, model, numeric spending cap or execution protocol is sealed.
This report is a planning artifact, not new evidence for the paper's performance or a higher review score.

The [prospective protocol](../../supplementary/matched-compiler-candidate-protocol.md) fixes the research questions and decision criteria.
The [machine-readable report](report.json) retains inputs, hashes, assumptions and complete calculations;
[availability.json](availability.json) retains the count-only public GitHub queries.

## 1. Data that are actually present

Each local Parquet file was checked against its retained source checksum. Counts below follow a conservative prior-use screen;
they are not certified fresh cohorts. Unqualified IDs are excluded across repositories, which can over-exclude.
Unrecognized encodings and untracked evidence still need a complete pre-seal lineage audit.
Raw datasets were not mistaken for prior model experiments. The two huggingface snapshots remain separate.

| Repository / snapshot | Unique records | Remaining after screen | PR core source screen | PR excerpt source screen | Issue source screen | Backlog source screen |
|---|---:|---:|---:|---:|---:|---:|
| huggingface/datasets / historical | 7440 | 1325 | 1317 | 1317 | 6 | 0 |
| pandas-dev/pandas / historical | 44536 | 37050 | 20041 | 0 | 0 | 0 |
| psf/requests / historical | 6528 | 1213 | 414 | 0 | 0 | 0 |
| streamlit/streamlit / historical | 4900 | 936 | 494 | 0 | 0 | 0 |
| pytorch/pytorch / historical | 9609 | 9268 | 6827 | 0 | 0 | 0 |
| huggingface/datasets / post-cutoff | 1095 | 406 | 259 | 259 | 146 | 89 |

These screens overlap; issue/backlog counts cannot be added as disjoint cohorts. They do not verify task graders, class balance,
candidate recurrence, full source schemas, or independent groups. Repository replications are not distinct workflow structures.
Four multi-repository mirrors contain comment counts rather than comment bodies. Their existing adapter's synthetic 'comment'
placeholders must not be used as factual excerpt evidence. Those mirrors support only the narrower source screen until complete evidence is acquired.

## 2. Live availability, not acquired evidence

| Repository | Issues since 2025-06-14 | Open issues since 2025-06-14 | PRs since 2025-06-14 | Issues since 2026-10-08 | PRs since 2026-10-08 |
|---|---:|---:|---:|---:|---:|
| huggingface/datasets | 295 | 183 | 940 | 16 | 119 |
| pandas-dev/pandas | 1162 | 261 | 5617 | 69 | 476 |
| psf/requests | 144 | 26 | 475 | 3 | 1 |
| streamlit/streamlit | 988 | 351 | 5064 | 32 | 385 |
| pytorch/pytorch | 10309 | 3130 | 35939 | 520 | 1746 |

Queries captured: 2026-10-29T02:39:54.422703+00:00 through 2026-10-29T02:40:07.551202+00:00.
The broad window follows the original 2025-06-13 snapshot. The recent window follows the last retained API acquisition on 2026-10-07.
Neither window proves record-level non-overlap. Search totals are mutable and are not counts of usable or independent tasks.
No issue bodies, comments or final cohort were acquired by these probes.
[GitHub documents](https://docs.github.com/en/rest/search/search#search-issues-and-pull-requests) incomplete-result flags and a 1,000-result retrieval cap per search.
A full acquisition must paginate repository endpoints or use auditable date partitions, not treat one search page as a complete corpus.

## 3. Prospective power

The quality family has 24 paired contrasts (12 families x two simpler compilers). Planned analysis uses two-sided exact McNemar tests
with Holm correction. These conservative power calculations use 0.05/24 for each test, assuming iid paired groups.
The assumed favorable/reverse discordance probabilities are (3%,1%), (4%,1%) and (6%,1%), respectively. They are assumptions, not measured future rates.

| Test groups per family | Four-arm test episodes | Power: +2 pp | Power: +3 pp | Power: +5 pp | Five-point NI power at 2% comparator-only success |
|---:|---:|---:|---:|---:|---:|
| 300 | 14400 | 4.5% | 15.4% | 55.0% | 28.2% |
| 600 | 28800 | 20.0% | 54.6% | 95.9% | 84.7% |
| 900 | 43200 | 42.1% | 83.4% | 99.8% | 97.3% |
| 1200 | 57600 | 62.5% | 95.2% | 100.0% | 99.8% |
| 1800 | 86400 | 87.9% | 99.8% | 100.0% | 100.0% |
| 2400 | 115200 | 97.0% | 100.0% | 100.0% | 100.0% |

At 300 groups even zero comparator-only losses give a simultaneous upper bound of 2.0369 points: this design cannot establish a two-point margin.
The strict zero-loss minima are 121, 306 and 615 groups for five-, two- and one-point noninferiority, respectively.
At 900 groups, the three-point planning scenario exceeds the 80% per-contrast power target; at 1,200 it reaches about 95%.
Investigate source feasibility at 900–1,200 test groups per family. This range is a planning reference, not a chosen sample size,
not adequate for every two-point scenario, and not a guarantee of joint success across families. Effective cluster counts can be much smaller.
The existing 92-group replay floor is per fixed candidate. Simultaneous correction over 12 fixed candidates and 11 thresholds requires
at least 141 zero-violation groups under alpha=0.05 and delta=0.10. This arithmetic does not establish iid sampling or final-answer reliability.

## 4. Resource reference and scope

The following is a historical frozen-price reference, not a current quote or spending cap. It applies the minimum/maximum observed completed
baseline mean cost across six retained cells to every planned episode. New tool payloads and model settings may have different costs.
Each row adds 5,040 illustrative setup episodes: 12 x (64 train + 32 development + 300 calibration + six pilot records x four arms).
Additional discovery, unknown failed-call charges, acquisition, human work and a separate end-to-end calibration study are excluded.

| Test groups per family | Reference total episodes | Historical cost reference, USD | 5x high reference, USD |
|---:|---:|---:|---:|
| 300 | 19440 | 6.18–17.10 | 85.48 |
| 600 | 33840 | 10.76–29.76 | 148.80 |
| 900 | 48240 | 15.34–42.43 | 212.13 |
| 1200 | 62640 | 19.92–55.09 | 275.45 |
| 1800 | 91440 | 29.09–80.42 | 402.09 |
| 2400 | 120240 | 38.25–105.75 | 528.73 |

No spending is authorized by this report. Current prices, actual discovery volume, pilot token distributions and a failure reserve must inform a later numeric cap.

## 5. What is still required

- Fresh complete source snapshots and a sealed overlap audit have not been acquired.
- Twelve candidate families have not been discovered; repository replications are not distinct workflow structures.
- Compiler-level comparator policies and matched continuation packaging are not implemented.
- Final endpoints, sample sizes and independence assumptions require an executable prospective seal.
- Current provider pricing, execution pilot, failure reserve and study-specific spending cap remain unset.

The current harness offers three task templates plus a narrower PR-core variant. It has not mined twelve fresh candidate families.
The support-only implementation copies an already-admitted registry; it must become a compiler-level policy over the common candidate list.
The first acquisition priority is complete PR evidence from pandas, streamlit and pytorch, where the broad count probes justify investigating volume.
At the illustrative 1,200-test-group design, 64 train + 32 dev + 300 calibration + six pilot records require 1,602 distinct records per unit.
The observed broad-window open-issue pools in pandas and streamlit fall below that count even before exclusions, so a 12-cell grid of the existing
templates must not be assumed feasible. Additional repositories, different legitimate task structures or a prospectively narrower design are needed.
Freeze the acquisition plan before model discovery; acquire source evidence, audit labels/comments/PR state, then mine candidates on training data only.
Do not replace rejected candidates, select families by final accuracy, or extrapolate search counts into an execution-ready cohort.

## Reproduction

From the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python paper/scripts/matched_compiler_feasibility.py build
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider paper/scripts/test_matched_compiler_feasibility.py
```

The local inventory requires the retained optional multi-repository Parquet caches; absent caches are explicitly reported, never downloaded automatically.
The tests use synthetic source fixtures and retained reports, and need no credentials. To collect a new dated count-only availability snapshot,
run the script's `availability` command with a fresh `--out` directory; do not overwrite historical evidence silently.
