#!/usr/bin/env python3
"""Provider-free AgentHop source, cohort, and dependence preflight.

This does not read answers, run an agent, synthesize a candidate, or claim
independent calibration. Gold/bridge paper identifiers are used only to audit
the source graph and a conservative path-overlap sensitivity.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/results/agenthop_source_feasibility/report.json"
CODE_REVISION = "419407e1b06f95f6baa0a6d2c12da43fc53045c2"
DATA_REVISION = "24e7076425ead02de2f858d8963846dc981ef9e3"
QA_SHA256 = "02ae03d17fa6d6d4c813bcea774eee99b768663764f4fe27f71739df9f60e62c"
GRAPHS_SHA256 = "48bfc5cc1ac580bcd0a92b7a12752047455b58dbb901ccd864b222ad1ab5b572"
PAPERS_SHA256 = "cf86f1ef81dc1d7693ad1412083aa5f45a05f8d539ef45b60b7df2504354f3af"
LOADER_SHA256 = "8b6d18235cb6cefb21284dfd7e8d40d9eceaac6981f01ae15de25a4034889cf7"
TOOLS_SHA256 = "99b21367fa7cdd5c7276dd9cdfd56e442778d7fb17934d22de3e552e317dd6b9"
HARNESS_SHA256 = "feca15851e88c444fdc6b235d53e7b6c2759aa6bcd8cc50b4102c95c19e0d9f2"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class Components:
    """Connected components induced by shared paper identifiers."""

    def __init__(self, count: int):
        self.parent = list(range(count))
        self.owner: dict[str, int] = {}

    def root(self, index: int) -> int:
        while self.parent[index] != index:
            self.parent[index] = self.parent[self.parent[index]]
            index = self.parent[index]
        return index

    def add(self, index: int, papers: set[str]) -> None:
        for paper in papers:
            prior = self.owner.setdefault(paper, index)
            self.parent[self.root(index)] = self.root(prior)

    def sizes(self) -> list[int]:
        return sorted(Counter(self.root(i) for i in range(len(self.parent))).values(), reverse=True)


def build(qa_path: Path, graphs_path: Path, papers_path: Path, code_root: Path) -> dict:
    observed_revision = subprocess.check_output(
        ["git", "-C", str(code_root), "rev-parse", "HEAD"], text=True).strip()
    expected_files = ((qa_path, QA_SHA256), (graphs_path, GRAPHS_SHA256),
        (papers_path, PAPERS_SHA256), (code_root / "data_loader.py", LOADER_SHA256),
        (code_root / "testbed/tools.py", TOOLS_SHA256),
        (code_root / "testbed/harness.py", HARNESS_SHA256))
    if observed_revision != CODE_REVISION or any(digest(path) != expected for path, expected in expected_files):
        raise ValueError("pinned AgentHop code or data drift")

    rows = [json.loads(line) for line in qa_path.open(encoding="utf-8") if line.strip()]
    if len(rows) != 1011 or len({row["id"] for row in rows}) != len(rows):
        raise ValueError("AgentHop QA task IDs changed")
    subtypes = Counter(f"{row['question_type']}/depth-{row['depth']}" for row in rows)
    selected = [row for row in rows if row["question_type"] == "single-target" and row["depth"] == 2]
    if len(selected) != 478 or any(len(row["gold_paper_ids"]) != 1 for row in selected):
        raise ValueError("single-target depth-2 source cohort changed")
    papers: set[str] = set()
    papers_with_sections: set[str] = set()
    with papers_path.open(encoding="utf-8") as source:
        for line in source:
            paper = json.loads(line)
            paper_id = paper["arxiv_id"]
            if paper_id in papers:
                raise ValueError("duplicate paper in source pool")
            papers.add(paper_id)
            if paper.get("sections"):
                papers_with_sections.add(paper_id)
    if len(papers) != 7205 or papers != papers_with_sections:
        raise ValueError("paper pool count or section coverage changed")
    content_coverage = {name: sum(all(p in papers_with_sections for p in ids(row))
        for row in selected) for name, ids in (
            ("seed", lambda row: [row["seed_arxiv_id"]]),
            ("bridge", lambda row: row["bridge_arxiv_ids"]),
            ("gold", lambda row: row["gold_arxiv_ids"]))}
    by_id = {row["id"]: (index, row) for index, row in enumerate(selected)}
    path_components = Components(len(selected))
    full_components = Components(len(selected))
    for index, row in enumerate(selected):
        path_components.add(index, set([row["seed_paper_id"], *row["bridge_paper_ids"],
                                        *row["gold_paper_ids"]]))

    memberships: Counter[str] = Counter()
    path_reachable = 0
    structural_missing: list[str] = []
    seen: set[str] = set()
    node_counts: list[int] = []
    with graphs_path.open(encoding="utf-8") as source:
        for line in source:
            graph = json.loads(line)
            sample_id = graph["sample_id"]
            if sample_id not in by_id:
                continue
            if sample_id in seen:
                raise ValueError("duplicate graph for fixed task")
            seen.add(sample_id)
            index, row = by_id[sample_id]
            if graph["seed_paper_id"] != row["seed_paper_id"]:
                raise ValueError("QA/graph seed mismatch")
            nodes = set(graph["nodes"])
            full_components.add(index, nodes)
            memberships.update(nodes)
            node_counts.append(len(nodes))
            seed, gold = row["seed_paper_id"], row["gold_paper_ids"][0]
            reachable = any(bridge in graph["edges"].get(seed, [])
                            and gold in graph["edges"].get(bridge, [])
                            for bridge in row["bridge_paper_ids"])
            path_reachable += int(reachable)
            if not reachable:
                structural_missing.append(sample_id)
    if seen != set(by_id):
        raise ValueError("missing graph for fixed task")
    path_sizes = path_components.sizes()
    full_sizes = full_components.sizes()
    return {"schema": "gac-agenthop-source-feasibility-v1",
        "source": {"code_repository": "https://github.com/JohnnyNLP/agenthop",
            "code_revision": CODE_REVISION,
            "dataset_repository": "https://huggingface.co/datasets/nlpai-lab/agenthop",
            "dataset_revision": DATA_REVISION,
            "sha256": {"qa/full.jsonl": QA_SHA256, "graphs/full.jsonl": GRAPHS_SHA256,
                "paper_pool/papers.jsonl": PAPERS_SHA256,
                "data_loader.py": LOADER_SHA256,
                "testbed/tools.py": TOOLS_SHA256, "testbed/harness.py": HARNESS_SHA256}},
        "source_script_sha256": digest(Path(__file__)),
        "provider_calls": 0, "agent_trajectories_observed": 0,
        "gac_candidates": 0, "calibration_groups": 0, "test_groups_scored": 0,
        "qa_rows": len(rows), "paper_pool_rows_with_sections": len(papers_with_sections),
        "subtypes": dict(sorted(subtypes.items())),
        "selected": {"name": "single-target/depth-2", "tasks": len(selected),
            "unique_seed_papers": len({row["seed_paper_id"] for row in selected}),
            "paper_content_coverage": content_coverage,
            "source_graphs_present": len(seen),
            "seed_bridge_gold_path_reachable": path_reachable,
            "path_unreachable_task_ids": sorted(structural_missing),
            "path_overlap_components": len(path_sizes),
            "path_overlap_largest_component_sizes": path_sizes[:20],
            "path_overlap_singletons": path_sizes.count(1),
            "full_graph_components": len(full_sizes),
            "full_graph_largest_component_sizes": full_sizes[:20],
            "full_graph_paper_memberships": sum(node_counts),
            "full_graph_unique_papers": len(memberships),
            "full_graph_reused_papers": sum(count > 1 for count in memberships.values()),
            "full_graph_max_paper_reuse": max(memberships.values())},
        "decision": "GO_FOR_BOUNDED_DEVELOPMENT_PILOT_ONLY_NO_CONFIRMATORY_GAC_CLAIM",
        "required_next_gate": "Collect train-only baseline trajectories and show a recurring multi-step prefix whose dynamic arguments are uniquely grounded in entry state or prior tool outputs, without gold paper IDs or answer metadata; compare exact handwritten and simpler-compiler implementations before paid matched evaluation.",
        "limitations": [
            "One full-neighborhood connected component prevents claiming source-disjoint groups.",
            "Path-overlap components are a sensitivity unit, not proven independent samples.",
            "A two-read fixed seed prefetch alone does not establish state-dependent compilation benefit.",
            "The released code has a trajectory writer, but no observed agent trajectories were supplied to this preflight.",
            "The two path-unreachable cases remain in any fixed denominator; they are not outcome-selected exclusions."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qa", type=Path, required=True)
    parser.add_argument("--graphs", type=Path, required=True)
    parser.add_argument("--papers", type=Path, required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    args = parser.parse_args()
    report = build(args.qa, args.graphs, args.papers, args.code_root)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"decision": report["decision"], "selected": report["selected"]}, sort_keys=True))


if __name__ == "__main__":
    main()
