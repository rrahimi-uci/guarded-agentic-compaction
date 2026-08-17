# Mathematical correctness audit

Date: August 17, 2026

Scope: Sections 2--3, Algorithms 1--4, Proposition 1, its appendix proof, and
the registered statistical configuration. The audit checked the ICLR source
against the retained implementation and result artifacts. It changes no
stored experimental number.

## Corrections applied

1. **Risk unit.** The objective previously stated episode-level conditional
   risk while calibration and Proposition 1 bounded an any-violation event over
   independent scenario groups. The objective now defines group admission
   \(D_A\) and group violation \(W_A\) explicitly. These reduce to the episode
   quantities in the reported studies because every group is a singleton.
2. **Dispatch domain and cost.** Dispatch now depends on the future entry state,
   runtime manifest, and external state. The cost of a dispatched attempt
   explicitly includes work spent before a clean fallback, preventing failed
   attempts from being treated as free. Manifest compatibility and the violation
   event are explicit: incidents count as violations, while attested clean
   fallback does not.
3. **Notation collision.** \(V\) remains the output verifier; \(W_A\) is the
   group-level violation event. The family-entropy term is
   \(\mathsf{Ent}(F)\) rather than \(H(F)\), avoiding collision with the hard
   guard \(H\).
   The family-ranking term is also labeled support-weighted rather than an
   expectation because the implementation uses a train-group support count.
4. **Compiler output.** Algorithm 1 now returns the nondominated set of
   per-candidate artifacts rather than claiming the implementation returns the
   first admissible family.
5. **Provenance candidates.** Algorithm 3 now represents witnesses as
   source/transform pairs, deduplicates by source, retains every candidate up
   to the ambiguity cap, and defers the stable binding choice to synthesis.
   Declared literal-only arguments remain explicit constants and are not
   mislabeled as provenance edges.
6. **Calibration selection.** Algorithm 2 counts violations only among members
   that satisfy both the hard guard and score threshold, and returns the
   threshold component of the lexicographic coverage maximum. This removes the
   prior pseudocode ambiguity in which `argmax` returned a pair and ties were
   unspecified.
7. **Rollback semantics.** Algorithm 4 now returns the baseline after an
   execution or verifier failure only when abort-and-attest proves the staged
   attempt reversible. Failed abort or commit is an incident, and the output
   contract names that terminal state explicitly.
8. **Proof conditioning.** The proof now conditions on train/development data,
   defines the i.i.d. group admission/violation pairs, derives the conditional
   binomial law, and applies the union bound only over the frozen threshold
   grid.
9. **Declared literals and null dispatch.** The grounding definition now admits
   only schema-allowlisted literals outside provenance, matching Algorithm 3,
   and the optimization defines zero conditional risk when population dispatch
   probability is zero.
10. **Implemented admission denominator.** Calibration samples now carry the
    result of the frozen hard guard, and the low-level calibrator excludes
    guard-ineligible instances from admission while retaining all source groups
    in the empirical-coverage denominator. A regression test fixes this
    theorem-to-code correspondence.
11. **Candidate/data separation.** The compiler now fits the provenance policy,
    mines support, and ranks candidate families on train groups only. Development
    and calibration graphs are attached only after that ranked list is fixed;
    sealed-test and shadow episodes are never graphed. This repairs an
    implementation path that could otherwise make the nominally fixed candidate
    depend on calibration or test covariates.

## Verified arithmetic

- With \(\alpha=.05\), \(\delta=.10\), and \(|\Lambda|=11\), the first
  zero-violation support that clears the bound is 92 groups:
  \(U(91)=0.05034226>.05\) and \(U(92)=0.04980892\le.05\).
- With \(\delta=.05\), or with a Bonferroni split over two candidate families
  at \(\delta=.10\), the requirement is 106 groups:
  \(U(105)=0.05007086>.05\) and \(U(106)=0.04961041\le.05\).
- The statistics and exact-bound unit tests pass (16/16).

## Remaining theorem boundaries

- Proposition 1 is valid for one candidate fixed before calibration. It is not
  a compiler-wide guarantee for adaptive search across several families.
- Source groups must be i.i.d. from the future-group distribution. Grouped
  splitting does not prove exchangeability or robustness to temporal drift.
- Calibration must label every dispatch-eligible member of a cohort sampled
  independently of baseline recurrence; filtering to groups where the baseline
  already displayed the candidate region would change the target population.
- Group-level and episode-level selective risk coincide for the paper's
  singleton groups, but not generally for unequal multi-episode groups.
- The optimization objective is a design target. The compiler does not prove
  global optimality or an approximation ratio.
- Exact task contracts and the group-risk certificate do not establish full
  semantic equivalence of a later model continuation.

These boundaries are stated in the main text and appendix rather than being
left implicit in this audit note.
