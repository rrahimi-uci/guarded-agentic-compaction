# TraceCompiler and corpora screen: NO-GO for every use

Provider-free (0 calls, $0). Paper: El Yadouni and Li, arXiv 2608.02680 v1. Counts in `screen.json`; parse-only scripts in `scripts/`.

**TraceCompiler as a competing compiler: NO-GO.** No official code or artifact was found (absence not proven; GitHub search was
rate-limited). The paper says its workflow was hand-transcribed because the authors have no IR runtime, and it reports no
cost, no unchanged-agent comparison, no competing systems and no statistical admission. A reimplementation would be a
recency-attribution ablation close to our recurrence-only arm, a mismatched comparator by the repository's own bar.
Smallest next step: ask the authors for the skill package (about 0.5 day); a faithful run would need 5-8 days.

**Corpora as an adaptive-task testbed: NO-GO.**

| Corpus | Key numbers | Why it fails |
|---|---|---|
| T1 (13,500 dialogues, 11 read-only tools) | 225 of 13,500 (1.7%) have 2 or more calls at the first model boundary; 3,425 dialogues share a `search_flights,search_flights` opening only at a later user turn | First calls are gated by later user turns; no tool results in the release; per-turn gold-code grading |
| Hermes-Function-Calling-v1 | Best singleturn opening recurs in 6 of 1,090 examples (floor 92); Glaive has no 2-call entry opening | Nothing recurs; no grader |
| AppWorld (8,190 trajectories) | Best released baseline 48.8% on test_normal; this repo's baselines 1/12 and 2/12 against an 8/12 floor | Fails baseline competence; login is a write barrier |

Limits: read-only labels for Hermes and AppWorld are heuristics; support depends on the independence unit.
