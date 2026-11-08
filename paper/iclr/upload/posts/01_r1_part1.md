Thank you for the detailed reading. Your five questions are answered in Part 2.

**[W1] Introduction hard to follow; issue #4420 lacks context**
Answer: Agreed. The rewritten first page defines the task before the example: "Consider GitHub issue triage, one of three workflow families we study: given an issue number from the public huggingface/datasets snapshot, the agent returns a label-based category, the issue title, and an exact evidence excerpt."
Changed: Abstract and Section 1 rewritten with three one-sentence contributions.
Evidence: Table 2; #4420 is one of 30 held-out issue-type records.
Still open: Nothing further is claimed.

**[W2] No cost-quality comparison with EvoC2F or Agent JIT**
Answer: We ran neither and make no ranking claim against them. EvoC2F has no inspectable implementation (its code endpoint returned HTTP 401), Agent JIT plans web tasks (our SQL adaptation is only a probe), and AWO has no verified public code. The executed alternative is a pre-registered comparison with adapted offline Agent Workflow Memory. We also compared design properties as each paper states them: TraceCompiler, PreAct, EvoC2F, Agent JIT, plan caching and AWM admit artifacts by support floors, test-pass thresholds, condition checks, key matches or one re-run, and none states a finite-sample bound on the violation rate after admission. We concede what those systems do that GAC does not: writes, branches and loops, steps beyond the opening, online adaptation and latency scheduling.
Changed: Sections 2 and 6 and the Appendix G comparison table (with page-cited quotes); Section 5.1 and Table 3 report the AWM study.
Evidence: `experiments/generalization_gate/analysis.json`: GAC meets the five-point noninferiority margin in 5/6 workflow-model cells with 50 to 75% fewer requests.
Still open: A matched compiler-policy comparison is designed, not run (`matched-compiler-candidate-protocol.md`; 6 to 10 working days).

**[W3] Table 2 hard to interpret; compiled-segment quality unclear**
Answer: Table 2 in the reviewed version (now Table 4; all four substrates in Table 20) reports refusal on trace benchmarks where no model runs: feasibility, not answer quality. Compiled-segment quality is measured where a live agent runs: Table 2 and BIRD (Section 5.2).
Changed: Plain-word column names and a one-line key in the caption.
Evidence: Table 20: NESTFUL's largest family has 26 of the 92 supporting groups required, so every family retires.
Still open: Nothing further is claimed.

**[W4] Certified loss includes answer errors; labels are replay-only**
Answer: Correct: the reviewed Section 2 counted continuation errors in the loss, but the 92-group labels came from replay. Those are now stated as replay certificates; end-to-end statements are made only where final answers were executed and graded.
Changed: Section 2 fixes the loss as "verifier-passing replay-output mismatch for the primary bound; final task-contract failure for the end-to-end study"; Section 5.4 and Table 28 separate the two.
Evidence: `time_forward/pr_outcome/certificate.json`: 0/132 end-to-end misses on fresh post-cutoff PRs, U = 0.0173; multi-repository study: k = 3 of n = 760, U = 0.0133.
Still open: The three primary families have replay certificates only.

**[W5] Calibration population is outcome-filtered**
Answer: Confirmed: the exact-trace filter removed issues #539 and #2781 and PR #5700, and all three pass their saved artifact's entry guard and gate. The unfiltered-population claim for the primary bounds is withdrawn. The repair you suggest was run: the multi-repository study samples one PR per author before any outcome is seen and labels every eligible group, failures included.
Changed: Section 4 and Appendix G "Calibration population audit"; new appendix "Unfiltered end-to-end calibration across repositories".
Evidence: `calibration_population_audit/report.json` (396/396 discovery records).
Still open: Issue-type and backlog routing keep the filtered population and the stated limit.

**[W6] Lifecycle: what triggers revision and renewed admission**
Answer: Implemented controls and the proposed renewal policy are now separated; Q4 gives both. SKILL.nb is cited.
Changed: Section 7; Appendix D "Implemented lifecycle controls and proposed renewal policy".
Evidence: `registry/lifecycle.py`; Q4: 60/60 abstentions on a new snapshot.
Still open: No failure-rate trigger, sequential guarantee or measured maintenance benefit is claimed.
