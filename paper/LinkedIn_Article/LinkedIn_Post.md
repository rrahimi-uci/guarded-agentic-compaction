# Companion feed posts

A LinkedIn article gets very little organic distribution on its own — the feed post
that points at it is what actually travels. These are ready to paste.

**Mechanics that matter more than the wording:**

- The first ~200 characters are all that shows before "…see more". Everything below
  that line has to earn the click, so no preamble and no throat-clearing.
- Put the article link in the **first comment**, not the post body. A post with an
  outbound link in the body is served to fewer people; posting the link as your own
  first comment costs nothing and keeps reach.
- Attach `images/01_hero.png` to the post itself. An image post outperforms a bare
  link preview, and the hero already carries the headline numbers.
- Three to five hashtags, at the end, not sprinkled inline.
- Reply to every comment in the first two hours. That window sets how far it goes.

---

## Post A — the refusal hook (recommended)

> We built a compiler that turns repeated AI-agent work into deterministic code.
>
> On two public benchmarks it recovered the logic, synthesized the programs, replayed them on held-out data with zero wrong executions —
>
> and then refused to ship a single one.
>
> Every recurrent family retired. The largest had 26 groups of supporting evidence where the risk bound needed 92.
>
> That gap is the whole finding. Recurrence is a property of a trace. Admissibility is a property of the evidence. A system that shipped on "it replayed correctly" would have deployed twelve artifacts it could not certify — and all twelve would have looked fine in testing.
>
> Where the evidence *did* hold, on three live GitHub workflows: 50–75% fewer provider requests, 39.5–81.4% fewer tokens, quality holding at 90/90 exact outcomes.
>
> The part I'd normally be tempted to leave out: a hand-written program also hit 90/90. So the contribution isn't beating a good engineer. It's finding the opportunity automatically and declining the ones it can't license.
>
> Full paper, code, and every retired candidate are open. Link in the comments.
>
> \#AIAgents #LLMOps #MachineLearning #SoftwareEngineering #AIEngineering

## Post B — the cost hook

> Most teams running AI agents are paying a model to re-derive answers it already has.
>
> Your agent calls a model, the model calls a tool, the tool returns — and the agent calls the model again to decide the thing it decided the same way yesterday.
>
> That loop is correct when a workflow is new. At scale it's the most expensive way to reach a conclusion you already reached.
>
> We compiled the repeated read-only part into deterministic code and measured it on three live GitHub workflows: 50–75% fewer provider requests, 39.5–81.4% fewer tokens, 32–75.3% lower cost, quality holding at 90/90.
>
> The hard part wasn't the speedup. It was proving which part we were *allowed* to replace — a later argument can depend on an earlier observation, and a "read-only" step can carry a side effect nobody declared.
>
> So the compiler refuses by default. On two public benchmarks it refused everything, and that turned out to be the most useful result in the paper.
>
> Link in the comments.
>
> \#AIAgents #LLMOps #AIEngineering #MLOps #SoftwareArchitecture

## Post C — short, for reshares

> An AI-agent optimizer that never declines isn't confident. It's unmeasured.
>
> We built a trace-to-program compiler whose normal output is refusal. On two public benchmarks it synthesized programs that replayed with zero wrong executions — then admitted none of them, because 26 groups of evidence don't clear a bound that needs 92.
>
> Where the evidence held: 50–75% fewer provider requests at 90/90 exact outcomes.
>
> Paper and code in the comments.
>
> \#AIAgents #LLMOps #AIEngineering

---

## First comment (all three variants)

> Paper, code, data manifests, and every retired candidate:
> https://github.com/rrahimi-uci/guarded-agentic-compaction
>
> The article walks through why compaction and context compression are different axes, and where this approach stops working.

## Claim hygiene

The same two statements are load-bearing in the posts as in the article, and neither
survives being trimmed for length:

- Hand-written programs also reach 90/90, so the contribution is automated discovery
  and calibrated admission — not universal superiority.
- The reported reductions compare against an *uncompressed* baseline.

Post C omits the hand-written comparison for length. That is acceptable only because
it makes no superiority claim to qualify; if you add one, add the caveat with it.
