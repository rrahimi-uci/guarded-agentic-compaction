# AWO comparator feasibility spike

**Status: SPIKE COMPLETE. Result: NO-GO.** No provider call, no implementation work, and no
comparator run happened under this document. `prospective-gate-frontier-protocol.md`
pre-registers the bar an executable workflow-compiler comparator must clear before being
built at all: "identical records and model, equivalent execution placement, optimization
overhead accounted separately from deployment metrics, identical cache and ordering
policy, and exact task-contract grading shared with the other two arms," and states
explicitly that "a forced or mismatched comparator would weaken the paper more than
omitting one." This spike checks the first and most basic precondition for clearing that
bar at all: does a fair, official implementation exist to build against.

## What was checked

AWO (Abuzakuk, Kermarrec, Sharma, Veski, and de Vos, "Optimizing Agentic Workflows using
Meta-tools," arXiv:2601.22037, submitted 2026-01-29) is the system
`docs/related-work-matrix.md` and `prospective-gate-frontier-protocol.md` both name as the
closest published candidate: it mines recurring tool-call sequences from agent traces and
transforms them into deterministic meta-tools, reporting up to 11.9% fewer LLM calls and up
to 4.2 percentage points higher task success on two agentic benchmarks.

A public search for an official code release turned up:

- The arXiv abstract and PDF ([arxiv.org/abs/2601.22037](https://arxiv.org/abs/2601.22037)).
- A Microsoft Research publication listing.
- No linked GitHub repository, package, or artifact release from the paper's authors.
- Secondary coverage (a Scribd mirror of the PDF, a ResearchGate listing, an unrelated
  method-summary blog post) that describes the approach but does not host or link to an
  implementation.
- Coverage stating the authors "have indicated they will release AWO as an open-source
  framework," with no release found at spike time.

## Decision

**No-go, per the pre-registered rule, not by discretion.** Building AWO from the paper's
method description alone, without an official reference implementation to calibrate
against, cannot satisfy "identical records and model, equivalent execution placement,
... and exact task-contract grading shared with the other two arms" — there would be no
way to confirm a from-scratch reimplementation actually reproduces AWO's own reported
mining and meta-tool-synthesis behavior rather than a paper author's best guess at it. That
is precisely the "forced or mismatched comparator" the protocol names as worse than
omitting one, and the same reasoning `docs/related-work-matrix.md` already gives for every
comparator this repository declines to build ("no local adapter or same-task comparison is
claimed").

This closes the executable-comparator workstream as **addressed, not abandoned**: the
pre-registered gate was exercised, correctly returned no-go on its first and most basic
precondition, and no forced substitute was built in its place.

## What would reopen this

1. AWO's authors publish an official implementation or evaluation harness.
2. A different published system with a confirmed public reference implementation and a
   comparably close post-trace framing is identified. `docs/related-work-matrix.md`'s
   other `reference`-tier rows (EvoC2F, Agent JIT, COVENANT, JTPRO) were not re-screened
   under this spike's bar; a future revision of the prospective protocol could run this
   same check against any of them before committing to a build.

Neither is authorized or scheduled by this document. It records a completed check, not an
open task.

## Reproduction

This is a documentation-only artifact: the check was a web search and a read of the arXiv
listing, not a script. Re-running it means repeating that search against AWO's current
public presence before assuming this finding is still current; do not treat a NO-GO from
2026-08-22 as permanent without re-checking.
