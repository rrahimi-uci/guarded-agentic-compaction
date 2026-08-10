# We Built a Compiler for AI Agents. Its Most Useful Result Was Refusing to Ship

*What happens when you hold agent optimization to the standard we hold everything else to: evidence.*

![Cover: repeated traces pass through a gate that either emits a verified compiled prefix or keeps the baseline agent, with headline reductions of 50-75% requests, 39.5-81.4% tokens, 51.7-73% latency and 32-75.3% cost](images/01_hero.png)

Your agent calls a model. The model calls a tool. The tool returns, and the agent calls the model again — to decide the thing it decided the same way yesterday, and the day before.

That loop is the right design when a workflow is new. At scale it becomes the most expensive way to re-derive a conclusion you already have.

The obvious fix is to replace the repeated part with code. The non-obvious problem is knowing **which** part you are allowed to replace.

## Why this is not a caching problem

It looks like caching. It isn't.

A later tool argument may depend on an earlier observation. A nominally read-only step may carry a hidden side effect. A prefix that replayed perfectly in a hundred traces can still be wrong under a different permission scope, a staleness window, or a contract you never wrote down.

Speed only counts when the faster path is still the *right* path. So we built the compiler that assumes it usually isn't.

## Guarded agentic compaction, in one line

**GAC** is a trace-to-program compiler that converts recurring read-only agent work into deterministic code — and refuses by default.

It compiles a prefix only when typed provenance, effect declarations, manifest compatibility, bounded synthesis, verification, and finite-sample admission *all* line up. Miss any one and the unchanged agent keeps running.

Refusal isn't the failure mode. It's the normal output.

![Five-stage cascade from capture to admit, each stage labelled with the condition that makes it refuse, above a band listing the hard barriers no evidence can override](images/02_pipeline.png)

## What it saved, and what that cost to learn

Across three public-record GitHub workflow families with live provider calls:

- **50–75%** fewer provider requests
- **39.5–81.4%** fewer tokens
- **51.7–73%** lower observed latency
- **32–75.3%** lower estimated cost

Quality held: compiled programs passed **90/90** exact held-out contracts against **89/90** for the unchanged agent.

Here is the part most write-ups would bury. A **hand-written** program also reached 90/90.

So the contribution is not that the compiler beats a careful engineer. It doesn't. It's that the compiler *finds* the opportunity automatically and refuses to ship the ones it can't license — at a stated risk level, without a human reading every trace.

The averages are also the least interesting number. Look at the spread: the issue-type family admits only a shallow two-read prefix and saves least, while the two deeper families run near the ceiling the workload allows. **Admissible depth sets the savings, not the optimizer.**

![Grouped bar chart of reduction versus the unchanged agent across three workflow families and five metrics, showing issue-type routing consistently lowest and the two deeper families near 75-81%](images/03_results.png)

## The result I did not expect

On two public benchmarks — NESTFUL and API-Bank — the compiler recovered provenance, synthesized programs, and replayed them on held-out data with **zero wrong executions**.

Then it admitted nothing at all.

Every recurrent family retired. The largest was backed by 26 groups of evidence where the risk bound required 92.

That single comparison is the whole thesis:

> **Recurrence is a property of a trace. Admissibility is a property of the evidence.**

A system that shipped on synthesis-plus-replay alone would have deployed twelve artifacts it could not certify — and every one of them would have *looked* fine in testing.

![Stage-by-stage table showing NESTFUL and API-Bank clearing every compiler stage with zero wrong executions, beside a bar chart where both families' support falls far below the 92-group requirement](images/04_refusal.png)

## "Isn't this just context compression?"

Fair question, and no.

Context-compression middleware such as [Headroom](https://github.com/headroomlabs-ai/headroom) shrinks what goes *into* a call. It reports large token reductions on similar workloads — but it never removes a model turn, so it cannot reduce provider requests at all.

Compaction removes the turn and leaves the payload alone. Different axis, and the two compose.

The honest caveat: our numbers compare against an *uncompressed* baseline, so read the token reduction as the part attributable to removing model boundaries.

![Side-by-side comparison: compaction greys out model turns while keeping payload sizes, compression keeps every turn while shrinking payloads, with a band noting the uncompressed-baseline caveat](images/05_compaction_vs_compression.png)

## What we are not claiming

No semantic equivalence. No production certification. No automatic API fusion. No universal superiority over code a competent engineer would write.

We also ran a bounded trial of a learned prompt optimizer on the same workload. It spent 59 provider requests and selected no change. We reported that too.

## The takeaway for anyone shipping agents

Don't optimize every boundary. Optimize the boundaries evidence can license, and preserve the baseline everywhere else.

And when you evaluate an agent optimizer — yours or a vendor's — ask the question the benchmark won't:

**What does it refuse to do, and what happens when it's wrong?**

An optimizer that never declines isn't confident. It's unmeasured.

![Three cards summarising what guarded agentic compaction keeps with the model, what it shifts to deterministic code, and what it refuses to ship](images/06_takeaway.png)

---

**The full paper**, code, data manifests, and every retired candidate are open:
[github.com/rrahimi-uci/guarded-agentic-compaction](https://github.com/rrahimi-uci/guarded-agentic-compaction)

*From Traces to Guarded Programs: Evidence-Gated Compilation of Recurrent Agent Workflows* — Reza Rahimi, JazzX AI.

**Curious where others land:** if you're running agents in production, what share of your model turns do you think are genuinely re-deriving a known answer? I'd guess most teams are surprised by the number.
