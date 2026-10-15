# Validation and execution status

Provider-free validation completed locally on October 15, 2026 using the existing
repository virtual environment with this worktree's `src` on `PYTHONPATH`.

| Check | Result |
| --- | --- |
| Pilot-specific tests | 22 passed; includes a real SDK loop with a fake repair model |
| Full suite | 604 passed, 3 optional-data tests skipped; 180.09 seconds |
| `live_safeguard_recovery.py prepare` | Sealed 24 issues and 576 episodes; zero provider calls |
| Corresponding `verify` | Source, code, dependency, configuration and dispatcher checks passed |
| Paper artifact validator | 5,277 checks passed, zero failed |
| Release verification | Passed; three existing untracked-docs checks skipped |
| Pages build | Passed; 9 pages, 32 paths |
| Package build | Source distribution and wheel built |
| `git diff --cached --check` | Passed |

The real dispatcher preflight observed 39/144 full dispatches, 117/144 without
the requested-limit hull, and 48/144 without the completeness check. These are
provider-free observations only; no live accuracy or savings follows from them.

The installed SDK exposes a runner-managed retry layer in addition to transport
retries. Both are explicitly disabled and the SDK-loop test checks the former.
The initial unused development seal was replaced before any provider call to
bind this setting explicitly. The final cohort and request design are unchanged.
The final seal is non-overwritable and checked before execution.

The artifact validator's generated historical validation summary was restored.
No existing paper result or production runtime changed. CI and reviewer state
are tracked on the PR separately from these local checks. No independent human
gold attestation or Copilot review is claimed here.

On October 15, 2026 the user separately authorized a **$200 estimated-spend cap**
for this sealed 576-episode pilot. The runner recorded that cap in its checkpoint
before the first provider call. The frozen rate card and $1 episode reserve are
an estimated-spend guard, not a hard provider billing cap or invoice verification.
Execution stopped at attempt 153 with a retained `ValueError`: 152 completed,
one failed, 423 unattempted. Of the completed answers, 151 are correct. Completed
estimated spend is $0.0490666 and the unknown-cost reserve is $1. No retry was
made. See [OBSERVED.md](OBSERVED.md) for the incomplete coverage, adverse outcome
and unresolved failure cause. This is not a completed effectiveness comparison.

Post-run `live_safeguard_recovery.py analyze` passed source regrading, prefetch
and successful continuation-tool replay, response-cost recomputation and request/
tool/token accounting. The separate post-run `verify` command also passed with
the original seal, code and configuration unchanged. Both commands are
provider-free; neither adds live episodes.

Initial implementation commit `e23ed2721af740246e9068a9597348550c2b6dba` passed
GitHub CI on Python 3.11 and 3.14 (run `38803149304`). This status does not
substitute for CI on the later commit retaining the live results.
