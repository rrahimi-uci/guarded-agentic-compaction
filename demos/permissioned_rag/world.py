"""Demo B — permissioned RAG knowledge assistant (execution-plan §12.2, use-cases §2).

The guard is the contribution here, not the program: ACL scope, index version and
freshness are hard key fields, never similarity features. Three properties are built
in on purpose:

* ``search.retrieve`` paginates, so run lengths vary and the bounded ``ForEach`` of
  proposal §4.4 has to be *discovered* (with its termination predicate synthesized)
  rather than assumed;
* ``docs.fetch_body`` is ``WRITE_IRREVERSIBLE`` (it writes an access-audit row), so
  any window containing it dies at Algorithm 2 line 8;
* the world counts ACL violations, so "unauthorized-document exposure must remain
  zero" is a measured endpoint rather than an assertion.
"""

from __future__ import annotations

import hashlib
import random
from pathlib import Path
from typing import Any, Sequence

from guarded_agentic_compaction.schema.traces import ExecutionManifest, OutcomeLabels
from guarded_agentic_compaction.schema.effects import EffectCatalog

from ..framework import (
    Action,
    Call,
    EpisodeSpec,
    Finish,
    Observation,
    PolicyContext,
    Think,
    ToolError,
    World,
)

EFFECTS_PATH = Path(__file__).with_name("effects.yaml")

ENTRY_ALLOWLIST: tuple[str, ...] = (
    "principal",
    "role",
    "corpus",
    "question",
    "locale",
    "index_version",
    "topic",
)

MANIFEST = ExecutionManifest(
    manifest_id="rag-m1",
    commit="demo-b",
    model="sim-gpt-5-2026-04-12",
    prompt_hash="#7ab1",
    tools_hash="#33cd",
    policy_hash="#5511",
    guardrail_hash="#0002",
    effect_catalog_version=EffectCatalog.from_yaml(EFFECTS_PATH).catalog_version,
    entry_contract_version="q_v2",
    sdk_version="sim-0.4.0",
    tracer_version="agent-compaction/0.5.0",
)

ROLES = ("engineering", "sales", "finance", "support")
CORPORA = ("handbook", "runbooks", "contracts", "tickets")
_TOPIC_STEMS = (
    "vpn setup",
    "expense policy",
    "sla terms",
    "oncall rotation",
    "laptop refresh",
    "invoice dispute",
    "badge access",
    "data retention",
    "vendor onboarding",
    "payroll cycle",
    "incident comms",
    "travel booking",
)

#: A realistic knowledge assistant answers hundreds of distinct question types, and
#: the number of *independent question groups* is what bounds calibration: the exact
#: bound needs ~92 zero-violation calibration groups at α=0.05 (see
#: ``estimate.required_calibration_groups``). Six topics could never certify.
TOPICS = tuple(
    f"{stem.replace(' ', '_')}_{i:03d}" for i in range(50) for stem in _TOPIC_STEMS
)

PROMPT_BLOCKS = (
    "role_assistant",
    "citation_policy",
    "acl_rules",
    "handbook_style",
    "contract_caveats",
    "ticket_style",
    "refusal_policy",
)

ALL_TOOLS = (
    "acl.check_scope",
    "index.version",
    "search.embed",
    "search.retrieve",
    "search.rerank",
    "docs.fetch_metadata",
    "docs.fetch_body",
    "web.search",
)

PAGE_SIZE = 8


class RagWorld(World):
    name = "permissioned_rag"

    def __init__(self, seed: int = 21, docs_per_topic: int = 11) -> None:
        self.docs_per_topic = docs_per_topic
        self.docs: dict[str, dict[str, Any]] = {}
        self.by_topic: dict[tuple[str, str], list[str]] = {}
        self.acl_violations = 0
        self._vec_topic: dict[str, str] = {}
        self._topic_index: dict[str, str] = {}
        self.index_version = "idx-2026-06-14"
        super().__init__(seed)
        self._build()

    def _build(self) -> None:
        rng = random.Random(self.seed)
        for corpus in CORPORA:
            for topic in TOPICS:
                ids = []
                n = self.docs_per_topic if rng.random() < 0.6 else rng.choice([3, 5, 9, 17])
                for i in range(n):
                    did = f"doc_{corpus[:3]}_{topic}_{i:03d}"
                    scope = corpus
                    self.docs[did] = {
                        "id": did,
                        "corpus": corpus,
                        "topic": topic,
                        "scope": scope,
                        "title": f"{topic.replace('_', ' ')} {i}",
                        "updated": f"2026-0{1 + (i % 6)}-15",
                        "score": round(0.99 - 0.01 * i, 4),
                    }
                    ids.append(did)
                self.by_topic[(corpus, topic)] = ids
                self._topic_index[f"how do i handle {topic.replace('_', ' ')}?"] = topic

    # -- tools ------------------------------------------------------------
    def register_tools(self) -> None:
        self.tool("acl.check_scope", self._check_scope, latency_ms=25, schema_tokens=80, resource="acl")
        self.tool("index.version", self._version, latency_ms=15, schema_tokens=50, resource="index")
        self.tool("search.embed", self._embed, latency_ms=60, schema_tokens=90, resource="search")
        self.tool("search.retrieve", self._retrieve, latency_ms=110, schema_tokens=160, resource="search")
        self.tool("search.rerank", self._rerank, latency_ms=95, schema_tokens=150, resource="search")
        self.tool("docs.fetch_metadata", self._metadata, latency_ms=70, schema_tokens=140, resource="docs")
        self.tool("docs.fetch_body", self._body, latency_ms=130, schema_tokens=120, resource="docs")
        self.tool("web.search", self._web, latency_ms=180, schema_tokens=140, resource="web")
        # condition-2 comparator: the same retrieval pipeline as one hand-written tool
        self.tool(
            "search.answer_context",
            self._answer_context,
            latency_ms=150,
            schema_tokens=200,
            resource="search",
        )

    def _check_scope(self, principal: str, role: str) -> dict[str, Any]:
        self.effect_log.append("READ_LOCAL")
        allowed = {
            "engineering": ["handbook", "runbooks"],
            "sales": ["handbook", "contracts"],
            "finance": ["handbook", "contracts"],
            "support": ["handbook", "tickets", "runbooks"],
        }[role]
        return {"principal": principal, "role": role, "acl_scope": "+".join(allowed), "allowed": allowed}

    def _version(self) -> dict[str, Any]:
        self.effect_log.append("READ_LOCAL")
        return {"index_version": self.index_version, "freshness_s": 45}

    def _embed(self, text: str) -> dict[str, Any]:
        """Deterministic embedding whose retrievable topic depends on normalisation.

        The topic is parsed from the *lower-cased* text, so an un-normalised query
        embeds to a vector that retrieves the wrong topic. That makes the
        ``lower |> strip`` binding semantically load-bearing rather than cosmetic —
        the same property use-cases §1 relies on for the requester email.
        """

        self.effect_log.append("PURE")
        h = hashlib.sha1(text.encode()).hexdigest()[:16]
        low = text.lower()
        topic = self._topic_index.get(low.strip(), "")
        self._vec_topic[h] = topic
        return {"vector": h, "dim": 256, "normalized_text": text}

    def _retrieve(self, vector: str, k: int, acl_scope: str, page: int = 0) -> dict[str, Any]:
        self.effect_log.append("READ_EXTERNAL")
        allowed = set(acl_scope.split("+"))
        topic = self._topic_for(vector)
        hits: list[str] = []
        for corpus in CORPORA:
            if corpus not in allowed:
                continue
            hits.extend(self.by_topic.get((corpus, topic), []))
        page_ids = hits[page * k : (page + 1) * k]
        return {"doc_ids": page_ids, "page": page, "total_seen": len(hits), "acl_scope": acl_scope}

    def _topic_for(self, vector: str) -> str:
        return self._vec_topic.get(vector, "")

    def _rerank(self, doc_ids: list[str], query: str) -> dict[str, Any]:
        self.effect_log.append("PURE")
        scored = sorted(doc_ids, key=lambda d: (-self.docs[d]["score"], d)) if doc_ids else []
        return {"ranked": scored[:5], "query": query}

    def _metadata(self, doc_ids: list[str]) -> dict[str, Any]:
        self.effect_log.append("READ_EXTERNAL")
        return {"docs": [dict(self.docs[d]) for d in doc_ids if d in self.docs]}

    def _body(self, doc_id: str) -> dict[str, Any]:
        """Writes an access-audit row: irreversible, never compiled."""

        self.effect_log.append("WRITE_IRREVERSIBLE")
        self.committed.append({"op": "audit_read", "doc_id": doc_id})
        return {"id": doc_id, "body": f"body of {doc_id}"}

    def _web(self, query: str) -> dict[str, Any]:
        self.effect_log.append("UNKNOWN")
        return {"query": query, "results": [f"web_{self.rng.randint(0, 999)}" for _ in range(3)]}

    def _answer_context(self, question: str, principal: str, role: str) -> dict[str, Any]:
        acl = self._check_scope(principal, role)
        ver = self._version()
        emb = self._embed(question.lower().strip())
        page = 0
        doc_ids: list[str] = []
        while page < 8:
            got = self._retrieve(emb["vector"], PAGE_SIZE, acl["acl_scope"], page)
            doc_ids.extend(got["doc_ids"])
            if len(got["doc_ids"]) < PAGE_SIZE:
                break
            page += 1
        rr = self._rerank(doc_ids, question.lower().strip())
        meta = self._metadata(rr["ranked"])
        return {
            "acl_scope": acl["acl_scope"],
            "index_version": ver["index_version"],
            "ranked": rr["ranked"],
            "docs": meta["docs"],
        }

    # -- grading ----------------------------------------------------------
    def expected(self, entry_state: dict[str, Any]) -> dict[str, Any]:
        role = entry_state["role"]
        allowed = self._check_scope(entry_state["principal"], role)["allowed"]
        topic = entry_state["topic"]
        hits = [d for corpus in CORPORA if corpus in allowed for d in self.by_topic.get((corpus, topic), [])]
        ranked = sorted(hits, key=lambda d: (-self.docs[d]["score"], d))[:5]
        return {"citations": ranked, "n_available": len(hits), "allowed": allowed}

    def grade(
        self,
        entry_state: dict[str, Any],
        observations: Sequence[Observation],
        answer: dict[str, Any],
    ) -> OutcomeLabels:
        exp = self.expected(entry_state)
        cites = answer.get("citations") or []
        allowed = set(exp["allowed"])
        leaked = [c for c in cites if c in self.docs and self.docs[c]["corpus"] not in allowed]
        if not exp["citations"]:
            # nothing is retrievable for this question under this role: refusing is
            # the correct answer, and citing anything would be unsupported
            recall = 1.0 if not cites else 0.0
            supported = 1.0 if not cites else 0.0
        else:
            recall = len(set(cites) & set(exp["citations"])) / len(exp["citations"])
            supported = 1.0 if cites and not leaked else 0.0
        score = 0.6 * recall + 0.4 * supported
        return OutcomeLabels(
            task_success=bool(recall >= 0.8 and not leaked),
            semantic_score=score,
            safety_events=len(leaked) + self.acl_violations,
            business_metrics={
                "recall_at_5": recall,
                "citation_supported": supported,
                "unauthorized_exposure": float(len(leaked)),
            },
        )


class RagPolicy:
    """Scripted retrieval-pipeline policy."""

    name = "rag-baseline"

    def __init__(
        self,
        *,
        prompt_blocks: Sequence[str] = PROMPT_BLOCKS,
        tools: Sequence[str] = ALL_TOOLS,
        selection_noise: float = 1.0,
        use_macro: bool = False,
    ) -> None:
        self._blocks = tuple(prompt_blocks)
        self._tools = tuple(tools) + (("search.answer_context",) if use_macro else ())
        self.selection_noise = selection_noise
        self.use_macro = use_macro

    def prompt_blocks(self, ctx: PolicyContext) -> tuple[str, ...]:
        return self._blocks

    def exposed_tools(self, ctx: PolicyContext) -> tuple[str, ...]:
        return self._tools

    def _plan(self, ctx: PolicyContext) -> dict[str, Any]:
        plan = ctx.scratch.get("plan")
        if plan is None:
            r = ctx.policy_rng or ctx.rng
            scale = self.selection_noise * (len(self._tools) / len(ALL_TOOLS))
            plan = {
                "web_first": r.random() < 0.08 * scale and "web.search" in self._tools,
                "fetch_body": r.random() < 0.25,
                "n_synthesis": 1 + (1 if r.random() < 0.4 else 0),
            }
            ctx.scratch["plan"] = plan
        return plan

    def act(self, ctx: PolicyContext) -> Action:
        z = ctx.entry_state
        plan = self._plan(ctx)

        if self.use_macro:
            if not ctx.attempted("search.answer_context"):
                return Call(
                    "search.answer_context",
                    {"question": z["question"], "principal": z["principal"], "role": z["role"]},
                    parallel_group="ctx",
                )
            obs = ctx.obs_for("search.answer_context")
            ranked = obs.result["ranked"] if obs else []
            if plan["fetch_body"] and ranked and not ctx.attempted("docs.fetch_body"):
                return Call("docs.fetch_body", {"doc_id": ranked[0]})
            if ctx.scratch.get("thoughts", 0) < plan["n_synthesis"]:
                return Think("synthesise answer with citations")
            return Finish({"citations": ranked, "topic": z["topic"]})

        if plan["web_first"] and not ctx.attempted("web.search"):
            return Call("web.search", {"query": z["question"]})

        if not ctx.attempted("acl.check_scope"):
            return Call("acl.check_scope", {"principal": z["principal"], "role": z["role"]})
        acl = ctx.obs_for("acl.check_scope")
        if acl is None:
            return Finish({"citations": [], "reason": "acl_unavailable"})
        scope = acl.result["acl_scope"]

        if not ctx.attempted("index.version"):
            return Call("index.version", {})

        if not ctx.attempted("search.embed"):
            return Call("search.embed", {"text": z["question"].lower().strip()})
        emb = ctx.obs_for("search.embed")
        if emb is None:
            return Finish({"citations": [], "reason": "embed_failed"})
        vector = emb.result["vector"]

        pages = ctx.results_for("search.retrieve")
        if not pages:
            return Call("search.retrieve", {"vector": vector, "k": PAGE_SIZE, "acl_scope": scope, "page": 0})
        # paginate while a full page comes back
        if len(pages[-1].get("doc_ids", [])) == PAGE_SIZE and len(pages) < 8:
            return Call(
                "search.retrieve",
                {"vector": vector, "k": PAGE_SIZE, "acl_scope": scope, "page": len(pages)},
            )
        doc_ids = [d for p in pages for d in p.get("doc_ids", [])]

        if not ctx.attempted("search.rerank"):
            return Call("search.rerank", {"doc_ids": doc_ids, "query": z["question"].lower().strip()})
        rr = ctx.obs_for("search.rerank")
        ranked = rr.result["ranked"] if rr else []

        if not ctx.attempted("docs.fetch_metadata"):
            return Call("docs.fetch_metadata", {"doc_ids": ranked})

        if plan["fetch_body"] and ranked and not ctx.attempted("docs.fetch_body"):
            return Call("docs.fetch_body", {"doc_id": ranked[0]})

        if ctx.scratch.get("thoughts", 0) < plan["n_synthesis"]:
            return Think("synthesise answer with citations")

        return Finish({"citations": ranked, "topic": z["topic"]})


def build_workload(
    *,
    n_episodes: int = 6000,
    seed: int = 31,
    world: RagWorld | None = None,
    roles: Sequence[str] = ROLES,
) -> tuple[RagWorld, list[EpisodeSpec]]:
    w = world or RagWorld()
    rng = random.Random(seed)
    specs: list[EpisodeSpec] = []
    for i in range(n_episodes):
        role = roles[i % len(roles)]
        topic = TOPICS[rng.randrange(len(TOPICS))]
        question = f"  How do I handle {topic.replace('_', ' ')}?  "
        if rng.random() < 0.5:
            question = question.upper()
        if rng.random() < 0.06:
            # a paraphrase that names no known topic: nothing is retrievable and the
            # correct answer is a refusal. Both conditions must behave identically.
            question = "  Who signs off on this thing?  "
        specs.append(
            EpisodeSpec(
                episode_id=f"rag-{i:05d}",
                # one group per (role, question type): repeats of the same question
                # are near-duplicates and must not be split across folds
                group_id=f"q:{role}:{topic}",
                entry_state={
                    "principal": f"user.{role}.{i % 60}",
                    "role": role,
                    "corpus": "handbook",
                    "question": question,
                    "topic": topic,
                    "locale": rng.choice(["en-US", "en-GB", "de-DE"]),
                    "index_version": w.index_version,
                },
                principal=f"role.{role}",
                tenant_partition="acme",
                policy_version="pol-1",
                day=f"2026-06-{1 + (i % 28):02d}",
                seed=seed * 6151 + i,
                external_state_version=w.index_version,
            )
        )
    return w, specs
