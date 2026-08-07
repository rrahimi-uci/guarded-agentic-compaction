# GitHub Multirepo PR-Outcome-Core Summary

This note summarizes the new cross-repository, time-forward study executed from
`paper/scripts/github_multirepo_pr_outcome_core.py`.

## Protocol

- Frozen public GitHub snapshots from Hugging Face datasets
- Repository cohort:
  - `huggingface/datasets`
  - `pandas-dev/pandas`
  - `psf/requests`
  - `streamlit/streamlit`
  - `pytorch/pytorch`
- Task:
  - exact `record_number`
  - exact `title`
  - exact PR `outcome` in `{open, merged, closed_unmerged}`
- Discovery protocol:
  - `116` older discovery cases per repository
  - `16` train, `8` dev, `92` calibration
  - `freeze_one_candidate_before_calibration=True`
- Held-out evaluation protocol:
  - `30` balanced time-forward PRs per completed repository
  - conditions:
    - `baseline`
    - `compiled`
    - `template_pre_model`

## Preflight

- Output: `paper/results/github_multirepo_pr_outcome_core/preflight.json`
- All 5 repositories satisfied the frozen time-forward design gate.
- The design supports a pooled `300`-case held-out cohort (`60` per repository).

## Executed provider-backed results

- Top-level output: `paper/results/github_multirepo_pr_outcome_core/results.json`
- Completed held-out repositories:
  - `huggingface/datasets`
  - `pandas-dev/pandas`
  - `psf/requests`
  - `streamlit/streamlit`
- Completed held-out pairs: `120`
- Exact discovery traces:
  - `580 / 580` exact across all 5 repositories
  - `116 / 116` exact in each repository individually
- Held-out exact quality on the 4 completed repositories:
  - baseline: `120 / 120`
  - compiled: `120 / 120`
  - template pre-model comparator: `120 / 120`

## Aggregate paired deltas vs baseline

- Compiled vs baseline on `120` held-out pairs:
  - provider requests: `-44.4%`
  - total tokens: `-52.4%`
  - wall latency: `-49.4%`
  - estimated cost: `-48.6%`
- Template pre-model vs baseline on `120` held-out pairs:
  - provider requests: `-66.7%`
  - total tokens: `-78.6%`
  - wall latency: `-68.1%`
  - estimated cost: `-73.3%`

## Coverage pattern

- The compiled artifact compacted `80 / 120` held-out records.
- All `40` compiled fallbacks were `open` pull requests.
- All `80` compacted records were `merged` or `closed_unmerged`.
- The fixed template comparator compacted `120 / 120` held-out records.

## Fail-closed negative result

- `pytorch/pytorch` reached `116 / 116` exact discovery traces.
- The strict frozen-candidate calibration admitted no artifact and retired the
  repository at compile time.
- The failure is recorded in `results.json` under `repository_failures` and the
  repo-local `discovery_checkpoint.json` is retained.

## Interpretation

- The new evidence materially improves the paper's external-validity story:
  the guarded compiler now has provider-backed, time-forward support across
  multiple independent open-source repositories rather than only one retained
  repository snapshot.
- The evidence also sharpens the claim boundary:
  the learned artifact is conservative, class-selective, and not as efficient as
  a fixed ungated two-read template on this simplified task.
- The `pytorch/pytorch` retirement is useful scientific evidence rather than a
  failure to hide: the strict protocol can refuse to deploy even after perfect
  discovery accuracy.
