#!/usr/bin/env python3
"""Render benchmarks/explorer/index.html from the benchmark evidence artifacts.

The explorer is a browsable view of the same audit the paper reports, so it is generated
from paper/results/ rather than hand-written.  Screening, execution, measurement, and
gated-source rows carry different evidence, and the page has to keep them distinguishable:
a screened reference plan is not a compiler execution, and an inaccessible source gets no
imputed metric.  Totals are recomputed from the per-benchmark rows and the script fails
closed when they disagree with the recorded summary.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
OUTPUT = ROOT / "benchmarks" / "explorer" / "index.html"

MATRIX = "results/external_benchmarks/reference_analysis.json"
MULTIDOMAIN = "results/multidomain/preflight/validation.json"

# Upstream capitalisation, so a reader searching "tau2" or "SWE-bench" finds the row.
DISPLAY_NAMES = {
    "agentbench": "AgentBench",
    "api_bank": "API-Bank",
    "bfcl": "BFCL v4 — multi-turn base",
    "browsecomp": "BrowseComp",
    "gaia": "GAIA",
    "nestful": "NESTFUL",
    "swe_bench_verified": "SWE-bench Verified",
    "tau2": "τ²-bench",
    "toolbench": "ToolBench",
    "toolsandbox": "ToolSandbox",
}

DOMAIN_NAMES = {
    "vulnerability": "OSV / GitHub Advisory / NVD vulnerability records",
    "hmda": "HMDA public loan application register",
    "sec": "SEC filing facts",
}

STATUS_COPY = {
    "measured": "Compiler executed on this benchmark; a gate decision was produced.",
    "screened": "Reference plans were screened for compilable structure. No compiler ran.",
    "gated": "Upstream access denied. No task or compiler metric is imputed.",
    "preflight": "Real records validated and frozen, but the study has not been run.",
}


class VerificationError(SystemExit):
    """Raised when recomputed totals disagree with the recorded summary."""


def load(relative: str) -> dict:
    return json.loads((PAPER / relative).read_text(encoding="utf-8"))


def esc(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def humanize(value: str) -> str:
    return value.replace("_", " ")


def rows_from_matrix(matrix: dict) -> list[dict]:
    rows = []
    for key, entry in sorted(matrix["benchmarks"].items()):
        execution = entry.get("execution") or {}
        measured = entry.get("measured_compiler_results") or {}
        compiler_ran = bool(
            entry.get("compiler_executions")
            or execution.get("compiler_execution")
            or entry.get("status") == "measured"
        )
        gate = measured.get("default_gate_outcome") or execution.get("gate_outcome")
        rows.append(
            {
                "id": key,
                "name": DISPLAY_NAMES.get(key, key),
                "raw": entry.get("benchmark", key),
                "family": "External benchmark audit",
                "status": entry["status"],
                "substrate": entry.get("substrate"),
                "execution_status": entry.get("execution_status"),
                "evidence_stage": entry.get("evidence_stage"),
                "license": entry.get("license"),
                "scope": entry.get("benchmark_scope"),
                "reason": entry.get("reason"),
                "tasks": entry.get("tasks"),
                "actions": entry.get("total_actions"),
                "candidate_regions": entry.get("tasks_with_candidate_region"),
                "provider_calls": entry.get("provider_calls"),
                "compiler_ran": compiler_ran,
                "gate": gate,
                # Left as None when the artifact records no verdict. NESTFUL and GAIA do
                # not carry these fields, and rendering absence as "not licensed" would
                # invent a judgement the evidence file never made.
                "quality_licensed": entry.get("quality_claim_licensed"),
                "efficiency_licensed": entry.get("efficiency_claim_licensed"),
                "notes": entry.get("notes") or [],
                "source": entry.get("source_result"),
                "source_sha256": entry.get("source_result_sha256"),
                "revision": entry.get("source_revision"),
                "structure": {
                    label: entry[field]
                    for label, field in (
                        ("Read-like actions", "read_like_actions"),
                        ("Barrier actions", "barrier_actions"),
                        ("Unknown-effect actions", "unknown_actions"),
                        ("Recurrent candidate families", "recurrent_candidate_families"),
                        ("Longest read region", "maximum_read_region"),
                        ("Largest family support", "maximum_candidate_family_support"),
                        ("Tasks with reference actions", "tasks_with_reference_actions"),
                        ("Tasks with a barrier", "tasks_with_barrier"),
                        ("Tasks with unknown effects", "tasks_with_unknown"),
                    )
                    if entry.get(field) is not None
                },
                "effects": entry.get("effect_counts") or {},
                "blocks": entry.get("block_reason_counts") or {},
                "measured": measured,
                "execution": {
                    k: v
                    for k, v in execution.items()
                    if k not in {"schema", "result", "result_sha256", "compiler_execution"}
                },
                "credential": entry.get("credential_name"),
            }
        )
    return rows


def rows_from_multidomain(validation: dict) -> list[dict]:
    rows = []
    for domain in validation["domains"]:
        available = domain.get("available", False)
        rows.append(
            {
                "id": f"multidomain_{domain['domain']}",
                "name": DOMAIN_NAMES.get(domain["domain"], domain["domain"]),
                "raw": domain["domain"],
                "family": "Multidomain real-record source",
                "status": "preflight" if available else "gated",
                "substrate": "real_public_records" if available else None,
                "execution_status": "not_executed",
                "evidence_stage": "frozen_preflight" if available else "source_unavailable",
                "license": "public record redistribution terms per source manifest",
                "scope": (
                    f"{domain['cases']} validated cases across {domain['independent_groups']} "
                    "independent groups; protocol frozen before any provider call"
                    if available
                    else "pool could not be normalized from real records"
                ),
                "reason": (domain.get("errors") or [None])[0] if not available else None,
                "tasks": domain.get("cases"),
                "actions": None,
                "candidate_regions": None,
                # An unavailable pool reports nothing, matching how the gated external
                # source is handled; the study-level zero-provider-call fact is in notes.
                "provider_calls": 0 if available else None,
                "compiler_ran": False,
                "gate": None,
                "quality_licensed": False,
                "efficiency_licensed": False,
                "notes": [
                    "Study status is proposed_unrun with zero provider calls executed; "
                    "these rows are frozen inputs, not results."
                ],
                "source": "paper/results/multidomain/preflight/validation.json",
                "source_sha256": None,
                "revision": None,
                "structure": {
                    label: domain[field]
                    for label, field in (
                        ("Independent groups", "independent_groups"),
                        ("Exact-oracle passes", "exact_oracle_passes"),
                        ("Independent gold passes", "independent_gold_passes"),
                    )
                    if domain.get(field) is not None
                },
                "effects": {},
                "blocks": {},
                "measured": {},
                "execution": (
                    {"variable_path_fraction": round(domain["variable_path_fraction"], 4)}
                    if available
                    else {}
                ),
                "credential": None,
            }
        )
    return rows


DATASETS = ROOT / "paper" / "results" / "datasets"
PREFLIGHT = PAPER / "results" / "multidomain" / "preflight"
SOURCE_MANIFEST = ROOT / "benchmarks" / "manifests" / "external-benchmarks.yaml"
BIBLIOGRAPHY = PAPER / "bibliography" / "references.bib"

# What each benchmark evaluates, and why it appears here. The "tests" lines follow the
# manuscript's own characterisation of each corpus (Related work, tool-use evaluation);
# the "role" lines follow how the manuscript uses it. Both are editorial summaries of the
# paper, so they are kept beside the generated numbers rather than mixed into them.
PROFILES = {
    "nestful": {
        "cite": "basu2025nestful",
        "tests": "Executable nested API sequences, designed to test whether later calls "
                 "correctly reuse the outputs of earlier ones.",
        "role": "One of only two audited public corpora that retain the observed "
                "intermediate values a post-trace compiler needs, because it exposes "
                "nested producer references. The compiler genuinely ran here: families "
                "were mined, split by group, synthesized from train/dev windows, and "
                "replayed on held-out windows. Every family still fell below the "
                "92-group exact-gate requirement and retired.",
    },
    "api_bank": {
        "cite": "li2023apibank",
        "tests": "Runnable APIs and tool-use dialogues for tool-augmented models.",
        "role": "The second trace-complete corpus, retained because it keeps recorded "
                "call results. It produces an independent refusal: two families "
                "synthesize, but their held-out windows give zero passes, two "
                "abstentions, and zero wrong executions, so the gate retires every "
                "family. Recurrence and replayability do not supply admission evidence.",
    },
    "bfcl": {
        "cite": "patil2025bfcl",
        "tests": "Serial, parallel, abstaining, and stateful function calling.",
        "role": "Supplementary interoperability check. The official checker validates "
                "the pinned gold plans, which says nothing about model quality here.",
    },
    "toolsandbox": {
        "cite": "lu2025toolsandbox",
        "tests": "Stateful, conversational, interactive tool use.",
        "role": "Supplementary interoperability check on a simulated environment with a "
                "real provider. A simulator run is not a real-world demonstration.",
    },
    "tau2": {
        "cite": "barres2025tau2",
        "tests": "Conversational agents under dual control, where both the agent and the "
                 "user can act on the environment.",
        "role": "Supplementary interoperability check. Its reference plans are dominated "
                "by reversible writes and unknown effects, so conservative barriers "
                "leave very little compilable read structure.",
    },
    "toolbench": {
        "cite": "qin2023toolllm",
        "tests": "Tool retrieval and use scaled across thousands of real-world APIs.",
        "role": "Supplementary interoperability check limited to the examples bundled in "
                "the repository; the full reproduction data is an external download.",
    },
    "agentbench": {
        "cite": "liu2023agentbench",
        "tests": "LLMs acting as agents across interactive environments.",
        "role": "Supplementary interoperability check. Only the knowledge-graph portion "
                "carries reference actions; the DB and OS records are task-only.",
    },
    "gaia": {
        "cite": "mialon2023gaia",
        "tests": "General assistant capability on questions requiring multi-step "
                 "reasoning and tool use.",
        "role": "Recorded as withheld. The pinned revision sits behind a gated "
                "non-redistribution agreement and upstream refused authorization, so no "
                "task or compiler metric is imputed for it.",
    },
    "browsecomp": {
        "cite": "wei2025browsecomp",
        "tests": "Persistent browsing: locating hard-to-find facts on the live web.",
        "role": "Supplementary interoperability check on a bounded live-web subset. It "
                "exercises a hosted search tool rather than the compiler, and its "
                "prompts and answers stay encrypted upstream.",
    },
    "swe_bench_verified": {
        "cite": "jimenez2024swebench",
        "tests": "Resolving real GitHub issues in real repositories.",
        "role": "Recorded as screened with zero compilable structure, because the dataset "
                "ships task records without agent trajectories. Absent trajectories are "
                "not turned into compiler failures.",
    },
}

PAPER_CAVEAT = (
    "The eight supplementary benchmarks primarily test whether an agent can choose and "
    "execute actions or produce a final answer. That is a different question from the one "
    "asked here, which is whether an already-valid trace carries enough evidence to "
    "compile and admit a guarded program."
)

# Terms the tables use that are specific to this compiler. Defined once, and attached to
# the column headers and metric labels that use them.
GLOSSARY = {
    "Reference-plan screening": "Reading a benchmark's own gold or reference action "
        "sequences to see whether any compilable read structure exists. No compiler runs "
        "and no model is called, so screening is never a quality result.",
    "Candidate region": "A contiguous run of read-like actions inside one task that could, "
        "in principle, be compiled. Counted per task as a candidate window.",
    "Candidate family": "A recurring call chain shared across tasks. Support counts how "
        "many tasks share that exact chain; the exact gate needs far more independent "
        "groups than any of these reach.",
    "Barrier action": "An action the compiler refuses to cross, because it writes, or its "
        "effect cannot be established as read-only.",
    "Unknown-effect action": "An action whose effect class could not be determined from the "
        "source. Treated as a barrier, never as a read.",
    "Complete observed trace": "A recorded task where every intermediate call result is "
        "retained, which is what a post-trace compiler needs to reconstruct provenance.",
    "Independent groups": "Calibration units that the exact gate counts. The configured "
        "gate requires 92 zero-violation groups before it will admit anything.",
    "Gate outcome": "The compiler's decision for a family. RETIRE means the evidence was "
        "insufficient and nothing is deployed, which is the default.",
}

# Free-text previews are clipped so the page stays a browsable index rather than a mirror
# of the upstream corpus; the full record always stays reachable at the cited path.
PREVIEW_CHARS = 190
PAGE_SIZE = 100


def load_upstream() -> dict[str, dict]:
    """Where each corpus came from: repository, pinned revision, licence, retrieval mode.

    Read from the sealed source manifest so the explorer cites the same provenance the
    experiments were run against, rather than a hand-copied link that can rot.
    """

    import yaml

    manifest = yaml.safe_load(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    sources = {
        key: {
            "repository": spec.get("repository"),
            "revision": spec.get("revision"),
            "license": spec.get("license"),
            "kind": spec.get("kind"),
            "url": spec.get("url"),
            "auth_env": spec.get("auth_env"),
            "scope": spec.get("benchmark_scope"),
        }
        for key, spec in manifest["sources"].items()
    }
    # NESTFUL is pinned by its own dataset manifest rather than the source checkout list.
    nestful = json.loads(
        (DATASETS / "nestful" / "source_manifest.json").read_text(encoding="utf-8")
    )
    sources["nestful"] = {
        "repository": f"https://huggingface.co/datasets/{nestful['dataset']}",
        "revision": nestful["commit"],
        "license": nestful.get("license"),
        "kind": "dataset",
        "url": None,
        "auth_env": None,
        "scope": "data_v2/nestful_data.jsonl with the audited basic_functions module",
    }
    return sources


def bib_field(entry: str, name: str) -> str | None:
    """Pull one brace-delimited BibTeX field, counting braces so nesting survives."""

    match = re.search(name + r"\s*=\s*\{", entry)
    if not match:
        return None
    depth = 1
    out = []
    for char in entry[match.end():]:
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                break
        out.append(char)
    return "".join(out)


def clean_tex(value: str) -> str:
    """Strip the BibTeX braces and escapes that protect casing and accents."""

    text = value.replace("\\&", "&")
    text = re.sub(r"\$\\tau\^2\$", "τ²", text)
    text = re.sub(r"\\['\"^`~=.]\{?(\w)\}?", r"\1", text)
    text = text.replace("{", "").replace("}", "")
    return " ".join(text.split())


def load_citations(keys: set[str]) -> dict[str, dict]:
    """Resolve each benchmark's paper reference out of the manuscript bibliography."""

    text = BIBLIOGRAPHY.read_text(encoding="utf-8")
    found = {}
    for key in sorted(keys):
        start = text.find("{" + key + ",")
        if start < 0:
            raise VerificationError(f"bibliography has no entry for {key}")
        begin = text.rfind("@", 0, start)
        depth = 0
        end = len(text)
        for index in range(start, len(text)):
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        entry = text[begin:end]
        authors = clean_tex(bib_field(entry, "author") or "")
        first = authors.split(" and ")[0].split(",")[0].strip()
        many = " and " in authors
        found[key] = {
            "title": clean_tex(bib_field(entry, "title") or key),
            "authors": f"{first} et al." if many else first,
            "year": (bib_field(entry, "year") or "").strip(),
            "venue": clean_tex(
                bib_field(entry, "booktitle") or bib_field(entry, "journal") or "preprint"
            ),
        }
    return found


def read_jsonl(path: Path, limit: int | None = None) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
            if limit is not None and len(records) >= limit:
                break
    return records


def clip(value: object, limit: int = PREVIEW_CHARS) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def collection(
    title: str, note: str, source: str, columns: list[dict], records: list[dict]
) -> dict:
    return {
        "title": title,
        "note": note,
        "source": source,
        "columns": columns,
        "records": records,
        "count": len(records),
    }


def col(key: str, label: str, kind: str = "text") -> dict:
    return {"key": key, "label": label, "kind": kind}


def nestful_collections() -> list[dict]:
    """Dataset tasks, the programs the compiler synthesized, and per-family replay rows."""

    tasks = read_jsonl(DATASETS / "nestful" / "nestful_data.jsonl")
    task_records = []
    for entry in tasks:
        calls = entry.get("output") or []
        task_records.append(
            {
                "id": clip(entry.get("sample_id"), 13),
                "question": clip(entry.get("input")),
                "sequence": " → ".join(c.get("name", "?") for c in calls) or "—",
                "steps": len(calls),
                "tools": len(entry.get("tools") or []),
                "gold": clip(entry.get("gold_answer"), 40),
            }
        )

    programs = json.loads(
        (PAPER / "results/nestful/synthesized_programs.json").read_text(encoding="utf-8")
    )
    program_records = [
        {
            "family": entry["family_hash"],
            "support": entry["support"],
            "steps": len((entry.get("program") or {}).get("steps") or []),
            "removed": (entry.get("program") or {}).get("removed_requests"),
            "program": entry.get("pretty", ""),
        }
        for entry in programs
    ]

    with (PAPER / "results/nestful/family_results.csv").open(encoding="utf-8") as handle:
        family_rows = list(csv.DictReader(handle))

    return [
        collection(
            "Dataset tasks",
            f"{len(task_records):,} records from IBM/NESTFUL (Apache-2.0). Questions are "
            "clipped previews; the gold call sequence is shown in full.",
            "paper/results/datasets/nestful/nestful_data.jsonl",
            [
                col("id", "Sample", "id"),
                col("question", "Question"),
                col("sequence", "Gold call sequence", "mono"),
                col("steps", "Steps", "num"),
                col("tools", "Tools offered", "num"),
                col("gold", "Gold answer", "id"),
            ],
            task_records,
        ),
        collection(
            "Synthesized programs",
            "Programs the compiler actually emitted for recurrent families, with the "
            "requests each one removes.",
            "paper/results/nestful/synthesized_programs.json",
            [
                col("family", "Family", "id"),
                col("support", "Support", "num"),
                col("steps", "Steps", "num"),
                col("removed", "Requests removed", "num"),
                col("program", "Program", "pre"),
            ],
            program_records,
        ),
        collection(
            "Family replay results",
            "Per-family held-out replay outcomes behind the RETIRE decision.",
            "paper/results/nestful/family_results.csv",
            [
                col("family_hash", "Family", "id"),
                col("support", "Support", "num"),
                col("tools", "Tools", "id"),
                col("program_steps", "Steps", "num"),
                col("replay_passed", "Passed", "num"),
                col("replay_wrong", "Wrong", "num"),
                col("replay_abstained", "Abstained", "num"),
                col("replay_effect_mismatch", "Effect mismatch", "num"),
            ],
            family_rows,
        ),
    ]


def multidomain_collection(domain: str) -> list[dict]:
    path = PREFLIGHT / domain / "cases.jsonl"
    if not path.exists():
        return []
    cases = read_jsonl(path)
    if domain == "hmda":
        records = [
            {
                "case": clip(c["case_id"], 46),
                "group": c["group_id"],
                "year": (c["inputs"] or {}).get("activity_year"),
                "fields": ", ".join((c["inputs"] or {}).get("requested_fields") or []),
                "cohort": (c["metadata"] or {}).get("action_cohort"),
                "protected": (c["metadata"] or {}).get(
                    "protected_demographic_fields_exposed"
                ),
                "digest": clip((c["inputs"] or {}).get("row_digest"), 13),
            }
            for c in cases
        ]
        columns = [
            col("case", "Case", "id"),
            col("group", "Group (LEI)", "id"),
            col("year", "Year", "id"),
            col("fields", "Requested fields"),
            col("cohort", "Action cohort", "id"),
            col("protected", "Protected fields exposed", "bool"),
            col("digest", "Row digest", "id"),
        ]
        note = (
            f"{len(records):,} validated cases from the official privacy-modified public "
            "LAR. Every row records that no protected demographic field is exposed."
        )
    else:
        records = [
            {
                "case": clip(c["case_id"], 46),
                "advisory": (c["inputs"] or {}).get("advisory_id"),
                "ecosystem": (c["inputs"] or {}).get("ecosystem"),
                "package": (c["inputs"] or {}).get("package"),
                "version": (c["inputs"] or {}).get("version"),
                "aliases": ", ".join((c["metadata"] or {}).get("lineage_ids") or []),
                "verified": (c["metadata"] or {}).get("registry_verified"),
            }
            for c in cases
        ]
        columns = [
            col("case", "Case", "id"),
            col("advisory", "Advisory", "id"),
            col("ecosystem", "Ecosystem"),
            col("package", "Package", "id"),
            col("version", "Version", "id"),
            col("aliases", "Alias lineage", "mono"),
            col("verified", "Registry verified", "bool"),
        ]
        note = (
            f"{len(records):,} validated cases assembled from OSV, the GitHub Advisory "
            "Database, PyPI version checks, CISA KEV, and checksum-verified NVD feeds."
        )
    return [
        collection(
            "Validated cases",
            note,
            f"paper/results/multidomain/preflight/{domain}/cases.jsonl",
            columns,
            records,
        )
    ]


def family_collection(entry: dict) -> list[dict]:
    """The recurrent tool-call chains screening found, with how many tasks support each."""

    support = entry.get("candidate_family_support") or {}
    if not support:
        return []
    records = [
        {
            "chain": chain,
            "length": len([part for part in chain.split("->") if part.strip()]),
            "support": count,
        }
        for chain, count in sorted(support.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    return [
        collection(
            "Candidate families",
            "Recurrent read-like call chains mined from reference plans. Support counts "
            "how many tasks share the chain; the exact gate needs far more than these.",
            "paper/results/external_benchmarks/reference_analysis.json",
            [
                col("chain", "Call chain", "mono"),
                col("length", "Calls", "num"),
                col("support", "Support", "num"),
            ],
            records,
        )
    ]


def live_collections(key: str) -> list[dict]:
    """Per-task records from the bounded live-provider runs."""

    base = PAPER / "results/external_benchmarks"
    if key == "browsecomp":
        payload = json.loads((base / "browsecomp_live.json").read_text(encoding="utf-8"))
        records = [
            {
                "task": clip(t.get("task_hash"), 13),
                "status": t.get("status"),
                "correct": t.get("correct"),
                "searches": (t.get("agent_output_item_counts") or {}).get(
                    "web_search_call"
                ),
                "tokens": (t.get("agent_usage") or {}).get("total_tokens"),
                "latency": round(t.get("latency_seconds", 0), 1),
            }
            for t in payload.get("tasks") or []
        ]
        return [
            collection(
                "Live task records",
                "Bounded live-web subset. Tasks are identified by hash only: BrowseComp "
                "prompts and answers stay encrypted upstream and are not reproduced.",
                "paper/results/external_benchmarks/browsecomp_live.json",
                [
                    col("task", "Task", "id"),
                    col("status", "Status"),
                    col("correct", "Correct", "bool"),
                    col("searches", "Web searches", "num"),
                    col("tokens", "Total tokens", "num"),
                    col("latency", "Latency (s)", "num"),
                ],
                records,
            )
        ]
    if key == "tau2":
        payload = json.loads((base / "tau2_live.json").read_text(encoding="utf-8"))
        records = [
            {
                "task": clip(s.get("task_hash"), 13),
                "domain": s.get("domain"),
                "reward": s.get("reward"),
                "db_match": s.get("db_match"),
                "requests": s.get("provider_requests_with_usage"),
                "tokens": (s.get("prompt_tokens") or 0) + (s.get("completion_tokens") or 0),
                "termination": clip(s.get("termination_reason"), 28),
            }
            for s in payload.get("simulations") or []
        ]
        return [
            collection(
                "Live simulations",
                "Bounded official-simulator runs with a real provider. Zero reward is the "
                "recorded outcome, not a compiler result.",
                "paper/results/external_benchmarks/tau2_live.json",
                [
                    col("task", "Task", "id"),
                    col("domain", "Domain"),
                    col("reward", "Reward", "num"),
                    col("db_match", "DB match", "bool"),
                    col("requests", "Provider requests", "num"),
                    col("tokens", "Tokens", "num"),
                    col("termination", "Termination"),
                ],
                records,
            )
        ]
    return []


def attach_content(rows: list[dict], matrix: dict) -> dict[str, list[dict]]:
    """Build the browsable record collections, keyed by row id.

    Rows with nothing to browse say why rather than showing an empty table: an upstream
    gate and an upstream corpus that ships no trajectories are different facts.
    """

    content: dict[str, list[dict]] = {}
    for row in rows:
        key = row["id"]
        groups: list[dict] = []
        if key == "nestful":
            groups += nestful_collections()
        elif key.startswith("multidomain_"):
            groups += multidomain_collection(key.removeprefix("multidomain_"))
        else:
            entry = matrix["benchmarks"].get(key) or {}
            groups += family_collection(entry)
            groups += live_collections(key)
        if groups:
            content[key] = groups
            row["record_count"] = sum(g["count"] for g in groups)
        else:
            row["record_count"] = 0
            row["no_content_reason"] = (
                row.get("reason")
                or "no per-task records are redistributed with this path in the repository"
            )
    return content


def verify_content(content: dict[str, list[dict]], matrix: dict) -> None:
    """Bind the browsable records back to the numbers the audit already published."""

    families = matrix["benchmarks"]
    for key, groups in content.items():
        for group in groups:
            if group["count"] != len(group["records"]):
                raise VerificationError(f"{key}/{group['title']}: count disagrees with rows")
            if not group["records"]:
                raise VerificationError(f"{key}/{group['title']}: empty collection embedded")
        if key in families:
            support = families[key].get("candidate_family_support") or {}
            if support:
                mined = next(g for g in groups if g["title"] == "Candidate families")
                if mined["count"] != len(support):
                    raise VerificationError(f"{key}: candidate family count drifted")
                top = max(support.values())
                recorded = families[key].get("maximum_candidate_family_support")
                if recorded is not None and top != recorded:
                    raise VerificationError(
                        f"{key}: largest family support {top} != recorded {recorded}"
                    )

    nestful = content.get("nestful") or []
    tasks = next((g for g in nestful if g["title"] == "Dataset tasks"), None)
    if tasks is not None:
        complete = families["nestful"]["complete_observed_traces"]
        if tasks["count"] < complete:
            raise VerificationError(
                f"nestful: embedded {tasks['count']} tasks, fewer than the "
                f"{complete} complete observed traces the audit reports"
            )


def attach_profiles(rows: list[dict]) -> None:
    """Give every external row a description, provenance, and paper reference.

    Fails closed: a benchmark that reaches the page without a profile or without pinned
    upstream provenance would be presented as understood when it is not.
    """

    upstream = load_upstream()
    citations = load_citations({spec["cite"] for spec in PROFILES.values()})
    for row in rows:
        if row["family"] != "External benchmark audit":
            # The multidomain sources are assembled here rather than pinned upstream, so
            # their provenance is the snapshot digest already shown on the row.
            row["tests"] = None
            row["role"] = None
            row["upstream"] = None
            row["citation"] = None
            continue
        profile = PROFILES.get(row["id"])
        source = upstream.get(row["id"])
        if profile is None:
            raise VerificationError(f"{row['id']}: no profile; refusing to ship a bare row")
        if source is None or not source.get("repository"):
            raise VerificationError(f"{row['id']}: no pinned upstream source")
        row["tests"] = profile["tests"]
        row["role"] = profile["role"]
        row["upstream"] = source
        row["citation"] = citations[profile["cite"]]
        # The manifest and the analysis file must agree on what was pinned, or the page
        # would cite one revision while reporting numbers from another.
        recorded = row.get("revision")
        if recorded and source.get("revision") and recorded != source["revision"]:
            raise VerificationError(
                f"{row['id']}: analysis pinned {recorded[:12]} but manifest pins "
                f"{source['revision'][:12]}"
            )
        if row.get("license") and source.get("license") and row["license"] != source["license"]:
            raise VerificationError(f"{row['id']}: licence disagrees with the manifest")


def verify_totals(matrix: dict, rows: list[dict]) -> None:
    """Recompute the summary from the rows so the page cannot overstate the audit."""

    totals = matrix["totals"]
    external = [r for r in rows if r["family"] == "External benchmark audit"]
    screened = [r for r in external if r["status"] == "screened"]

    checks = {
        "named_benchmarks": (len(external), totals["named_benchmarks"]),
        "screened_sources": (len(screened), totals["screened_sources"]),
        "gated_sources": (
            len([r for r in external if r["status"] == "gated"]),
            totals["gated_sources"],
        ),
        "screened_tasks": (
            sum(r["tasks"] or 0 for r in screened),
            totals["screened_tasks"],
        ),
        "screened_reference_actions": (
            sum(r["actions"] or 0 for r in screened),
            totals["screened_reference_actions"],
        ),
        "screened_tasks_with_candidate_region": (
            sum(r["candidate_regions"] or 0 for r in screened),
            totals["screened_tasks_with_candidate_region"],
        ),
        "executed_external_paths": (
            len([r for r in external if r["execution_status"] == "executed"]),
            totals["executed_external_paths"],
        ),
        "provider_calls": (
            sum(r["provider_calls"] or 0 for r in external),
            totals["provider_calls"],
        ),
    }
    for label, (derived, recorded) in checks.items():
        if derived != recorded:
            raise VerificationError(
                f"{label}: rows give {derived}, recorded summary says {recorded}"
            )

    if matrix.get("secrets_serialized") is not False:
        raise VerificationError("benchmark matrix does not assert secrets_serialized=false")
    for row in rows:
        if row["status"] == "gated" and (row["actions"] or row["candidate_regions"]):
            raise VerificationError(f"{row['id']}: gated source carries imputed metrics")


def stat_tiles(matrix: dict, rows: list[dict]) -> str:
    totals = matrix["totals"]
    tiles = [
        (totals["named_benchmarks"], "named external benchmarks audited"),
        (totals["executed_external_paths"], "external paths actually executed"),
        (totals["measured_compiler_benchmarks"], "paths where the compiler itself ran"),
        (f"{totals['screened_tasks']:,}", "reference tasks screened for structure"),
        (f"{totals['screened_reference_actions']:,}", "reference actions screened"),
        (totals["gated_sources"], "source withheld upstream, nothing imputed"),
    ]
    cells = "".join(
        f'<div class="tile"><strong>{esc(value)}</strong><span>{esc(label)}</span></div>'
        for value, label in tiles
    )
    return f'<section class="tiles" aria-label="Audit summary">{cells}</section>'


def facet_options(rows: list[dict], key: str) -> list[str]:
    return sorted({str(r[key]) for r in rows if r.get(key)})


def render(matrix: dict, rows: list[dict], content: dict[str, list[dict]] | None = None) -> str:
    payload = json.dumps(rows, separators=(",", ":"), sort_keys=True)
    content_payload = json.dumps(content or {}, separators=(",", ":"), sort_keys=True)
    boundary = matrix["claim_boundary"]
    boundary_items = "".join(
        f"<li><code>{esc(k)}</code> is <strong>{esc(str(v).lower())}</strong></li>"
        for k, v in sorted(boundary.items())
    )
    glossary_items = "".join(
        f'<div class="legend-row"><strong class="term">{esc(term)}</strong>'
        f"<p>{esc(text)}</p></div>"
        for term, text in GLOSSARY.items()
    ) + f'<p class="glossary-caveat">{esc(PAPER_CAVEAT)}</p>'
    status_legend = "".join(
        f'<div class="legend-row"><span class="badge badge-{esc(k)}">{esc(k)}</span>'
        f"<p>{esc(v)}</p></div>"
        for k, v in STATUS_COPY.items()
    )

    def select(name: str, label: str, key: str) -> str:
        options = "".join(
            f'<option value="{esc(v)}">{esc(humanize(v))}</option>'
            for v in facet_options(rows, key)
        )
        return (
            f'<label class="control"><span>{esc(label)}</span>'
            f'<select id="{name}" data-facet="{esc(key)}">'
            f'<option value="">All</option>{options}</select></label>'
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Search and filter every benchmark used in the Guarded Agentic Compaction evaluation, with each row's evidence class, execution status, and claim boundary.">
<title>Benchmark explorer — Guarded Agentic Compaction</title>
<style>
:root {{
  --ink: #10242d; --ink-2: #173742; --paper: #f7f3eb; --paper-2: #eee8dc;
  --white: #fffdf8; --teal: #2a9d8f; --teal-light: #9ed9cf; --blue: #2f6b8a;
  --coral: #d06b4d; --gold: #b8862f; --muted: #64747a;
  --line: rgba(16,36,45,.16); --radius: 16px;
  color-scheme: light;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; color: var(--ink); background: var(--paper);
  font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 16px; line-height: 1.6;
}}
h1, h2, h3 {{ font-family: Georgia, "Times New Roman", serif; font-weight: 600; letter-spacing: -.03em; line-height: 1.1; }}
a {{ color: var(--blue); text-underline-offset: 3px; }}
a:hover {{ color: var(--coral); }}
code {{ font-family: "SFMono-Regular", Consolas, monospace; font-size: .86em; background: rgba(47,107,138,.09); padding: .1rem .35rem; border-radius: 5px; }}
.wrap {{ width: min(100% - 32px, 1180px); margin: 0 auto; }}
.skip {{ position: absolute; left: 16px; top: -80px; background: var(--coral); color: var(--white); padding: 10px 14px; z-index: 20; }}
.skip:focus {{ top: 12px; }}
header.masthead {{ padding: 54px 0 40px; color: var(--white); background: linear-gradient(135deg, var(--ink), #19434e); }}
.eyebrow {{ display: inline-flex; align-items: center; gap: 10px; margin: 0 0 14px; color: var(--teal-light); font-size: .72rem; font-weight: 800; letter-spacing: .16em; text-transform: uppercase; }}
.eyebrow::before {{ content: ""; width: 26px; height: 2px; background: currentColor; }}
header.masthead h1 {{ margin: 0; font-size: clamp(2.3rem, 5vw, 3.6rem); max-width: 900px; }}
header.masthead p {{ max-width: 760px; margin: 18px 0 0; color: rgba(255,253,248,.78); }}
.tiles {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 0; margin-top: 34px; border: 1px solid rgba(255,255,255,.18); border-radius: var(--radius); overflow: hidden; }}
.tile {{ padding: 16px 18px; border-right: 1px solid rgba(255,255,255,.14); }}
.tile:last-child {{ border-right: 0; }}
.tile strong {{ display: block; color: var(--teal-light); font: 600 1.7rem/1.1 Georgia, serif; }}
.tile span {{ display: block; margin-top: 5px; color: rgba(255,253,248,.72); font-size: .76rem; }}
main {{ padding: 40px 0 70px; }}
.controls {{ position: sticky; top: 0; z-index: 10; padding: 18px; margin-bottom: 26px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--white); box-shadow: 0 10px 30px rgba(16,36,45,.07); }}
.control-grid {{ display: grid; grid-template-columns: minmax(220px, 1.6fr) repeat(4, minmax(130px, 1fr)) auto; gap: 14px; align-items: end; }}
.control {{ display: grid; gap: 6px; }}
.control > span {{ color: var(--muted); font-size: .7rem; font-weight: 700; letter-spacing: .09em; text-transform: uppercase; }}
input[type="search"], select {{ width: 100%; min-height: 42px; padding: 8px 12px; border: 1px solid var(--line); border-radius: 10px; background: var(--paper); color: var(--ink); font: inherit; font-size: .92rem; }}
input[type="search"]:focus-visible, select:focus-visible, button:focus-visible, summary:focus-visible {{ outline: 3px solid var(--teal); outline-offset: 2px; }}
button {{ min-height: 42px; padding: 9px 16px; border: 1px solid var(--line); border-radius: 999px; background: var(--paper); color: var(--ink); font: inherit; font-weight: 650; font-size: .88rem; cursor: pointer; }}
button:hover {{ background: var(--paper-2); }}
.status-line {{ display: flex; flex-wrap: wrap; gap: 10px; justify-content: space-between; align-items: baseline; margin-top: 14px; color: var(--muted); font-size: .85rem; }}
.sort-inline {{ display: inline-flex; align-items: center; gap: 8px; color: var(--muted); font-size: .8rem; font-weight: 650; }}
.sort-inline select {{ width: auto; min-height: 36px; padding: 5px 10px; font-size: .84rem; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 18px; }}
.card {{ display: flex; flex-direction: column; padding: 22px 24px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--white); box-shadow: 0 10px 28px rgba(16,36,45,.06); }}
.card-head {{ display: flex; gap: 12px; justify-content: space-between; align-items: start; }}
.card h3 {{ margin: 0 0 4px; font-size: 1.18rem; }}
.card-raw {{ color: var(--muted); font-size: .74rem; font-family: "SFMono-Regular", Consolas, monospace; }}
.badge {{ display: inline-block; padding: 3px 11px; border-radius: 999px; font-size: .7rem; font-weight: 700; letter-spacing: .04em; white-space: nowrap; }}
.badge-measured {{ color: #14584f; background: rgba(42,157,143,.18); }}
.badge-screened {{ color: #234f66; background: rgba(47,107,138,.15); }}
.badge-gated {{ color: #8a3a1c; background: rgba(208,107,77,.18); }}
.badge-preflight {{ color: #6d5115; background: rgba(214,168,75,.22); }}
.scope {{ margin: 12px 0 0; color: #37505a; font-size: .89rem; }}
.metrics {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 1px; margin: 16px 0 0; background: var(--line); border: 1px solid var(--line); border-radius: 11px; overflow: hidden; }}
.metric {{ padding: 9px 12px; background: var(--white); }}
.metric dt {{ color: var(--muted); font-size: .68rem; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; }}
.metric dd {{ margin: 2px 0 0; font-variant-numeric: tabular-nums; font-weight: 600; font-size: .98rem; }}
.flags {{ display: flex; flex-wrap: wrap; gap: 7px; margin-top: 14px; }}
.flag {{ padding: 3px 10px; border: 1px solid var(--line); border-radius: 999px; font-size: .72rem; color: var(--muted); }}
.flag-no {{ border-color: rgba(208,107,77,.4); color: #8a3a1c; }}
.flag-yes {{ border-color: rgba(42,157,143,.45); color: #14584f; }}
details {{ margin-top: 16px; border-top: 1px solid var(--line); padding-top: 12px; }}
summary {{ cursor: pointer; color: var(--blue); font-size: .84rem; font-weight: 650; }}
.detail-block {{ margin-top: 12px; }}
.detail-block h4 {{ margin: 0 0 6px; color: var(--muted); font-size: .68rem; font-weight: 700; letter-spacing: .09em; text-transform: uppercase; }}
.kv {{ margin: 0; font-size: .84rem; }}
.kv div {{ display: flex; justify-content: space-between; gap: 12px; padding: 4px 0; border-bottom: 1px dotted var(--line); }}
.kv dt {{ color: #37505a; }}
.kv dd {{ margin: 0; font-variant-numeric: tabular-nums; font-weight: 600; }}
.notes {{ margin: 8px 0 0; padding-left: 18px; color: var(--muted); font-size: .82rem; }}
.prov {{ margin-top: 10px; color: var(--muted); font-size: .74rem; word-break: break-all; }}
.profile {{ display: grid; grid-template-columns: minmax(0,1.35fr) minmax(240px,.65fr); gap: 26px; align-items: start; margin: 0 0 22px; padding: 20px 22px; border: 1px solid var(--line); border-radius: 14px; background: var(--paper); }}
.profile h3 {{ margin: 0 0 6px; font-size: .72rem; font-weight: 700; letter-spacing: .09em; text-transform: uppercase; color: var(--muted); font-family: Inter, sans-serif; }}
.profile p {{ margin: 0 0 14px; color: #294149; font-size: .9rem; }}
.profile p:last-child {{ margin-bottom: 0; }}
.profile-meta {{ font-size: .82rem; }}
.profile-meta div {{ display: flex; gap: 10px; justify-content: space-between; padding: 5px 0; border-bottom: 1px dotted var(--line); }}
.profile-meta dt {{ color: var(--muted); white-space: nowrap; }}
.profile-meta dd {{ margin: 0; text-align: right; word-break: break-word; }}
.profile-cite {{ padding: 12px 14px; border-left: 3px solid var(--teal); background: var(--white); font-size: .82rem; color: #294149; }}
.profile-cite em {{ display: block; font-style: normal; font-weight: 650; margin-bottom: 3px; }}
.term {{ font-size: .84rem; }}
.glossary-caveat {{ margin: 16px 0 0; padding-top: 14px; border-top: 1px solid var(--line); color: var(--muted); font-size: .85rem; }}
.card-tests {{ margin: 10px 0 0; color: #294149; font-size: .87rem; }}
@media (max-width: 860px) {{ .profile {{ grid-template-columns: 1fr; }} }}
.browser {{ margin-bottom: 34px; padding: 26px 28px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--white); box-shadow: 0 12px 34px rgba(16,36,45,.07); }}
.back {{ margin-bottom: 16px; }}
.browser h2 {{ margin: 0 0 6px; font-size: 1.9rem; }}
.browser-sub {{ margin: 0 0 18px; color: var(--muted); font-size: .88rem; }}
.tabs {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }}
.tab {{ padding: 7px 15px; border: 1px solid var(--line); border-radius: 999px; background: var(--paper); font-size: .84rem; font-weight: 650; cursor: pointer; }}
.tab[aria-selected="true"] {{ border-color: var(--teal); background: rgba(42,157,143,.14); color: #14584f; }}
.collection-note {{ margin: 0 0 16px; color: #37505a; font-size: .86rem; }}
.record-controls {{ display: flex; flex-wrap: wrap; gap: 16px; align-items: end; justify-content: space-between; margin-bottom: 14px; }}
.record-controls .control {{ min-width: 260px; }}
#record-count {{ color: var(--muted); font-size: .84rem; }}
.table-scroll {{ overflow-x: auto; }}
.record-table {{ width: 100%; border-collapse: collapse; font-size: .85rem; }}
.record-table th {{ position: sticky; top: 0; z-index: 1; padding: 10px 12px; border-bottom: 1px solid var(--line); background: var(--white); color: var(--muted); font-size: .68rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; text-align: left; white-space: nowrap; }}
.record-table td {{ padding: 10px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }}
.record-table tbody tr:nth-child(even) {{ background: rgba(238,232,220,.4); }}
.record-table td.num {{ font-variant-numeric: tabular-nums; text-align: right; white-space: nowrap; }}
.record-table td.mono {{ font-family: "SFMono-Regular", Consolas, monospace; font-size: .8rem; }}
.record-table td.id {{ font-family: "SFMono-Regular", Consolas, monospace; font-size: .8rem; white-space: nowrap; }}
.record-table td.text {{ min-width: 260px; max-width: 460px; }}
.record-table pre {{ margin: 0; padding: 11px 13px; overflow-x: auto; border-radius: 9px; background: var(--ink); color: #eaf6f3; font-size: .76rem; line-height: 1.5; }}
.yes {{ color: #14584f; font-weight: 700; }}
.no {{ color: #8a3a1c; font-weight: 700; }}
.pager-top {{ justify-content: flex-start; margin: 0 0 12px; padding-bottom: 12px; border-bottom: 1px solid var(--line); }}
.pager {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; justify-content: center; margin-top: 18px; }}
.pager button[disabled] {{ opacity: .42; cursor: not-allowed; }}
.pager .page-of {{ color: var(--muted); font-size: .84rem; font-variant-numeric: tabular-nums; }}
.browse-btn {{ margin-top: 14px; width: 100%; border-color: rgba(42,157,143,.5); color: #14584f; background: rgba(42,157,143,.1); }}
.browse-btn:hover {{ background: rgba(42,157,143,.18); }}
.no-records {{ margin: 0; padding: 20px 22px; border-left: 4px solid var(--coral); border-radius: 0 12px 12px 0; background: var(--paper); color: #294149; font-size: .9rem; }}
.no-content {{ margin-top: 14px; color: var(--muted); font-size: .8rem; font-style: italic; }}
.empty {{ padding: 40px; border: 1px dashed var(--line); border-radius: var(--radius); text-align: center; color: var(--muted); }}
.panel {{ margin-top: 44px; padding: 26px 28px; border-left: 4px solid var(--coral); border-radius: 0 var(--radius) var(--radius) 0; background: var(--white); }}
.panel h2 {{ margin: 0 0 10px; font-size: 1.5rem; }}
.panel ul {{ margin: 10px 0 0; padding-left: 20px; color: #37505a; font-size: .9rem; }}
.legend {{ margin-top: 28px; padding: 24px 26px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--white); }}
.legend h2 {{ margin: 0 0 14px; font-size: 1.35rem; }}
.legend-row {{ display: grid; grid-template-columns: 110px 1fr; gap: 14px; align-items: start; padding: 7px 0; }}
.legend-row p {{ margin: 0; color: #37505a; font-size: .88rem; }}
footer {{ padding: 34px 0; color: rgba(255,253,248,.7); background: #0b1c22; font-size: .84rem; }}
footer a {{ color: rgba(255,253,248,.78); }}
@media (max-width: 1000px) {{
  .tiles {{ grid-template-columns: repeat(3, 1fr); }}
  .tile:nth-child(3) {{ border-right: 0; }}
  .control-grid {{ grid-template-columns: 1fr 1fr; }}
}}
@media (max-width: 620px) {{
  .tiles {{ grid-template-columns: 1fr 1fr; }}
  .control-grid {{ grid-template-columns: 1fr; }}
  .controls {{ position: static; }}
  .legend-row {{ grid-template-columns: 1fr; }}
}}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; }} }}
</style>
</head>
<body>
<a class="skip" href="#results">Skip to results</a>
<header class="masthead"><div class="wrap">
  <p class="eyebrow">Guarded Agentic Compaction</p>
  <h1>Every benchmark in the evaluation, and what each one can prove.</h1>
  <p>Ten named external benchmarks plus the frozen multidomain record sources. The
  evaluation deliberately does not average them: a screened reference plan, an executed
  simulator, a real compiler run, and a source we were denied access to support different
  claims, so each row keeps its own substrate, denominator, execution status, and
  boundary.</p>
  {stat_tiles(matrix, rows)}
</div></header>

<main><div class="wrap">
  <section id="browser" class="browser" aria-labelledby="browser-title" hidden>
    <button type="button" id="back" class="back">&larr; All benchmarks</button>
    <h2 id="browser-title"></h2>
    <p id="browser-sub" class="browser-sub"></p>
    <div id="profile" class="profile"></div>
    <div id="tabs" class="tabs" role="tablist" aria-label="Record collections"></div>
    <p id="collection-note" class="collection-note"></p>
    <div class="record-controls">
      <label class="control"><span>Filter records</span>
        <input type="search" id="rq" placeholder="Filter these records&hellip;" autocomplete="off"></label>
      <span id="record-count" role="status" aria-live="polite"></span>
    </div>
    <nav id="pager-top" class="pager pager-top" aria-label="Record pages (top)"></nav>
    <p id="no-records" class="no-records" hidden></p>
    <div class="table-scroll"><table id="record-table" class="record-table"><thead></thead><tbody></tbody></table></div>
    <nav id="pager" class="pager" aria-label="Record pages"></nav>
  </section>

  <form class="controls" id="controls" role="search" aria-label="Filter benchmarks" onsubmit="return false">
    <div class="control-grid">
      <label class="control"><span>Search</span>
        <input type="search" id="q" placeholder="NESTFUL, simulator, RETIRE&hellip;"
               autocomplete="off"></label>
      {select("f-family", "Family", "family")}
      {select("f-status", "Evidence status", "status")}
      {select("f-substrate", "Substrate", "substrate")}
      {select("f-exec", "Execution", "execution_status")}
      <button type="button" id="reset">Clear</button>
    </div>
    <div class="status-line">
      <span id="count" role="status" aria-live="polite"></span>
      <label class="sort-inline">Sort
        <select id="sort" aria-label="Sort results">
          <option value="name">by name</option>
          <option value="tasks">by tasks (high to low)</option>
          <option value="actions">by reference actions (high to low)</option>
          <option value="candidate_regions">by candidate regions (high to low)</option>
          <option value="status">by evidence status</option>
        </select>
      </label>
    </div>
  </form>

  <section id="results" class="grid" aria-label="Benchmarks"></section>
  <p class="empty" id="empty" hidden>No benchmark matches those filters. <button type="button" id="reset2">Clear filters</button></p>

  <section class="panel" aria-labelledby="boundary-h">
    <h2 id="boundary-h">What this audit does not claim</h2>
    <p>These flags are recorded in the evidence file itself and are fail-closed, so the
    matrix cannot quietly upgrade weaker evidence:</p>
    <ul>{boundary_items}</ul>
  </section>

  <section class="legend" aria-labelledby="glossary-h">
    <h2 id="glossary-h">What the numbers mean</h2>
    {glossary_items}
  </section>

  <section class="legend" aria-labelledby="legend-h">
    <h2 id="legend-h">Reading the evidence status</h2>
    {status_legend}
  </section>
</div></main>

<footer><div class="wrap">
  <p>Generated from <code>paper/{esc(MATRIX)}</code> and <code>paper/{esc(MULTIDOMAIN)}</code>
  by <code>scripts/build_benchmark_explorer.py</code>, which recomputes every headline total
  from the per-benchmark rows and fails closed if they disagree.</p>
  <p><a href="../../site/method.html">Method and certificates</a> &middot;
  <a href="../README.md">Benchmark suite README</a> &middot;
  <a href="https://github.com/rrahimi-uci/guarded-agentic-compaction">Source</a></p>
</div></footer>

<script type="application/json" id="data">{payload}</script>
<script type="application/json" id="content">{content_payload}</script>
<script>
(function () {{
  "use strict";
  const rows = JSON.parse(document.getElementById("data").textContent);
  const CONTENT = JSON.parse(document.getElementById("content").textContent);
  const results = document.getElementById("results");
  const empty = document.getElementById("empty");
  const count = document.getElementById("count");
  const q = document.getElementById("q");
  const sort = document.getElementById("sort");
  const facets = Array.from(document.querySelectorAll("select[data-facet]"));

  const num = (v) => (v === null || v === undefined ? "\\u2014" : v.toLocaleString("en-US"));
  const esc = (v) => String(v).replace(/[&<>"]/g, (c) =>
    ({{ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }})[c]);
  const words = (v) => String(v || "").replace(/_/g, " ");

  // One flat haystack per row so a single query can reach names, scope, licence,
  // gate outcomes and notes without the caller knowing the schema.
  rows.forEach((r) => {{
    r._hay = [r.name, r.raw, r.family, r.status, r.substrate, r.execution_status,
              r.evidence_stage, r.license, r.scope, r.reason, r.gate,
              (r.notes || []).join(" "), Object.keys(r.effects || {{}}).join(" "),
              Object.keys(r.blocks || {{}}).join(" ")]
             .filter(Boolean).join(" ").toLowerCase();
  }});

  // Three-state on purpose: null means the evidence file records no verdict, which is
  // not the same as recording "no". Absent verdicts render nothing at all.
  function flag(state, label) {{
    if (state === null || state === undefined) return "";
    return '<span class="flag ' + (state ? "flag-yes" : "flag-no") + '">' +
      (state ? "\\u2713 " : "\\u2717 ") + esc(label) + "</span>";
  }}

  function kv(title, obj) {{
    const keys = Object.keys(obj || {{}});
    if (!keys.length) return "";
    const body = keys.sort().map((k) =>
      "<div><dt>" + esc(words(k)) + "</dt><dd>" +
      (typeof obj[k] === "number" ? num(obj[k]) : esc(words(obj[k]))) + "</dd></div>").join("");
    return '<div class="detail-block"><h4>' + esc(title) + '</h4><dl class="kv">' + body + "</dl></div>";
  }}

  function card(r) {{
    const cells = [
      ["Tasks", r.tasks],
      ["Reference actions", r.actions],
      ["Tasks w/ candidate region", r.candidate_regions],
      ["Live provider calls", r.provider_calls],
    ];
    // A gated source has no metrics because none are imputed for it; a grid of dashes
    // would imply we measured zero rather than that we were never given the bytes.
    const anyMetric = cells.some(([, v]) => v !== null && v !== undefined);
    const metrics = !anyMetric ? "" : '<dl class="metrics">' + cells.map(([k, v]) =>
      "<div class=\\"metric\\"><dt>" + k + "</dt><dd>" + num(v) + "</dd></div>").join("") + "</dl>";

    const notes = (r.notes || []).length
      ? '<ul class="notes">' + r.notes.map((n) => "<li>" + esc(n) + "</li>").join("") + "</ul>"
      : "";

    const provenance = [
      r.source ? "Source: <code>" + esc(r.source) + "</code>" : "",
      r.source_sha256 ? "sha256 " + esc(r.source_sha256.slice(0, 16)) + "\\u2026" : "",
      r.revision ? "revision " + esc(r.revision.slice(0, 10)) : "",
    ].filter(Boolean).join(" &middot; ");

    return '<article class="card">' +
      '<div class="card-head"><div><h3>' + esc(r.name) + "</h3>" +
      '<div class="card-raw">' + esc(r.raw) + "</div></div>" +
      '<span class="badge badge-' + esc(r.status) + '">' + esc(r.status) + "</span></div>" +
      (r.tests ? '<p class="card-tests">' + esc(r.tests) + "</p>" : "") +
      (r.scope ? '<p class="scope"><strong>In this study:</strong> ' + esc(r.scope) + "</p>" : "") +
      (r.reason ? '<p class="scope"><strong>Blocked:</strong> ' + esc(r.reason) + "</p>" : "") +
      metrics +
      '<div class="flags">' +
        flag(r.compiler_ran, "compiler executed") +
        flag(r.quality_licensed, "quality claim licensed") +
        flag(r.efficiency_licensed, "efficiency claim licensed") +
        (r.gate ? '<span class="flag">gate: ' + esc(r.gate) + "</span>" : "") +
        (r.substrate ? '<span class="flag">' + esc(words(r.substrate)) + "</span>" : "") +
      "</div>" +
      "<details><summary>Evidence detail</summary>" +
        kv("Structure", r.structure) +
        kv("Effect classes", r.effects) +
        kv("Block reasons", r.blocks) +
        kv("Measured compiler result", r.measured) +
        kv("Execution record", r.execution) +
        '<div class="detail-block"><h4>Provenance</h4>' +
          '<p class="prov">' + (provenance || "\\u2014") +
          (r.license ? "<br>Licence: " + esc(r.license) : "") +
          (r.credential ? "<br>Credential required: <code>" + esc(r.credential) + "</code>" : "") +
          "</p>" + notes + "</div>" +
      "</details>" +
      '<button type="button" class="browse-btn" data-browse="' + esc(r.id) + '">' +
        (CONTENT[r.id]
          ? "Browse " + r.record_count.toLocaleString("en-US") + " records"
          : "Details \\u2014 no records shipped") + " \\u2192</button>" +
      "</article>";
  }}

  function apply() {{
    const needle = q.value.trim().toLowerCase();
    const active = facets.filter((s) => s.value);
    let shown = rows.filter((r) => {{
      if (needle && !r._hay.includes(needle)) return false;
      return active.every((s) => String(r[s.dataset.facet]) === s.value);
    }});

    const mode = sort.value;
    shown.sort((a, b) => {{
      if (mode === "name") return a.name.localeCompare(b.name);
      if (mode === "status") return String(a.status).localeCompare(String(b.status)) ||
        a.name.localeCompare(b.name);
      return (b[mode] || 0) - (a[mode] || 0) || a.name.localeCompare(b.name);
    }});

    results.innerHTML = shown.map(card).join("");
    empty.hidden = shown.length > 0;
    // Deliberately not a pooled denominator: these rows sit on different substrates and
    // the evaluation does not average them, so the record count is labelled as a sum of
    // per-row counts rather than presented as one benchmark size.
    const records = shown.reduce((sum, r) => sum + (r.tasks || 0), 0);
    count.textContent = shown.length + " of " + rows.length + " benchmarks" +
      (records ? " \\u00b7 " + records.toLocaleString("en-US") +
        " records across mixed substrates (not a pooled denominator)" : "");
  }}

  function reset() {{
    q.value = "";
    facets.forEach((s) => {{ s.value = ""; }});
    sort.value = "name";
    apply();
    q.focus();
  }}

  // ---- Record browser -------------------------------------------------------------
  // Collections can run to thousands of rows, so only the current page is ever put in
  // the DOM; filtering recomputes the page set rather than hiding rendered nodes.
  const PAGE = {PAGE_SIZE};
  const browser = document.getElementById("browser");
  const overview = [document.getElementById("controls"), results, empty];
  const tabsEl = document.getElementById("tabs");
  const noteEl = document.getElementById("collection-note");
  const rq = document.getElementById("rq");
  const recordCount = document.getElementById("record-count");
  const table = document.getElementById("record-table");
  const pager = document.getElementById("pager");
  const pagerTop = document.getElementById("pager-top");
  const noRecords = document.getElementById("no-records");
  let current = null;   // {{row, groups}}
  let groupIndex = 0;
  let page = 1;

  function cell(value, kind) {{
    if (value === null || value === undefined || value === "") return "\\u2014";
    if (kind === "bool") {{
      const truthy = value === true || value === "true" || value === "True";
      return '<span class="' + (truthy ? "yes" : "no") + '">' + (truthy ? "yes" : "no") + "</span>";
    }}
    if (kind === "pre") return "<pre>" + esc(value) + "</pre>";
    if (kind === "num" && typeof value === "number") return value.toLocaleString("en-US");
    // "id" and "mono" differ only in wrapping, handled in CSS.
    return esc(value);
  }}

  function matchRecord(record, needle) {{
    if (!needle) return true;
    for (const key in record) {{
      if (String(record[key]).toLowerCase().includes(needle)) return true;
    }}
    return false;
  }}

  function renderPage() {{
    const group = current.groups[groupIndex];
    const needle = rq.value.trim().toLowerCase();
    const matched = needle ? group.records.filter((r) => matchRecord(r, needle)) : group.records;
    const pages = Math.max(1, Math.ceil(matched.length / PAGE));
    if (page > pages) page = pages;
    const start = (page - 1) * PAGE;
    const slice = matched.slice(start, start + PAGE);

    table.querySelector("thead").innerHTML = "<tr><th>#</th>" +
      group.columns.map((c) => "<th>" + esc(c.label) + "</th>").join("") + "</tr>";
    table.querySelector("tbody").innerHTML = slice.map((rec, i) =>
      '<tr><td class="num">' + (start + i + 1).toLocaleString("en-US") + "</td>" +
      group.columns.map((c) => '<td class="' + c.kind + '">' + cell(rec[c.key], c.kind) + "</td>").join("") +
      "</tr>").join("") ||
      '<tr><td colspan="' + (group.columns.length + 1) + '">No record matches that filter.</td></tr>';

    recordCount.textContent = matched.length
      ? "Showing " + (start + 1).toLocaleString("en-US") + "\\u2013" +
        Math.min(start + PAGE, matched.length).toLocaleString("en-US") + " of " +
        matched.length.toLocaleString("en-US") + (needle ? " matching" : "") + " records"
      : "0 of " + group.count.toLocaleString("en-US") + " records match";

    const pagerHtml = pages > 1
      ? '<button type="button" data-page="1"' + (page === 1 ? " disabled" : "") + ">\\u00ab First</button>" +
        '<button type="button" data-page="' + (page - 1) + '"' + (page === 1 ? " disabled" : "") + ">\\u2039 Prev</button>" +
        '<span class="page-of">Page ' + page.toLocaleString("en-US") + " of " + pages.toLocaleString("en-US") + "</span>" +
        '<button type="button" data-page="' + (page + 1) + '"' + (page === pages ? " disabled" : "") + ">Next \\u203a</button>" +
        '<button type="button" data-page="' + pages + '"' + (page === pages ? " disabled" : "") + ">Last \\u00bb</button>"
      : "";
    pager.innerHTML = pagerHtml;
    pagerTop.innerHTML = pagerHtml;
  }}

  function renderProfile(r) {{
    const el = document.getElementById("profile");
    if (!r.tests && !r.upstream) {{ el.hidden = true; el.innerHTML = ""; return; }}
    el.hidden = false;
    const u = r.upstream || {{}};
    const meta = [
      ["Upstream", u.repository
        ? '<a href="' + esc(u.repository) + '" rel="noopener noreferrer">' +
          esc(String(u.repository).replace(/^https?:\\/\\//, "").replace(/\\.git$/, "")) + "</a>"
        : null],
      ["Pinned revision", u.revision ? "<code>" + esc(String(u.revision).slice(0, 12)) + "</code>" : null],
      ["Retrieved as", u.kind ? words(u.kind) : null],
      ["Licence", u.license || r.license],
      ["Credential", u.auth_env ? "<code>" + esc(u.auth_env) + "</code>" : null],
      ["Substrate", r.substrate ? words(r.substrate) : null],
      ["Evidence stage", r.evidence_stage ? words(r.evidence_stage) : null],
    ].filter((pair) => pair[1]);

    const cite = r.citation
      ? '<div class="profile-cite"><em>' + esc(r.citation.title) + "</em>" +
        esc(r.citation.authors) + (r.citation.year ? ", " + esc(r.citation.year) : "") +
        (r.citation.venue ? ". " + esc(r.citation.venue) : "") + "</div>"
      : "";

    el.innerHTML =
      "<div>" +
        (r.tests ? "<h3>What the benchmark tests</h3><p>" + esc(r.tests) + "</p>" : "") +
        (r.role ? "<h3>Why it is in this work</h3><p>" + esc(r.role) + "</p>" : "") +
        (r.reason ? "<h3>Why it is blocked</h3><p>" + esc(r.reason) + "</p>" : "") +
      "</div><div>" +
        (meta.length
          ? '<h3>Provenance</h3><dl class="profile-meta">' + meta.map((pair) =>
              "<div><dt>" + pair[0] + "</dt><dd>" + pair[1] + "</dd></div>").join("") + "</dl>"
          : "") +
        cite +
      "</div>";
  }}

  function renderTabs() {{
    tabsEl.hidden = current.groups.length < 2;
    tabsEl.innerHTML = current.groups.map((g, i) =>
      '<button type="button" class="tab" role="tab" data-group="' + i + '" aria-selected="' +
      (i === groupIndex) + '">' + esc(g.title) + " (" + g.count.toLocaleString("en-US") + ")</button>"
    ).join("");
    noteEl.innerHTML = esc(current.groups[groupIndex].note) +
      ' <code>' + esc(current.groups[groupIndex].source) + "</code>";
  }}

  function openBrowser(id, replaceHash, wanted) {{
    const row = rows.find((r) => r.id === id);
    if (!row) return;
    const groups = CONTENT[id] || [];
    current = {{ row: row, groups: groups }};
    groupIndex = Number.isInteger(wanted) && groups[wanted] ? wanted : 0;
    page = 1;
    rq.value = "";
    document.getElementById("browser-title").textContent = current.row.name;
    document.getElementById("browser-sub").textContent =
      current.row.raw + " \\u00b7 " + current.row.family + " \\u00b7 " + current.row.status;
    renderProfile(current.row);
    const hasRecords = current.groups.length > 0;
    ["tabs", "collection-note", "pager-top", "pager"].forEach((id2) => {{
      document.getElementById(id2).hidden = !hasRecords;
    }});
    document.querySelector(".record-controls").hidden = !hasRecords;
    document.querySelector(".table-scroll").hidden = !hasRecords;
    noRecords.hidden = hasRecords;
    if (hasRecords) {{
      renderTabs();
      renderPage();
    }} else {{
      noRecords.innerHTML = "<strong>No records are shipped for this path.</strong> " +
        esc(current.row.no_content_reason) +
        ". Nothing is imputed in its place, so this row contributes no task or compiler "
        + "metric to the audit.";
    }}
    browser.hidden = false;
    overview.forEach((el) => {{ el.hidden = true; }});
    if (!replaceHash) location.hash = groupIndex ? id + "/" + groupIndex : id;
    browser.scrollIntoView({{ block: "start" }});
  }}

  function closeBrowser() {{
    browser.hidden = true;
    current = null;
    overview.forEach((el) => {{ el.hidden = false; }});
    empty.hidden = true;
    apply();
    if (location.hash) history.pushState("", document.title, location.pathname);
  }}

  results.addEventListener("click", (event) => {{
    const btn = event.target.closest("[data-browse]");
    if (btn) openBrowser(btn.dataset.browse);
  }});
  tabsEl.addEventListener("click", (event) => {{
    const tab = event.target.closest("[data-group]");
    if (!tab) return;
    groupIndex = Number(tab.dataset.group);
    page = 1;
    rq.value = "";
    renderTabs();
    renderPage();
    history.replaceState("", document.title,
      location.pathname + "#" + current.row.id + (groupIndex ? "/" + groupIndex : ""));
  }});
  function onPagerClick(event) {{
    const btn = event.target.closest("[data-page]");
    if (!btn || btn.disabled) return;
    page = Number(btn.dataset.page);
    renderPage();
    // Keep the reader at the start of the new page instead of stranding them
    // thousands of pixels down where the bottom pager was.
    document.getElementById("pager-top").scrollIntoView({{ block: "center" }});
  }}
  pager.addEventListener("click", onPagerClick);
  pagerTop.addEventListener("click", onPagerClick);
  rq.addEventListener("input", () => {{ page = 1; renderPage(); }});
  document.getElementById("back").addEventListener("click", closeBrowser);
  function fromHash() {{
    const raw = location.hash.replace(/^#/, "");
    if (!raw) return null;
    const [id, group] = raw.split("/");
    return rows.some((r) => r.id === id) ? {{ id: id, group: Number(group) }} : null;
  }}
  window.addEventListener("hashchange", () => {{
    const target = fromHash();
    if (target) openBrowser(target.id, true, target.group);
    else if (current) closeBrowser();
  }});

  q.addEventListener("input", apply);
  sort.addEventListener("change", apply);
  facets.forEach((s) => s.addEventListener("change", apply));
  document.getElementById("reset").addEventListener("click", reset);
  document.getElementById("reset2").addEventListener("click", reset);
  apply();
  // A shared link like #nestful or #nestful/1 lands on that exact table.
  const initial = fromHash();
  if (initial) openBrowser(initial.id, true, initial.group);
}})();
</script>
</body>
</html>
"""


def main() -> None:
    matrix = load(MATRIX)
    if matrix.get("schema") != "agent-compaction-external-benchmark-matrix/v1":
        raise VerificationError("unexpected external benchmark matrix schema")
    validation = load(MULTIDOMAIN)
    if validation.get("schema") != "agent-compaction-multidomain-validation/v1":
        raise VerificationError("unexpected multidomain validation schema")

    rows = rows_from_matrix(matrix) + rows_from_multidomain(validation)
    verify_totals(matrix, rows)
    attach_profiles(rows)
    content = attach_content(rows, matrix)
    verify_content(content, matrix)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(matrix, rows, content), encoding="utf-8")
    browsable = sum(group["count"] for groups in content.values() for group in groups)
    without = [r["id"] for r in rows if not r.get("record_count")]
    print(
        f"wrote {OUTPUT.relative_to(ROOT)}: {len(rows)} benchmarks, "
        f"{browsable:,} browsable records across {len(content)} of {len(rows)} rows "
        f"({OUTPUT.stat().st_size / 1024:.0f} KiB); all recomputed totals agree"
    )
    # Never let a row silently look empty: say which ones ship no records and why.
    for key in without:
        row = next(r for r in rows if r["id"] == key)
        print(f"  no records: {key} — {row['no_content_reason']}")


if __name__ == "__main__":
    main()
