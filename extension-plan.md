# Feasible cross-domain extension plan

**Working title:** Evidence-Gated Optimization Across Real Agent Workflows
**Repository baseline:** release 0.6.0 on `main` after canonical-JSONL hardening and MLflow removal
**Reviewed:** 2026-08-04
**Note (2026-08-07):** point-in-time planning record. The baseline below is the
state at review time; the repository has since moved to 0.7.0 and the paper was
retitled. Its numbered invariants remain accurate; its schedule and version
references do not.
**Status:** all currently feasible provider-free code and two real 420-group domains are implemented; SEC acquisition, human approvals, and billable live experiments remain gated and unrun
**Headline scope:** cybersecurity vulnerability evidence, SEC filing reconciliation, and public HMDA mortgage-record interpretation

## 0. Implementation checkpoint — 2026-08-04

This checkpoint distinguishes implemented foundations from planned experiments:

| Area | Current state | Evidence and remaining boundary |
|---|---|---|
| Generic benchmark contracts | **Implemented** | `BenchmarkCase`, `OracleResult`, `FrozenStudy`, and `DomainAdapter` are in `src/guarded_agentic_compaction/evaluation/domains.py`; nested case data is immutable and the frozen split digest participates in compatibility identity. |
| Canonical measurement | **Implemented** | `CanonicalMetrics` rejects conflicting aliases, non-finite/count-invalid values, inconsistent totals, and missing weighted cost at portfolio evaluation. |
| Exact paired analysis | **Implemented** | Conservative exact one-sided paired binary non-inferiority rejects duplicate group identities. |
| Resumable evidence | **Implemented** | The local execution ledger is append-only, hash-chained, fsynced, idempotent by run/event identity, and corruption-tested. |
| Family policy and risk helpers | **Implemented** | Unknown families, compatibility drift, unreviewed macros, invalid serialized booleans, and uncertified selected actions fail closed. Tests recompute the frozen zero/one-event 75-group bounds. |
| Protocol and execution controls | **Implemented, not frozen** | Manifests, schemas, deterministic role/lineage freeze, full case-payload digests, attested artifact checksums, counterbalanced schedules, exact model/pricing/SDK contract, pre-call token-cost ceiling, append-only resume ledger, stage-specific candidate locks, a self-digested portfolio artifact, sealed action/policy binding, and analysis commands exist. The protocol cannot be frozen without all three pools and real pricing. |
| Vulnerability domain | **Implemented and provider-free validated** | 420 lineage-disjoint real PyPI package groups pass 420/420 exact recomputation. The pool reconciles OSV, GitHub Advisory Database, checksum-verified NVD feeds, PyPI versions, and CISA KEV. Its snapshot digest is `2e9912ecb96d5fb15d088977616c8065bb7bea860dd2f0ed25111bfcccc06a32`; 48/420 cases exercise the variable path. |
| HMDA domain | **Implemented and provider-free validated** | 420 independent real public LEI groups from official privacy-modified 2023/2024 LAR data pass 420/420 exact recomputation; 416/420 exercise denial/special-state paths. Protected demographic columns are excluded from agent tools. |
| SEC domain | **Code complete, source gated** | Rate-limited fetch, submissions/Company Facts/filed-XBRL normalization, numeric/context/unit handling, exact macro, schema, and parser/adversarial tests exist. No SEC request or normalized record was created because a compliant `SEC_USER_AGENT` contact is absent. |
| Macro review | **Materials implemented; approval absent** | Provider-free review bundles bind code, prompt, effect catalog, schema, independent gold implementation, and retained artifacts and self-recompute 840/840 available cases. They deliberately set `approved: false`; no independent reviewer evidence is invented. |
| GRC construction and calibration | **Implemented, unrun** | Discovery/development compilation, benchmark-only shadow evaluation, 100-group exact calibration, artifact-wise Bonferroni risk, human promotion, expiry, active-only portfolio/test dispatch, and explicit empty-registry unavailability are implemented. Real provider traces do not yet exist. |
| Live Agents SDK and analysis | **Implemented, not run** | Discovery, development, pilot, artifact calibration, portfolio calibration, sealed test/repeats, exact inference, determinism, effort, amortization, and validation entry points exist. Source-path grading requires complete case-specific tools with matching snapshot/record arguments; undefined zero-baseline ratios are explicit nulls. No OpenAI call or `.env` API-key use occurred for this extension; an approved cap, real pricing/token ceilings, and human approvals remain mandatory. |

The retained provider-free validator reconstructs gold directly from normalized public records,
independently of the candidate macros, and passes **840/840 available real cases** in both the
independent-gold and macro comparisons. It records SEC as explicitly unavailable and reports zero
provider calls. The three-domain preflight remains ineligible by design. Protocol freezing now
binds every case input and metadata value, while source preflight verifies the exact case, gold,
snapshot, and independent-gold code hashes. Validation totals are regenerated after every
documentation and manuscript change. The release gate builds the distribution, checks current
documentation and local links, compiles both LaTeX manuscripts, validates the publication
manifest and claim register, and scans the publication tree for secrets. The implementation and
MLflow-removal hardening are versioned on `main`; live efficiency, quality-preservation, latency,
cost, determinism, and portfolio claims remain unmeasured rather than simulated.

## 1. Executive decision

The extension should test one narrow, defensible claim:

> Given a real read-only workflow family and paired measurements for the unchanged agent,
> Guarded Region Compilation (GRC), and a reviewed hand-written macro, an exact-risk portfolio
> can select an admissible action or abstain without hiding quality failures, incompatibility,
> missing evidence, or full execution cost.

The confirmatory study will use three domains whose public records, exact factual fields, and
source APIs are reachable now:

1. **Cybersecurity:** reconcile a real open-source package advisory across OSV/GitHub Advisory
   Database, NVD, and CISA KEV snapshots.
2. **Financial reporting:** reconcile an issuer fact across SEC submissions, Company Facts, and
   filed XBRL records.
3. **Mortgage reporting:** interpret a real privacy-modified HMDA public Loan/Application Record
   against its year-specific public schema and code definitions.

These are evidence-gathering tasks, not regulated decisions. The system will not prioritize
patches, provide investment advice, decide credit, audit an adverse-action notice, infer
discrimination, or issue a legal or clinical conclusion.

The existing public GitHub-issue study remains a continuity and regression anchor. It is not
counted as one of the three new domains and is not pooled into their certificates.

### 1.1 Feasibility verdict

| Work package | Verdict now | Reason |
|---|---|---|
| Provider-free source acquisition and adapter development | **GO** | All three public sources responded during the 2026-08-04 review; no paid data or private partner is required. |
| Real OpenAI Agents SDK pilot | **CONDITIONAL GO** | `OPENAI_API_KEY` is configured by variable name, but a user-approved spending cap and a compliant SEC `User-Agent` contact string are still required. |
| Full confirmatory live study | **CONDITIONAL GO** | It proceeds only after independent-group counts, oracle audits, pilot reliability, and extrapolated cost pass their gates. |
| Mortgage adverse-action notice audit | **NO-GO with current data** | Public HMDA omits the actual notice, full underwriting inputs, model decision trail, and internal policy. A lender partner and compliance review would be required. |
| Pharmacovigilance causality or clinical decision study | **NO-GO for this extension** | Public AEMS/FAERS has abundant records but lacks public case narratives and adjudicated causal gold. |
| Production certification | **OUT OF SCOPE** | The study can establish benchmark evidence, not legal, security, financial, or operational certification. |

## 2. What was verified in the current environment

### 2.1 Repository and compute

| Resource | Observed state on 2026-08-04 | Planning consequence |
|---|---|---|
| Checkout | Release 0.6.0 implementation and MLflow removal are on `main`; revalidate exact HEAD before a paid run | Preserve the implemented control plane and historical evidence. |
| Package | `guarded-agentic-compaction` 0.6.0; Python requirement `>=3.11` | No package rename or architecture restart is needed. |
| Local interpreter | `.venv` Python 3.14.4 on macOS arm64 | Core adapters can run locally; Linux CI remains necessary for release evidence. |
| Provider libraries | `openai-agents` 0.19.2; `openai` 2.52.0 | Freeze these versions for the first pilot and record them in every manifest. |
| Credentials | `.env` contains `OPENAI_API_KEY` and `HF_TOKEN` variable names | Never print or serialize values. `HF_TOKEN` is not needed by the core study. |
| Missing configuration | No `SEC_USER_AGENT` or NVD API-key variable was observed | Require a real SEC contact string before SEC fetches. Use cached NVD requests at the unauthenticated rate; an NVD key is optional. |
| Docker | Client and daemon 29.6.1 | Available for Linux preflights, but not required by the three core datasets. |
| Free storage | Approximately 572 GiB | Sufficient for pinned source subsets and the SEC bulk files if needed. Apply a 40 GiB study-cache cap initially. |
| Optional packages | `pandas` 2.3.3 is installed; `duckdb` and `datasets` are absent | The core design must not depend on DuckDB, Hugging Face Datasets, RCAEval, Spider, or SciFact. |

### 2.2 Live public-data reachability

These checks establish access and scale, not benchmark validity:

| Domain | Observed preflight | Authentication and access policy | Sufficiency conclusion |
|---|---|---|---|
| Cybersecurity | OSV returned real package/version matches; current PyPI and npm OSV archives reported 32,948,938 and 213,447,334 bytes; a validated PyPI archive scan found 13,203 distinct affected package names; NVD returned the requested CVE; GitHub lists more than 30,000 reviewed advisories | OSV downloads need no key. GitHub Advisory Database is CC-BY-4.0. NVD works without a key but should be cached and throttled; its guidance recommends six seconds between requests | Far more than the required 420 candidate package groups are available. Registry/version verification and complete-case filtering must still run before sampling. |
| SEC | The public ticker file returned 10,412 entities; a Company Facts request returned structured facts; `companyfacts.zip` and `submissions.zip` reported 1,393,634,633 and 1,555,272,253 bytes | EDGAR data APIs require no key. SEC limits automated access to 10 requests/second and requires a declared organizational/user contact in `User-Agent` | More than 420 issuer groups are available. Standard-taxonomy fact coverage and filing-document resolution must pass preflight. |
| HMDA | A current 2025 nationwide filer query returned 4,660 institutions; a Rhode Island query returned 454 institutions and 8,138 denied applications; raw CSV streaming returned current public LAR rows. The earlier CFPB modified-LAR release described approximately 4,768 filers, so the manifest must pin the exact queried vintage | Public Data Browser endpoints need no key. Records are privacy-modified and may not be joined for re-identification | More than 420 filer groups are available. The study must remain a public-record interpretation task, not a reconstruction of underwriting decisions. |

### 2.3 Implemented library capabilities to reuse

- Framework-neutral typed `Episode` and effect-catalog contracts.
- OpenAI Agents SDK trace capture and `CompactingModel` integration.
- GRC for grounded, qualified read regions.
- TGWS, available only when the application supplies a measured evaluator and adequate grouped
  support.
- Grouped splits, replay/perturbation evidence, exact Clopper-Pearson admission, compatibility
  manifests, registry lifecycle, and baseline fallback.
- A portfolio selector over already measured actions.
- Existing live-study code for exact-source evaluation, usage accounting, provider traces,
  paired comparisons, and prospective freeze/test separation.

### 2.4 Constraints the extension must preserve

- Only `PURE`, `READ_LOCAL`, or qualified `READ_EXTERNAL` tools may enter a compiled region.
- Every compiled external read must have an explicit snapshot/freshness identity and declared
  `speculatable` and `replayable` capabilities.
- In the confirmatory study, measured agent tools read immutable local snapshots and are declared
  `READ_LOCAL`; network fetchers run before the study and never appear inside a candidate region.
  The source digest is part of every compatibility key. Live `READ_EXTERNAL` execution is a
  later transfer, not needed for the primary result.
- Writes, approvals, handoffs, guardrails, unknown effects, streaming, server-managed
  continuation, and hosted/MCP execution remain baseline barriers.
- Straight-line local Agents SDK function tools are the supported first implementation surface.
- GRC does not currently compile arbitrary loops. Each core case therefore uses a bounded number
  of source lookups; bulk iteration remains inside deterministic data-preparation code, outside
  the agent trace.
- The portfolio selects measured actions; it does not synthesize a macro, evolve a prompt, or
  create a cache policy.
- A macro is authored from train/development evidence, independently reviewed, and marked
  `HUMAN_REVIEW` before selection.
- Missing objective measurements reject an action. They are never imputed as zero cost or zero
  saving.

## 3. What changed from the earlier plan

The earlier version was scientifically interesting but not a single feasible execution path. It
made three core domains, two transfer suites, cache accounting, TGWS, GEPA, and new statistics
interdependent. It also selected SciFact despite the stronger practical need for regulated-domain
evidence and introduced `datasets`/`duckdb` dependencies that are not installed.

This revision makes the following changes:

- Replaces SciFact with **SEC filing reconciliation**.
- Replaces the generic HMDA adverse-action idea with a strictly public **HMDA record
  interpretation** contract.
- Uses **OSV/GitHub Advisory Database first** for package/version truth; NVD and KEV are
  enrichment sources rather than the sole vulnerability oracle.
- Reduces the required action set to baseline, GRC, and a reviewed macro.
- Removes cache, GEPA, TGWS, RCAEval, Spider, SWE-bench, and scientific QA from the critical path.
- Keeps GEPA and cache-aware prompt layout as optional later experiments after the three-domain
  certificate is complete.
- Eliminates any requirement for a lender, clinician, proprietary dataset, Hugging Face download,
  Kubernetes cluster, code-writing benchmark, or exploit environment.
- Adds explicit current blockers: compliant SEC contact configuration, provider budget approval,
  and preflight group/oracle validation.

## 4. Research questions and falsifiable hypotheses

### RQ1 — Does the best safe action vary across real workflow families?

**H1:** No one non-baseline action dominates baseline, GRC, and reviewed macro across all three
domains after quality, requests, tokens, latency, tool calls, provider cost, and construction
effort are reported.

Action heterogeneity is evidence, not a success condition. If one reviewed macro wins every
domain, the result supports interface consolidation rather than adaptive optimization.

### RQ2 — Does a calibrated family policy beat a fixed global action?

**H2:** A policy selected only from portfolio-calibration groups has greater sealed-test utility
than the best global fixed action chosen on those same calibration groups, while every selected
action passes the domain's exact quality contract.

Unavailable or inadmissible actions fall back to baseline in the fixed-policy comparison. A
test-oracle policy is reported only as an unattainable upper bound.

### RQ3 — Does GRC preserve exact evidence under source heterogeneity?

**H3:** Where GRC is admitted, it preserves every required field and source identity while
reducing model requests on sealed groups. Unknown aliases, units, forms, schema years, or source
states must cause baseline fallback rather than extrapolation.

### RQ4 — Do savings survive full accounting?

**H4:** Any selected non-baseline action has positive paired utility after provider inference,
tool time, source access, macro construction/review, compiler discovery, calibration, and
monitoring cost are amortized over a predeclared traffic horizon.

### RQ5 — What does the optimizer correctly refuse?

**H5:** Drifted manifests, unknown source versions, unsupported effects, incomplete metrics,
unseen categorical route values, or absent macro approval return baseline without changing the
task's source-visible state.

## 5. Common benchmark rules

Every headline case must satisfy all of the following:

1. It is derived from a real public record, not a fictional fixture or simulated policy.
2. The provider interaction is a live OpenAI Agents SDK execution.
3. Agent tools perform declared `READ_LOCAL` calls over a frozen snapshot produced from an
   authoritative public source; network acquisition is outside the measured workflow.
4. Source fetch and normalization are deterministic, checksum-verified, and provider-free.
5. The primary oracle is exact and programmatic; no LLM judge determines headline correctness.
6. Gold fields are not exposed through prompts, tools, traces, or candidate construction.
7. Every answer includes source identifiers sufficient to recompute the oracle.
8. Missing, withdrawn, amended, `NA`, conflicting, or not-applicable states are retained as
   cohorts rather than silently discarded.
9. The workflow performs no external write, recommendation, approval, or regulated decision.
10. A hand-written deterministic solution is included as a first-class comparator.

Source APIs are used to create immutable snapshots. They are not called repeatedly during live
agent measurement, which avoids rate-limit noise and makes all arms observe identical records.

## 6. Domain 1 — Open-source vulnerability evidence reconciliation

### 6.1 Real scenario

A software-security analyst receives a published package advisory and must reconcile its factual
status across authoritative sources before deciding what investigation happens next.

This benchmark does **not** decide exploitability in an organization's deployment and does not
prioritize or apply a patch.

### 6.2 Case contract

**Input**

- ecosystem;
- package name;
- real published package version when version applicability is evaluated;
- GHSA/OSV advisory identifier;
- source snapshot date.

**Bounded read-only tools**

- `get_osv_advisory(advisory_id)`;
- `query_osv_package_version(ecosystem, package, version)`;
- `get_github_advisory(ghsa_id)`;
- `get_nvd_record(cve_id)` when a CVE alias exists;
- `get_kev_record(cve_id)` when a CVE alias exists;
- `read_advisory_reference(advisory_id, reference_id)` for a preselected hard cohort only.

**Required output**

- canonical advisory and alias identifiers;
- ecosystem, package, and queried version;
- affected/unaffected/not-assessable status under the frozen OSV range;
- affected and fixed ranges exactly as represented;
- published, modified, and withdrawn state;
- severity source, version, vector, and score when available;
- CWE identifiers when available;
- KEV membership and date when available;
- conflicts or missing fields, without resolving them by invention;
- one source identifier per reported field family.

**Primary oracle**

Exact normalized equality against pinned OSV/GitHub Advisory JSON, with NVD and KEV treated as
separately attributed enrichment. A disagreement between sources is a correct `CONFLICT` state,
not an excuse to choose whichever value is convenient.

### 6.3 Cohorts and grouping

- Group by normalized ecosystem and package, so advisories for the same package cannot cross
  train, calibration, and test.
- Include reviewed advisories with and without CVE aliases, fixed and unfixed ranges, withdrawn
  records, missing severity, KEV and non-KEV records, pre-release versions, and explicit source
  disagreements.
- Start with PyPI and npm because their OSV snapshots were directly reachable and are large
  enough. Add Maven or Go only if one of the first ecosystems fails the unique-package gate.
- Select real versions from advisory version data and verify their publication in the relevant
  public package registry before freeze.

### 6.4 Why this is agentic rather than only a database join

The evidence path varies with aliases, withdrawal, source disagreement, KEV membership, and
missing metadata. Nevertheless, a macro may still dominate. That is an intended comparator
result. If every case follows the same deterministic join, this family should be classified as a
macro workload rather than used to claim GRC value.

### 6.5 Feasibility gate

- At least 420 unique packages after normalization and registry verification.
- At least 10% of the preflight pool must require a materially different source path; otherwise
  the benchmark remains useful as a macro negative control but cannot support a branching claim.
- Every selected source record must be redistributable or represented by a fetch manifest and
  digest.
- Unauthenticated NVD acquisition must follow the documented throttle and cache every response.

## 7. Domain 2 — SEC filing fact reconciliation

### 7.1 Real scenario

A financial-reporting analyst must identify the as-filed value of a disclosed fact for one issuer
and period, reconcile it across SEC Company Facts and the underlying filing, and identify whether
an amendment or later filing changes which value is applicable as of the case date.

The output is factual filing evidence. It is not investment advice, fraud detection, or a legal
assessment of the issuer's compliance.

### 7.2 Case contract

**Input**

- issuer CIK;
- fiscal period/end date;
- standard US-GAAP or DEI concept;
- as-of filing date;
- source snapshot identifier.

**Bounded read-only tools**

- `get_sec_submissions(cik)`;
- `get_sec_companyfacts(cik)`;
- `list_applicable_filings(cik, form, as_of_date)`;
- `read_filing_xbrl_fact(accession, concept, period)`;
- `read_filing_metadata(accession)`.

**Required output**

- issuer, concept, value, unit, start/end or instant period;
- form, fiscal year/period, accession, filed date, and report date;
- amendment status and the applicable accession as of the requested date;
- whether Company Facts and the filed fact agree;
- explicit `MULTIPLE_UNITS`, `MULTIPLE_CONTEXTS`, `MISSING`, or `NOT_ASSESSABLE` states;
- source URLs/identifiers for the Company Facts item and filing.

**Primary oracle**

Exact equality against the pinned SEC JSON and filed XBRL fact, including unit, period, form,
accession, and filed date. The evaluator must not collapse values across incompatible units or
contexts.

### 7.3 Cohorts and grouping

- Group by CIK; an issuer can appear in only one data role.
- Begin with standard taxonomy facts from 10-K, 10-Q, 10-K/A, and 10-Q/A filings.
- Stratify normal facts, amendments, multiple filings for one period, multiple units, non-calendar
  fiscal periods, missing Company Facts aggregation, and filing/aggregation disagreement.
- Custom-taxonomy concepts and narrative interpretation are deferred until the exact structured
  benchmark passes.

### 7.4 Access discipline

- Require `SEC_USER_AGENT` containing a real project identity and contact address before any
  automated fetch.
- Enforce at most 5 requests/second in our fetcher, below the SEC's published 10-request/second
  maximum.
- Prefer bulk archives or per-issuer cached JSON. Never repeatedly hit EDGAR during live agent
  arms.
- Store accession identifiers and digests, not modified copies presented as official filings.

### 7.5 Feasibility gate

- At least 420 issuers with a complete standard-concept case and resolvable underlying filing.
- At least 10% hard cases involving amendment, multiple context/unit, or missingness; otherwise
  retain the domain as a deterministic macro control.
- Independent oracle recomputation must agree on every field for a 50-case stratified audit.
- The fetch phase stops immediately if SEC access-policy responses or throttling errors occur.

## 8. Domain 3 — Public HMDA record interpretation

### 8.1 Real scenario

A mortgage-data or compliance analyst receives one public, privacy-modified HMDA LAR row and
needs a traceable interpretation of the codes that were publicly reported under the correct
year-specific schema.

The benchmark does **not** determine whether the lender's underwriting decision was fair, whether
an adverse-action notice was legally sufficient, or whether an applicant should receive credit.

### 8.2 Case contract

**Input**

- activity year;
- filer LEI;
- deterministic digest of one public LAR row;
- requested non-sensitive field families;
- source snapshot identifier.

**Bounded read-only tools**

- `get_public_lar_record(year, lei, row_digest)`;
- `get_hmda_public_schema(year)`;
- `get_hmda_field_definition(year, field)`;
- `get_hmda_filer(year, lei)`;
- `get_hmda_code_label(year, field, value)`.

**Required output**

- year, filer, action taken, loan type/purpose, lien status, occupancy/property type, and
  preapproval status;
- reported denial-reason codes and labels only when the public row contains them;
- `NA`, exempt, unavailable, or not-applicable states exactly as defined for the year;
- a privacy-modification notice;
- source identifiers for the row, schema, definitions, and filer metadata.

Protected demographic attributes are excluded from routing, action selection, and the primary
answer. They may be used only in a separately approved post-hoc error audit that reports aggregate
strata and never attempts re-identification.

**Primary oracle**

Exact equality to the frozen public row plus year-specific public schema and definitions. The
oracle checks faithful interpretation, not the truth of unobserved underwriting facts.

### 8.3 Cohorts and grouping

- Group by LEI so the same institution cannot cross data roles.
- Include originated, denied, withdrawn, incomplete, purchased-loan, and preapproval actions;
  denial reasons present and absent; `NA`/exempt fields; and at least two activity years.
- Use only public modified LAR data. Do not join property, identity, consumer, credit-bureau, or
  commercial enrichment data.
- Generate case IDs from source year, LEI, source snapshot, and row digest; never publish a
  reconstructed private application identifier.

### 8.4 Why the scope is deliberately narrow

HMDA has enough rows and filer groups, but it does not expose the actual adverse-action notice,
full credit record, internal model factors, or policy decision trail. Therefore the public study
can evaluate source fidelity and workflow optimization, not notice compliance or causal fairness.

A later private-partner study would require deidentified decision factors, actual notice text,
model and policy versions, expert labels, counsel-approved handling, and a separate protocol. It
is not a hidden dependency of this plan.

### 8.5 Feasibility gate

- At least 420 LEIs with a complete public row and year-specific documentation.
- At least 10% of cases must exercise different action/availability branches; otherwise classify
  the family as a macro negative control.
- Independent recomputation must agree on every field for a 50-case stratified audit.
- No case or output may attempt person, property, or application re-identification.

## 9. Data design and sample sizes

### 9.1 Preflight pool

Build a deterministic pool of at least 420 independent groups per domain. The 75-group reserve
absorbs invalid-source or oracle failures **before** roles are frozen. Once roles are frozen, a
failed, timed-out, or low-quality test case is never replaced.

| Domain | Independent group | Minimum preflight groups | Raw availability evidence |
|---|---|---:|---|
| Vulnerability | normalized ecosystem + package | 420 | 13,203 distinct affected package names observed in the validated PyPI OSV archive alone; complete cases will be fewer |
| SEC | issuer CIK | 420 | 10,412 ticker-file entities observed; EDGAR also contains non-ticker filers |
| HMDA | filer LEI | 420 | 4,660 institutions observed in the current 2025 nationwide API response; source-vintage drift is pinned explicitly |

Raw counts do not prove valid independent cases. The provider-free preflight must compute and
publish included, rejected, duplicated, source-missing, license-gated, and reserve counts.

### 9.2 Frozen role allocation

Each domain uses 345 disjoint groups:

| Role | Groups | Permitted use |
|---|---:|---|
| Discovery/train | 40 | Observe baseline traces, mine recurrence, and draft the macro. |
| Development | 30 | Finalize tools, prompts, contracts, macro tests, and candidate settings. |
| GRC artifact calibration | 100 | Admit or retire the frozen compiler artifact. |
| Portfolio calibration | 75 | Measure frozen A0/A1/A2 and select the family action. |
| Sealed prospective test | 100 | Compare selected family policy, each fixed action, and baseline once. |

Artifact and portfolio calibration are separate. Data used to create or internally admit GRC
cannot also certify it as the best portfolio action.

### 9.3 Leakage controls

- Vulnerability: package identity, advisory aliases, and reference lineage.
- SEC: CIK, accession lineage, and filing amendments.
- HMDA: LEI and source-row digest.
- All domains: normalized input hash, source record ID, snapshot digest, prompt/tool/evaluator
  digest, and group role.

A single command must fail if an identity or lineage edge crosses frozen roles.

## 10. Required actions and fair comparison

### 10.1 Confirmatory arms

| ID | Action | Current state | Admission rule |
|---|---|---|---|
| A0 | Unchanged Agents SDK baseline | Implemented | Always available; the three condition orders are counterbalanced rather than always running baseline first. |
| A1 | GRC | Implemented | Only a grounded, bounded, read-only region that passes existing artifact gates and the outer portfolio certificate. |
| A2 | Reviewed deterministic macro | Domain-specific implementation required | Authored from train/development only, exact contract tests pass, construction/review effort recorded, and explicit review approval attached. |

The macro must use the same frozen source snapshot and return the same schema. It may combine
deterministic source reads into one cohesive application operation. This is the comparator that
tests whether compilation is preferable to ordinary interface engineering.

The best global fixed comparator may consider only an action that is available in every domain.
Replacing an unavailable domain/action cell with baseline would be a conditional fallback policy,
not one fixed action, and is therefore prohibited in that comparison.

### 10.2 Actions intentionally outside the confirmatory path

- **TGWS:** run only as an exploratory arm if train/development data reveal a genuine entry-state
  route and every leaf has adequate independent support.
- **Prompt caching:** current accounting lacks cache-write tokens and the requested SDK request
  shape has not been verified. Add only after separate implementation and smoke evidence.
- **GEPA:** scientifically related, but it adds an optimizer, reflection model, rollout budget,
  dependencies, and a second calibration problem. Run only after the three-domain study freezes.
- **RCAEval, Spider, SciFact, SWE-bench, AIOpsLab, ScienceAgentBench:** useful future transfers,
  not required for this extension and not evidence for the three-domain claim.

Exploratory arms never change the multiplicity or interpretation of a frozen confirmatory study.

## 11. Quality, safety, and statistical contracts

### 11.1 Domain contracts

| Domain | Primary binary success | Secondary quality | Explicitly excluded claim |
|---|---|---|---|
| Vulnerability | Every required normalized field, source attribution, and missing/conflict state is exact | field accuracy, alias recall, source-path accuracy | deployment exploitability or remediation priority |
| SEC | Fact value, unit, period, form, accession, filed date, amendment state, and source identity are exact | per-field accuracy, hard-cohort accuracy | investment, fraud, or legal conclusion |
| HMDA | Public row values and year-specific code/availability interpretations are exact | per-field accuracy, action-family accuracy | underwriting fairness, adverse-action compliance, or credit decision |

Source-path success also requires the predeclared domain-specific evidence-tool set. Every
required call must carry the frozen snapshot and case record identity; an exact-looking answer
plus an irrelevant or wrong-argument allowed call fails the binary contract.

### 11.2 Portfolio risk configuration

The confirmatory study has two non-baseline actions. Use:

```python
SelectionConfig(
    quality_risk_limit=0.10,
    regret_risk_limit=0.10,
    confidence=bonferroni_family_confidence(0.99, n_families=3),
    minimum_groups=75,
    minimum_utility=0.0,
    expected_compatibility_key=family_key,
)
```

The per-family confidence is approximately 0.99667, so the union-bound error across three
families is at most 1%. Within each family, the selector splits the remaining error budget across
four action/bound combinations. For zero events in 75 groups, the recomputed one-sided upper
bound is approximately 0.0902; one event raises it to approximately 0.1190 and rejects the action
at the 10% limit.

Do not add an action after portfolio calibration begins. Recompute the sample size if the number
of registered actions changes.

### 11.3 Sealed-test inference

- Binary quality: exact paired candidate-minus-baseline non-inferiority with a 5-percentage-point
  margin and 99% one-sided interval per domain.
- Continuous paired endpoints: group bootstrap with at least 10,000 resamples.
- Primary efficiency endpoint: provider-request ratio.
- Required secondary endpoints: input/cached/output/total tokens, estimated cost under a pinned
  pricing manifest, wall latency, tool calls, fallbacks, verifier failures, and exact trace/output
  agreement on repeats.
- Repeat all arms three times on 20 preselected test groups per domain. Repeats assess
  determinism and are not independent support.
- Correct secondary hypothesis families with Holm's procedure.
- Require every selected family action to pass quality. Cross-domain averaging cannot hide a
  domain failure.

With zero failures among 100 groups, the existing exact upper-bound implementation gives about
0.0450 at 99% confidence. A failure may make the 5-point claim unattainable; this is an intended
strict gate, not a reason to top up or tune on test.

### 11.4 Utility and amortization

Use the existing portfolio objective fields only after one canonical, tested mapper aligns live
study results and `EpisodeMetrics`:

- `estimated_cost_usd`;
- `wall_latency_ms`;
- `total_tokens`;
- `tool_calls`.

Report provider requests separately as the primary structural endpoint. Cost is null when the
model price or usage category cannot be resolved; a positively weighted null metric rejects the
action.

Construction and amortization reporting must include:

- baseline discovery calls;
- GRC compilation/calibration calls and engineering time;
- macro authoring, review, tests, and maintenance time;
- source acquisition and normalization time;
- live evaluation cost;
- observed per-run savings and break-even volume.

## 12. Resource and spending model

### 12.1 Provider-free work

The following requires no OpenAI calls:

- source fetch, checksums, and license/attribution manifests;
- normalization and group-count reports;
- deterministic oracle construction;
- adapter and macro unit tests;
- leakage, effect-catalog, and snapshot-replay tests;
- full existing repository test suite.

### 12.2 Pilot budget gate

The pilot schedules 12 groups × 3 domains × 3 actions = **108 action-group executions**, plus
bounded retries. Before it starts, the runner must require:

- a user-supplied `--max-provider-usd` value;
- a pinned model and pricing manifest;
- a fixed maximum number of model requests per action-group;
- a fixed retry policy;
- a dry-run schedule showing the exact maximum call count.

The pilot estimates the full-run cost as:

```text
sum over domain/action(
    pilot mean cost per completed group
    × scheduled calibration/test/repeat groups
) × 1.25 contingency
```

The full study does not start until that estimate fits a separately approved cap. Possession of
an API key is not spending authorization.

### 12.3 Storage and network

- Initial cache cap: 40 GiB; stop before exceeding it.
- Prefer per-ecosystem OSV archives, per-issuer SEC JSON, and filtered/year-specific HMDA streams.
- The observed SEC bulk ZIPs total under 3 GiB compressed, but bulk download is optional.
- Download once, checksum, and execute all agent arms against local snapshots.
- Retain raw public-source manifests and normalized cases; do not commit large source archives.

### 12.4 Human resources actually required

The primary exact-field oracles do not require a licensed mortgage professional, attorney,
clinician, or financial adviser. They do require:

- one engineering author;
- one independent code/oracle reviewer before the pilot;
- one named reviewer for each domain macro.

If no independent reviewer is available, the implementation can proceed, but the study must be
labeled single-reviewer and cannot claim independent expert validation. Any future adverse-action
or clinical extension requires qualified domain review and a new protocol.

## 13. Library and artifact design

Keep generic experiment contracts in the library and domain-specific data outside its import
surface:

```text
src/guarded_agentic_compaction/
  benchmarking/             # protocol, schedules, approvals, action identity, budget, preflight
  evaluation/
    domains.py              # DomainAdapter, BenchmarkCase, OracleResult protocols
    evidence.py             # canonical live/episode metric mapper
    paired_exact.py         # paired binary non-inferiority
    ledger.py               # append-only resumable execution ledger
  portfolio/
    policy.py               # per-family decisions and unknown-family baseline
    risk.py                 # registered family/action error allocation

benchmarks/
  README.md
  manifests/
    multidomain-study.yaml
    sources/                # URL, retrieval time, revision, digest, terms, counts
  adapters/
    vulnerability_evidence.py
    sec_filing_facts.py
    hmda_public_lar.py
  contracts/
    vulnerability.schema.json
    sec_fact.schema.json
    hmda_record.schema.json
    pricing.schema.json
    macro-approval.schema.json
    construction-effort.schema.json
    effects/
  fetch/
    common.py
    vulnerability.py
    sec.py
    hmda.py
  build/
    vulnerability_pool.py
    nvd_subset.py
    sec_pool.py
    hmda_pool.py
  acquire.py
  runtime.py
  oracles.py

paper/scripts/
  multidomain_study.py
  compile_multidomain.py
  prepare_macro_review.py
  calibrate_grc_artifacts.py
  freeze_multidomain_actions.py
  calibrate_multidomain.py
  analyze_multidomain.py
  validate_multidomain.py

paper/results/multidomain/
  protocol/
  source_manifests/
  preflight/
  pilot/
  artifact-calibration/
  calibrated-registries/
  calibration/
  test/
  analysis/
```

### 13.1 Generic adapter contract

```python
class DomainAdapter(Protocol):
    name: str

    def cases(self, role: BenchmarkRole) -> Sequence[BenchmarkCase]: ...
    def build_agent(self, action: str, frozen: FrozenStudy) -> Any: ...
    def oracle(self, case: BenchmarkCase, output: object) -> OracleResult: ...
    def effect_catalog(self) -> EffectCatalog: ...
    def compatibility_key(self, frozen: FrozenStudy) -> str: ...
```

The adapter never receives unrestricted access to gold labels. Candidate code receives only the
case input and read-only source facade.

### 13.2 Canonical metric mapper

Add one immutable record with:

```text
model_requests
input_tokens
cached_input_tokens
output_tokens
total_tokens
estimated_cost_usd | null
wall_latency_ms
critical_path_ms
tool_calls
quality_contract_pass
provider_trace_id
run_status
```

The mapper from retained live results and `EpisodeMetrics` must be unit-tested. Do not add
`cache_write_tokens` until the provider/SDK exposes and the implementation captures them.

### 13.3 Dependencies

Do not add new core dependencies for these benchmarks. Use standard-library JSON/CSV/SQLite/ZIP
processing where practical and the already available pandas extra for analysis. If a large-file
parser becomes necessary, add it only to a pinned `benchmarks` optional extra after a measured
preflight.

## 14. Execution phases

### Phase 0 — source and protocol lock

**Work**

- Add `SEC_USER_AGENT` documentation and fail closed when it is missing.
- Fetch small real samples from every source and record status, headers, retrieval time, digest,
  license/terms, and count.
- Build the 420-group preflight pool per domain and publish every inclusion/rejection reason.
- Freeze group identities, role allocation, random seed, effect catalogs, output schemas,
  primary metrics, margins, actions, model, SDK versions, and pricing manifest.
- Register the study as `proposed/unrun`.

**Acceptance**

- Three domains each retain at least 345 usable disjoint groups plus a documented reserve.
- Every source can be recreated from an empty cache without a private credential.
- SEC fetches use a compliant declared contact and stay below five requests/second.
- No provider call occurs and no test gold is exposed.

### Phase 1 — generic evidence substrate

**Work**

- Implement `DomainAdapter`, canonical metric mapping, family policy serialization, exact paired
  binary analysis, and append-only resumable ledger.
- Add a family policy that returns baseline for an unknown family or compatibility key.
- Reuse the current `select_portfolio_action`; do not rewrite its risk logic without a failing
  test and statistical review.

**Acceptance**

- Unknown family/key, incomplete pairs, null weighted metrics, mixed compatibility, absent macro
  approval, and interrupted runs fail closed.
- Tests recompute the 75-group zero/one-event bounds reported in this plan.
- Default `pytest` remains provider-free.

### Phase 2 — domain adapters and oracle audit

Implement in this order:

1. vulnerability evidence;
2. SEC filing facts;
3. HMDA public LAR.

For every adapter, add exact-positive, wrong-field, wrong-source, fabricated citation, missing
source, conflict, schema drift, timeout, duplicate identity, and leakage tests using retained real
records.

**Acceptance**

- Independent recomputation matches all fields on 50 stratified cases per domain.
- Source tools expose no gold-only values and declare only qualified reads.
- Prompt text does not prescribe the exact tool order.
- Unsupported source or schema states return baseline/`NOT_ASSESSABLE` as predeclared.

### Phase 3 — action construction

**Work**

- Run baseline only on discovery/train groups.
- Compile GRC within the current straight-line local-function-tool boundary.
- Author and test one deterministic macro per domain using train/development only.
- Record engineering and review effort.
- Freeze every candidate before portfolio calibration.

**Acceptance**

- GRC either carries complete artifact evidence or is recorded as unavailable/retired.
- Each macro has explicit review approval and exact schema/effect tests.
- All actions use identical snapshots, case inputs, output schema, and evaluator.

### Phase 4 — real-provider pilot

Run 12 fresh pilot groups per domain and applicable action. Pilot data validates infrastructure,
cost, provider usage, source facade, evaluator, and failure handling. It is never pooled into
confirmatory inference.

**Go criteria**

- zero secret or gold leakage;
- at least 95% complete scheduled records, with all failures retained;
- zero unresolved material oracle disagreements;
- fixed retry behavior and no silent case replacement;
- observed request/token/cost records reconcile to provider usage;
- extrapolated full cost fits an explicitly approved cap;
- no external source is called during measured action execution.

### Phase 5 — calibration, freeze, and sealed test

1. Execute shadow GRC candidates on the 100 artifact-calibration groups.
2. Calibrate artifacts with exact per-domain quality and artifact-wise Bonferroni bounds; a
   distinct reviewer promotes admitted artifacts with an expiry, while rejected/empty registries
   remain explicit unavailability evidence.
3. Freeze active artifacts, macros, prompts, tools, manifests, evaluators, compatibility keys,
   model, pricing, service tier, and SDK identities.
4. Run A0/A1/A2 on all 75 portfolio-calibration groups where applicable.
5. Select each family action and the best global fixed policy, then write a digested frozen policy
   before any test call.
6. Run all actions on the 100 sealed groups in a deterministic counterbalanced schedule.
7. Run the preselected repeat cohort.
8. Generate every table and figure from retained raw outputs through one analysis entry point.

**Acceptance**

- Frozen policy timestamp/digest predates every test call.
- Every scheduled pair is complete or has an immutable failure reason.
- No prompt, macro, threshold, action, source snapshot, or evaluator changes after freeze.
- Reanalysis is byte-identical except explicitly documented volatile metadata.

### Phase 6 — robustness and time-forward follow-up

- Test unknown advisory states, SEC filing-form/schema changes, and a later HMDA data vintage
  through real new snapshots when available.
- Measure compatibility invalidation, fallback, and artifact/action churn without refitting.
- Keep controlled schema perturbations separate from naturally observed drift.
- Recompute amortization using observed traffic and maintenance effort.

This phase is desirable but not required to claim completion of the initial three-domain
prospective study. It is required for any later robustness claim.

### Phase 7 — optional research extensions

Only after Phase 5 is frozen:

- GEPA residual prompt evolution on one domain with an equal rollout/spend budget;
- cache-aware prompt layout after cache-write accounting is implemented;
- TGWS when a genuine entry route has enough support;
- pharmacovigilance evidence assembly after clinical review resources are secured;
- adverse-action notice fidelity after a lender partner provides deidentified decision records;
- RCAEval/Spider/SciFact as separate transfer studies.

None is part of the current definition of done.

### Phase 8 — paper and release

- Update manuscript claims, tables, figures, evidence register, paper review, limitations, data
  statements, and README from generated results.
- Add source/benchmark cards, cost and compute accounting, and exact reproduction commands.
- Run full tests, package build, artifact validation, LaTeX build, link checks, clean-clone
  reproduction, and secret scan.
- Record the final commit only after the user explicitly requests publication or push.

## 15. Validation matrix

| Layer | Required validation |
|---|---|
| Unit | metric mapper, risk bounds, family fallback, macro approval, exact field normalization, missing/conflict states |
| Property/fuzz | malformed source JSON/CSV, duplicate IDs, unexpected units/periods/codes, trace ordering, incomplete usage |
| Source integration | fetch policy, checksum, attribution, count report, deterministic snapshot replay |
| Adapter integration | tool schema, effect declarations, gold isolation, exact oracle recomputation |
| Live smoke | one capped real provider execution per action/domain after all provider-free gates |
| Statistical | role disjointness, no adaptive top-up, exact paired inference, policy frozen before test |
| Security/privacy | secret redaction, no writes, no exploit or patch actions, no advice/credit decision, no HMDA re-identification |
| Reproducibility | empty-cache source fetch, pinned manifests, append-only ledger, single analysis entry point |
| Publication | claims register matches results, tables are generated, PDF has no unresolved references |

Existing minimum commands remain:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m build
.venv/bin/python scripts/verify_release.py
.venv/bin/python paper/scripts/validate_artifacts.py
```

The benchmark CLI surface is implemented and its `--help` output is regression-tested. These
commands are executable control paths, not evidence that billable phases have run:

```bash
guarded-agentic-compaction benchmark preflight --help
guarded-agentic-compaction benchmark freeze --help
guarded-agentic-compaction benchmark discovery --help
guarded-agentic-compaction benchmark development --help
guarded-agentic-compaction benchmark compile-grc --help
guarded-agentic-compaction benchmark prepare-macro-review --help
guarded-agentic-compaction benchmark pilot --help
guarded-agentic-compaction benchmark artifact-calibration --help
guarded-agentic-compaction benchmark calibrate-grc --help
guarded-agentic-compaction benchmark freeze-actions --help
guarded-agentic-compaction benchmark portfolio-calibration --help
guarded-agentic-compaction benchmark calibrate --help
guarded-agentic-compaction benchmark test --help
guarded-agentic-compaction benchmark analyze --help
```

## 16. Reproducibility, credentials, and data handling

- Load `.env` only at the live runner boundary.
- Record only whether required credentials/configuration were available, never their values.
- `HF_TOKEN` is unused in the core study.
- Treat `SEC_USER_AGENT` as required configuration; store only a redacted/hash form in public run
  manifests if it contains personal contact information.
- Redact request headers and provider exception bodies before serialization.
- Keep downloaded archives in a gitignored cache. Commit source URLs, revisions, digests,
  attribution, fetch code, selection IDs, and small normalized cases only where redistribution is
  permitted.
- Every result records source/split/prompt/tool/evaluator digests, model, SDK versions,
  Python/platform, seed, service tier, pricing revision, action version, provider trace ID, and
  run status.
- Provider-free preflight must record `provider_calls_executed: 0`.
- Frozen protocols bind the canonical full case pool, not only case IDs; every schedule rejects
  post-freeze input, grouping, lineage, metadata, or snapshot-identity drift.
- Source attestations recompute the normalized snapshot identity and verify the exact retained
  case, independent-gold, and snapshot file hashes before any protocol can freeze.
- Live runs record scheduled, attempted, completed, failed, retried, and billed calls.
- Failed or unavailable sources remain visible in the manifest and denominator.

## 17. Schedule and effort

These are one-engineer estimates, not elapsed-time promises:

| Priority | Work package | Engineering estimate | Gate |
|---|---|---:|---|
| P0 | source manifests, pools, and protocol lock | 4–6 working days | 420 groups/domain and compliant source access |
| P0 | generic evidence/policy/statistics substrate | 6–9 working days | provider-free tests green |
| P0 | vulnerability adapter and oracle | 5–7 working days | 50-case audit and branch mix pass |
| P0 | SEC adapter and oracle | 5–8 working days | issuer/fact/source audit passes |
| P0 | HMDA adapter and oracle | 5–7 working days | filer/schema/privacy audit passes |
| P0 | macro/GRC construction and capped pilot | 5–8 working days | quality, reliability, and spending go decision |
| P0 | full calibration/test and analysis | 7–12 working days plus provider runtime | frozen protocol and complete paired ledger |
| P1 | paper, artifacts, and clean-clone release | 7–10 working days | full claims and reproduction audit |

Expected engineering range: approximately **7–11 weeks** for one experienced contributor,
assuming no source-access incident and timely review. This is substantially more realistic than
running all earlier benchmarks and optimizer extensions in one study.

## 18. Stop conditions

- **Missing compliant SEC contact:** do not fetch SEC data programmatically.
- **No approved provider cap:** stop after provider-free adapter/oracle completion.
- **Fewer than 345 valid groups after conservative grouping:** do not weaken identities; replace
  or downgrade the domain before protocol freeze.
- **Less than 10% variable-path cases:** retain the domain only as a macro negative control and
  drop any branching/GRC-benefit claim.
- **Unresolved source or oracle disagreement:** exclude under the predeclared pre-freeze rule and
  report it; never choose a favorable label.
- **Any test quality failure that violates the frozen margin:** retain the result and drop the
  corresponding preservation/admission claim; never tune on test.
- **Macro dominates all domains:** present evidence that interface consolidation is the practical
  optimum and GRC should abstain.
- **GRC never admits:** present a negative result about the current compiler's support envelope;
  do not loosen the effect or provenance rules to force a win.
- **Portfolio does not beat the fixed action:** retain exact-risk/abstention findings and drop
  adaptive-superiority language.
- **Source access policy changes or throttling occurs:** stop fetches, preserve the cache and
  error evidence, and revise the source plan.
- **Any secret, protected-data, or re-identification risk appears:** terminate the affected run
  and treat it as an incident.

## 19. Definition of done

The extension is complete only when:

- all three provider-free source packs and 345-group role manifests are reproducible;
- the generic adapter, evidence mapper, exact paired analysis, ledger, and family policy are
  implemented and documented;
- baseline, GRC, and reviewed macro are measured wherever applicable;
- all headline executions use real public records, real local source tools, and live provider
  calls;
- separate GRC calibration, portfolio calibration, and 100-group sealed tests are retained;
- every abstention, unavailable action, provider/source error, and failed contract remains in the
  evidence ledger;
- quality, requests, tokens, latency, cost, tools, determinism, construction effort, and
  amortization are reproducible;
- the paper explicitly limits mortgage results to public-record interpretation;
- no result is presented as patch priority, investment advice, lending fairness, adverse-action
  compliance, clinical causality, or production certification;
- full tests, package build, paper build, artifact validator, link check, clean-clone
  reproduction, and secret scan pass;
- the final paper claims register matches generated evidence exactly.

## 20. Primary sources and current evidence boundaries

### Cybersecurity

- [OSV API](https://google.github.io/osv.dev/api/)
- [OSV data sources and dumps](https://google.github.io/osv.dev/data/)
- [GitHub Advisory Database documentation](https://docs.github.com/en/code-security/concepts/vulnerability-reporting-and-management/github-advisory-database)
- [GitHub Advisory Database repository](https://github.com/github/advisory-database)
- [NVD vulnerability API](https://nvd.nist.gov/developers/vulnerabilities)
- [NVD API access guidance](https://nvd.nist.gov/developers/start-here)
- [NVD API key, throttling, and caching guidance](https://nvd.nist.gov/general/news/API-Key-Announcement)
- [CISA Known Exploited Vulnerabilities catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog)

### SEC

- [EDGAR application programming interfaces](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [SEC Financial Statement Data Sets](https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets)
- [SEC automated-access and User-Agent guidance](https://www.sec.gov/about/webmaster-frequently-asked-questions)

### Mortgage/HMDA

- [CFPB HMDA overview](https://www.consumerfinance.gov/data-research/hmda/)
- [HMDA Data Browser](https://ffiec.cfpb.gov/data-browser/data/)
- [HMDA snapshot national loan-level dataset](https://ffiec.cfpb.gov/data-publication/snapshot-national-loan-level-dataset/)
- [2025 HMDA public-data release](https://www.consumerfinance.gov/about-us/newsroom/2025-hmda-data-on-mortgage-lending-now-available/)
- [Current Regulation B resource and version notice](https://www.consumerfinance.gov/rules-policy/regulations/1002/)

### Related optimization work

- [GEPA paper](https://arxiv.org/abs/2507.19457)
- [GEPA official implementation](https://github.com/gepa-ai/gepa)

GEPA is a later learned-prompt comparator, not a source of domain gold and not part of the
confirmatory implementation path.
