# GitHub Copilot repository instructions

- You may work on assigned issues and development tasks, create a branch, and open a pull request. You must never merge a pull request, approve a pull request, push to `main`, or represent your review as human approval.
- Before opening or marking a pull request ready for human review, understand the issue acceptance criteria, implement the smallest complete change, and add or update tests for changed behavior.
- Run the repository CI-equivalent validation: install `.[dev,live,figures]`, run `python -m pytest`, `python scripts/verify_release.py`, `python paper/scripts/validate_artifacts.py`, `python scripts/build_pages.py --output _site`, and `python -m build`. Also run `git diff --check`.
- Keep validation deterministic and offline. Do not require credentials, network services, model calls, or uncommitted local data for ordinary tests.
- Do not submit a PR as ready if a required test, release-evidence check, artifact check, site build, or package build fails. If validation is blocked, keep the PR draft and state the exact blocker and command output in the PR body.
- The PR body must list changed behavior, tests added or updated, every validation command and result, limitations, risks, and publication/deployment implications. Preserve explicit observed, exploratory, refusal, prospective, and unrun evidence labels.
- During code review, identify correctness, security, test-coverage, and evidence-boundary issues and leave comments. Never approve or merge the PR.
