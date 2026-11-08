**[Q1] Complete references for the benchmarks**
Answer: GitHub families: the pinned public snapshot `helmo/github-issues` (helmo, 2025), revision e344be7b. BIRD (Li et al., 2023a), release dev_20240627. NESTFUL (Basu et al., 2025). AppWorld gold solutions and released agent runs (Trivedi et al., 2024). API-Bank (Li et al., 2023b). BFCL v4 (Patil et al., 2025). AgentHop (Park et al., 2026), development gates only. In the main results no model runs on NESTFUL, AppWorld, API-Bank or BFCL v4; they are compiler substrates.
Changed: Section 4 cites each; Table 16 (Table 11 in the reviewed version) specifies the GitHub tasks; Appendix F.4 maps every external benchmark to its use.
Evidence: Table 20; NESTFUL supplies 1,415 traces.
Still open: Nothing further is claimed.

**[Q2] Which 92-group labels include downstream answer errors?**
Answer: None. Every 92-group label comes from `grc/compile.py::_calibration_samples`, which replays the frozen program over the group's recorded tool results and, after verifier success, compares outputs with the recorded ones; the continuation never runs. The supported loss is the replay-contract violation of the compiled region, and the guarantee is a per-candidate replay bound (0 violations in 92 groups, U = 0.0498) under i.i.d. groups from the selected population.
Changed: Section 2; Appendix C "Calibration labels as computed"; Table 6 (Table 4 in the reviewed version) and Table 28 name each certificate's event.
Evidence: answer-level misses are measured on held-out records instead: 1/270 compiled-only misses on excerpt-bearing contracts across 810 compiled episodes (Section 7).
Still open: Final-answer labels exist only for PR-outcome (W4).

**[Q3] Account for every excluded record and the guard's verdict**
Answer: Yes. Of 132 discovery records per family (396 in total), issue-type routing excludes 2 inexact runs and leaves 14 eligible records unused, PR-outcome excludes 1 and leaves 15 unused, and backlog routing excludes none and leaves 16 unused after the 16/8/92 train/development/calibration allocation. Every assigned calibration group has a matching labeled window. The three excluded records (#539, #2781, #5700) pass the saved entry guard and gate under compatible manifest pins, so the deployed guard would not reject them.
Changed: Appendix G "Calibration population audit".
Evidence: `paper/results/calibration_population_audit/report.json`, produced by `paper/scripts/audit_calibration_population.py`; 396/396 records.
Still open: These are failed baseline answers, not observed failures of a compiled continuation; the repair is in W5.

**[Q4] Triggers for recompilation or retirement; calibration before reactivation**
Answer: Implemented: rejection of any incompatible manifest (a pinned model, prompt, tool, policy, effect catalog or snapshot changes), preset expiry, explicit retirement, rollback, a kill switch and staged promotion. No implemented trigger reacts to accumulating failures or to a distribution change that passes existing guards. Proposed, not evaluated: suspend on a confirmed committed contract violation or an invalidated pin; audit outcomes and fallback rates against a prospectively specified rule; reactivate only as a new version with a declared population, frozen candidate and loss, and fresh disjoint calibration including failed baseline runs.
Changed: Appendix D paragraph "Implemented lifecycle controls and proposed renewal policy"; one sentence in Section 7.
Evidence: `paper/results/time_forward/pr_outcome/`: on a new snapshot the retained artifact abstained on 60/60 fresh test PRs, and a re-derived version was admitted only after fresh calibration on 132 groups.
Still open: Nothing beyond the proposed policy is claimed.

**[Q5] Define the content-addressed execution manifest**
Answer: Section 2 now reads: "The manifest identifies the prompt, model, tools, policies, and effect catalog by version or content digest; its compatibility pins define which execution environment an artifact may replace." It matters for the episode definition because an episode is evidence for an artifact only under a compatible manifest: dispatch requires equality on every pinned field (Eq. (3)), so a certificate does not transfer to a changed model, prompt, tool or snapshot.
Changed: Section 2 (the reviewed version named the manifest without defining it).
Evidence: Eq. (3); the 60/60 abstentions on a new snapshot in Q4.
Still open: Nothing further is claimed.
