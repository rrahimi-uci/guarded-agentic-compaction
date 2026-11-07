# ToolHop screen for GAC: NO-GO

Provider-free (0 calls, $0). Source: ToolHop (ACL 2025, arXiv 2501.02506; HF `bytedance-research/ToolHop`,
commit `b439d7279af359fda46e8117ae4f0245b75f5c6b`; data CC BY 4.0). Counts in `screen.json`; scripts in `scripts/`.

| Gate | Result |
|---|---|
| Source, licence, grading | Pass with caveats: lenient substring grading (311 of 995 answers are one character), incomplete requirements, no declared effects, no released arguments |
| Recurrence at 92 groups | **Fail.** No opening reaches 92 queries at tool-name, signature or schema level. Best name-level opening: 73 queries (44 independent groups). All 3,912 function bodies are distinct |
| Entry-to-first-argument derivability | **Fail.** The repo binder bound 0 of 30 entity slots (one constant on a non-entity slot) |
| Dependent arguments | Mixed: 70.8% single-trace expressible, but 0 of 40 previous-tool families bind across traces |
| Batching ceiling vs handwritten | **Fail.** An initial prefix can remove at most 1 of about 4.93 requests (20.3%); a handwritten prefetch with the same entity extractor matches it |
| Populations | Marginal: 286 source-overlapping components; the 92-group floor would use a third of them for one candidate |
| Baseline competence >= 70% | **Fail.** Best published forced-tool score 55.6% (GPT-5.4 54.5%); o3 free-choice 75.7% coincides with 68.4% without tools, pointing to recall |

Tools are GPT-4o-written stubs that embed the stored answer (90.8% of retrieval-named tools). A valid matched study
would need a shared canonical tool library, a semantic entity selector as a method extension, a sealed competence pilot
and 92 or more grouped calibration groups: about 12 working days with a high prior that the handwritten arm ties.
Recommendation: stop at this screen.
