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

Live execution has not started. The new pilot requires a separately authorized
estimated-spend ceiling recorded in its checkpoint. The previous experiment's
budget is not silently reused. Execution status and the complete retained live
outcomes will be added after that limit is supplied.
