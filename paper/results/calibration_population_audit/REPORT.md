# Primary calibration population audit

Provider-free retrospective reconstruction; no new certificate or final-answer experiment.

All 396 primary discovery records are accounted for, including eligible unused records. All candidates reaching calibration are included, not only the selected artifacts.

| Family | Discovery | Filter-excluded | Eligible unused | Train / dev / calibration |
|---|---:|---:|---:|---|
| issue_type | 132 | 2 | 14 | 16 / 8 / 92 |
| pr_outcome | 132 | 1 | 15 | 16 / 8 / 92 |
| backlog_attention | 132 | 0 | 16 | 16 / 8 / 92 |

| Candidate | Selected | Labeled groups | Missing calibration windows | Excluded records passing entry guard and gate |
|---|---|---:|---|---|
| issue_type / `cand-01-1ebb8b2849c7` | True | 92 | [] | [539, 2781] |
| pr_outcome / `cand-00-a1de3856bb6c` | True | 92 | [] | [5700] |
| pr_outcome / `cand-01-4ea713b44da7` | False | 92 | [] | [5700] |
| backlog_attention / `cand-00-99f1b041ed7c` | True | 92 | [] | [] |
| backlog_attention / `cand-01-2f2e9a7272f7` | False | 92 | [] | [] |

## Interpretation and limits

Selected programs reproduce the retained programs. Guard and gate reproduction is reported separately in JSON: current code can induce different hulls from historical code. For selected artifacts, eligibility and replay relabeling use the **retained registry's** guard, verifier and gate, not a replacement produced by current compilation. Other calibrated candidates are explicitly labeled current-code reconstructions. Split/window membership is reconstructed from the retained checkpoints; replay labels are recomputed, not newly observed provider outcomes. Eligibility uses each original entry state/date, under compatible manifest/catalog pins. It is a dispatch-precondition diagnostic, not execution of the substituted agent or proof of a final-answer failure.

Excluded baseline failures can pass these preconditions. Their absence from calibration cannot be justified by claiming the deployed guard necessarily excludes them. Historical replay labels must not be promoted to end-to-end labels, and this audit does not certify the unfiltered deployment population. Eligible records deliberately unused by the split are reported separately; their non-use is not itself evidence of outcome filtering.

This audit covers the three primary GitHub discovery cohorts and their calibrated candidates. It does not establish population validity for every supplementary benchmark, independence of issue groups, or the outcomes of missing counterfactual continuations.

## Reproduction

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python paper/scripts/audit_calibration_population.py build
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python paper/scripts/audit_calibration_population.py verify
```

Build uses the retained checksum-verified public snapshot and reconstructs historical splits and replay labels. Verify checks shipped source hashes and accounting without fetching data or making model calls. `report.json` includes every record and candidate.
