"""Conservative parsers for the external benchmark matrix.

These adapters read upstream artifacts without importing benchmark packages.  That keeps
their mutually incompatible dependency stacks out of agent-compaction.  The effect labels
are screening annotations based on explicit HTTP methods and a small closed name policy;
they are never accepted as a signed runtime :class:`EffectCatalog`.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from agent_compaction.benchmarking.external import (
    EvidenceSubstrate,
    ReferenceAction,
    ReferenceTask,
)
from agent_compaction.schema.effects import EffectClass

__all__ = [
    "load_agentbench",
    "load_api_bank",
    "load_bfcl",
    "load_browsecomp",
    "load_gaia",
    "load_swebench",
    "load_tau2",
    "load_toolbench",
    "load_toolsandbox",
    "screening_effect",
]


_READ_PREFIXES = (
    "calculate",
    "can_",
    "cat",
    "check",
    "diff",
    "dictionary",
    "find",
    "get",
    "grep",
    "intersection",
    "list",
    "lookup",
    "query",
    "read",
    "retrieve",
    "search",
    "sort",
    "translate",
    "view",
    "weather",
    "wiki",
)
_WRITE_PREFIXES = (
    "add",
    "apply",
    "book",
    "call_discoverable",
    "cancel",
    "cd",
    "create",
    "delete",
    "enable",
    "exchange",
    "give_discoverable",
    "log_",
    "mkdir",
    "modify",
    "move",
    "mv",
    "open_",
    "play",
    "post",
    "record",
    "register",
    "remove",
    "rename",
    "send",
    "set",
    "submit",
    "timed",
    "toggle",
    "turn_",
    "unlock",
    "update",
    "write",
)


def screening_effect(name: str, *, method: str | None = None) -> EffectClass:
    """Classify only obvious benchmark actions; ambiguity remains ``UNKNOWN``."""

    normalized_method = (method or "").upper()
    if normalized_method in {"GET", "HEAD", "OPTIONS"}:
        return EffectClass.READ_EXTERNAL
    if normalized_method in {"POST", "PUT", "PATCH", "DELETE"}:
        return EffectClass.WRITE_REVERSIBLE
    leaf = re.sub(r"[^a-z0-9_]+", "_", name.rsplit(".", 1)[-1].lower()).strip("_")
    if leaf in {"calculator", "current_time", "get_today"}:
        return EffectClass.PURE
    if leaf.startswith(_READ_PREFIXES):
        return EffectClass.READ_LOCAL
    if leaf.startswith(_WRITE_PREFIXES):
        return EffectClass.WRITE_REVERSIBLE
    return EffectClass.UNKNOWN


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _safe_literal(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        try:
            return ast.unparse(node)
        except Exception:
            return "<dynamic>"


def _parse_call(expression: str) -> tuple[str, dict[str, Any]]:
    raw = expression.strip()
    try:
        parsed = ast.parse(raw, mode="eval").body
    except SyntaxError:
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_.-]*)\((.*)\)$", raw)
        if not match:
            return raw, {}
        name, payload = match.groups()
        values = [item.strip() for item in payload.split(",") if item.strip()]
        return name, {f"arg{index}": item for index, item in enumerate(values)}
    if not isinstance(parsed, ast.Call):
        return raw, {}
    arguments = {f"arg{index}": _safe_literal(item) for index, item in enumerate(parsed.args)}
    arguments.update(
        {keyword.arg or "kwargs": _safe_literal(keyword.value) for keyword in parsed.keywords}
    )
    return _call_name(parsed.func), arguments


def _prompt_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def load_bfcl(root: str | Path, revision: str) -> tuple[ReferenceTask, ...]:
    base = Path(root) / "berkeley-function-call-leaderboard" / "bfcl_eval" / "data"
    questions = _read_jsonl(base / "BFCL_v4_multi_turn_base.json")
    answers = {
        row["id"]: row["ground_truth"]
        for row in _read_jsonl(base / "possible_answer" / "BFCL_v4_multi_turn_base.json")
    }
    tasks: list[ReferenceTask] = []
    for row in questions:
        actions: list[ReferenceAction] = []
        for turn, calls in enumerate(answers.get(row["id"], [])):
            for raw_call in calls:
                name, arguments = _parse_call(raw_call)
                actions.append(
                    ReferenceAction(
                        name=name,
                        arguments=arguments,
                        effect=screening_effect(name),
                        turn=turn,
                        metadata={"raw_reference_call": raw_call},
                    )
                )
        user_text = [
            str(message.get("content", ""))
            for turn in row.get("question", [])
            for message in turn
            if isinstance(message, Mapping) and message.get("role") == "user"
        ]
        tasks.append(
            ReferenceTask(
                benchmark="bfcl_v4_multi_turn_base",
                task_id=str(row["id"]),
                group_id=f"bfcl:{row['id']}",
                source_revision=revision,
                substrate=EvidenceSubstrate.EXECUTABLE_PUBLIC_BENCHMARK,
                actions=tuple(actions),
                prompt="\n".join(user_text),
                metadata={
                    "involved_classes": row.get("involved_classes", []),
                    "excluded_function": row.get("excluded_function", []),
                    "reference_calls_have_results": False,
                    "official_category": "multi_turn_base",
                },
            )
        )
    return tuple(tasks)


def _scenario_extensions(tree: ast.AST) -> Iterable[ast.Call]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _call_name(node.func).endswith("ScenarioExtension"):
            yield node


def _keyword(call: ast.Call, name: str) -> ast.AST | None:
    return next((item.value for item in call.keywords if item.arg == name), None)


def _dict_string_value(node: ast.Dict, key_name: str) -> str | None:
    for key, value in zip(node.keys, node.values):
        if isinstance(key, ast.Constant) and key.value == key_name:
            candidate = _safe_literal(value)
            return candidate if isinstance(candidate, str) else None
    return None


def load_toolsandbox(root: str | Path, revision: str) -> tuple[ReferenceTask, ...]:
    scenario_root = Path(root) / "tool_sandbox" / "scenarios"
    tasks: list[ReferenceTask] = []
    for source in sorted(scenario_root.glob("*_scenarios.py")):
        if source.name in {"base_scenarios.py", "user_simulator_few_shot_examples.py"}:
            continue
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for call in _scenario_extensions(tree):
            raw_name = _safe_literal(_keyword(call, "name") or ast.Constant(""))
            if not isinstance(raw_name, str) or not raw_name:
                continue
            allow_node = _keyword(call, "tool_allow_list")
            allow_list = _safe_literal(allow_node) if allow_node is not None else []
            if not isinstance(allow_list, list):
                allow_list = []
            traced: list[tuple[int, str]] = []
            for nested in ast.walk(call):
                if not isinstance(nested, ast.Dict):
                    continue
                tool_name = _dict_string_value(nested, "tool_name")
                if tool_name:
                    traced.append((getattr(nested, "lineno", 0), tool_name))
            action_names = [name for _, name in sorted(set(traced))] or [
                str(name) for name in allow_list if isinstance(name, str)
            ]
            evidence = "milestone_tool_trace" if traced else "tool_allow_list_only"
            tasks.append(
                ReferenceTask(
                    benchmark="toolsandbox_base_scenarios",
                    task_id=f"{source.stem}:{raw_name}",
                    group_id=f"toolsandbox:{source.stem}:{raw_name}",
                    source_revision=revision,
                    substrate=EvidenceSubstrate.PUBLIC_SIMULATION,
                    actions=tuple(
                        ReferenceAction(
                            name=name,
                            effect=screening_effect(name),
                            metadata={"action_evidence": evidence},
                        )
                        for name in action_names
                    ),
                    metadata={
                        "source_file": source.name,
                        "action_evidence": evidence,
                        "tool_allow_list": allow_list,
                        "runtime_variants_per_lineage": 8,
                        "variants_are_not_independent_groups": True,
                    },
                )
            )
    return tuple(tasks)


def _tau_rows(root: Path) -> Iterable[tuple[str, dict[str, Any]]]:
    domain_root = root / "data" / "tau2" / "domains"
    for domain in ("airline", "retail", "telecom"):
        payload = json.loads((domain_root / domain / "tasks.json").read_text(encoding="utf-8"))
        for row in payload:
            yield domain, row
    for source in sorted((domain_root / "banking_knowledge" / "tasks").glob("task_*.json")):
        yield "banking_knowledge", json.loads(source.read_text(encoding="utf-8"))


def load_tau2(root: str | Path, revision: str) -> tuple[ReferenceTask, ...]:
    tasks: list[ReferenceTask] = []
    for domain, row in _tau_rows(Path(root)):
        criteria = row.get("evaluation_criteria") or {}
        actions = []
        for turn, action in enumerate(criteria.get("actions") or []):
            name = str(action.get("name") or "")
            if not name:
                continue
            actions.append(
                ReferenceAction(
                    name=name,
                    arguments=action.get("arguments") or {},
                    effect=screening_effect(name),
                    requestor=str(action.get("requestor") or "assistant"),
                    turn=turn,
                    metadata={"action_id": action.get("action_id")},
                )
            )
        scenario = row.get("user_scenario") or {}
        task_id = f"{domain}:{row['id']}"
        tasks.append(
            ReferenceTask(
                benchmark="tau2",
                task_id=task_id,
                group_id=f"tau2:{task_id}",
                source_revision=revision,
                substrate=EvidenceSubstrate.PUBLIC_SIMULATION,
                actions=tuple(actions),
                prompt=_prompt_text(scenario.get("instructions")),
                metadata={
                    "domain": domain,
                    "reward_basis": criteria.get("reward_basis") or [],
                    "has_nl_assertions": bool(criteria.get("nl_assertions")),
                    "has_env_assertions": bool(criteria.get("env_assertions")),
                    "has_initialization_actions": bool(
                        (row.get("initial_state") or {}).get("initialization_actions")
                    ),
                    "reference_calls_have_results": False,
                },
            )
        )
    return tuple(tasks)


def load_api_bank(root: str | Path, revision: str) -> tuple[ReferenceTask, ...]:
    source_root = Path(root) / "api-bank" / "lv1-lv2-samples" / "level-1-given-desc"
    tasks: list[ReferenceTask] = []
    for source in sorted(source_root.glob("*.jsonl")):
        rows = _read_jsonl(source)
        actions: list[ReferenceAction] = []
        prompt_parts: list[str] = []
        turn = 0
        for row in rows:
            role = str(row.get("role") or "").lower()
            if role == "user":
                prompt_parts.append(str(row.get("text") or ""))
            if role != "api":
                continue
            result = row.get("result")
            actions.append(
                ReferenceAction(
                    name=str(row.get("api_name")),
                    arguments=row.get("param_dict") or {},
                    output=result,
                    output_observed="result" in row,
                    effect=screening_effect(str(row.get("api_name"))),
                    turn=turn,
                    metadata={
                        "exception": result.get("exception") if isinstance(result, Mapping) else None
                    },
                )
            )
            turn += 1
        if not actions:
            continue
        tasks.append(
            ReferenceTask(
                benchmark="api_bank",
                task_id=source.stem,
                group_id=f"api-bank:{source.stem}",
                source_revision=revision,
                substrate=EvidenceSubstrate.EXECUTABLE_PUBLIC_BENCHMARK,
                actions=tuple(actions),
                prompt="\n".join(prompt_parts),
                metadata={
                    "source_file": source.name,
                    "reference_calls_have_results": True,
                    "synthetic_identity_fields_may_appear_in_prompts": True,
                },
            )
        )
    return tuple(tasks)


def load_toolbench(root: str | Path, revision: str) -> tuple[ReferenceTask, ...]:
    source_root = Path(root) / "data_example" / "instruction"
    tasks: list[ReferenceTask] = []
    for source in (source_root / "G1_query.json", source_root / "G2_query.json", source_root / "G3_query.json"):
        rows = json.loads(source.read_text(encoding="utf-8"))
        for row in rows:
            api_records = {
                (str(item.get("tool_name")), str(item.get("api_name"))): item
                for item in row.get("api_list") or []
            }
            actions = []
            for tool_name, api_name in row.get("relevant APIs") or []:
                record = api_records.get((str(tool_name), str(api_name)), {})
                name = f"{tool_name}.{api_name}"
                actions.append(
                    ReferenceAction(
                        name=name,
                        effect=screening_effect(name, method=record.get("method")),
                        metadata={"http_method": record.get("method")},
                    )
                )
            task_id = f"{source.stem}:{row['query_id']}"
            tasks.append(
                ReferenceTask(
                    benchmark="toolbench_repository_examples",
                    task_id=task_id,
                    group_id=f"toolbench:{task_id}",
                    source_revision=revision,
                    substrate=EvidenceSubstrate.EXECUTABLE_PUBLIC_BENCHMARK,
                    actions=tuple(actions),
                    prompt=str(row.get("query") or ""),
                    metadata={
                        "partial_fixture_only": True,
                        "full_reproduction_data_not_in_git": True,
                        "official_test_group": source.stem,
                    },
                )
            )
    return tuple(tasks)


def load_agentbench(root: str | Path, revision: str) -> tuple[ReferenceTask, ...]:
    base = Path(root) / "data"
    tasks: list[ReferenceTask] = []
    for split in ("dev", "std"):
        source = base / "knowledgegraph" / f"{split}.json"
        if not source.exists():
            continue
        for row in json.loads(source.read_text(encoding="utf-8")):
            actions = []
            for turn, raw_call in enumerate(row.get("actions") or []):
                name, arguments = _parse_call(str(raw_call))
                actions.append(
                    ReferenceAction(
                        name=name,
                        arguments=arguments,
                        effect=screening_effect(name),
                        turn=turn,
                        metadata={"raw_reference_call": raw_call},
                    )
                )
            task_id = f"kg:{split}:{row.get('qid')}"
            tasks.append(
                ReferenceTask(
                    benchmark="agentbench",
                    task_id=task_id,
                    group_id=f"agentbench:{task_id}",
                    source_revision=revision,
                    substrate=EvidenceSubstrate.PUBLIC_SIMULATION,
                    actions=tuple(actions),
                    prompt=str(row.get("question") or ""),
                    metadata={"domain": "knowledgegraph", "split": split},
                )
            )
    for split in ("dev", "standard"):
        source = base / "dbbench" / f"{split}.jsonl"
        if not source.exists():
            continue
        for index, row in enumerate(_read_jsonl(source)):
            task_id = f"db:{split}:{index}"
            tasks.append(
                ReferenceTask(
                    benchmark="agentbench",
                    task_id=task_id,
                    group_id=f"agentbench:{task_id}",
                    source_revision=revision,
                    substrate=EvidenceSubstrate.PUBLIC_SIMULATION,
                    prompt=str(row.get("description") or ""),
                    metadata={"domain": "dbbench", "split": split, "task_only": True},
                )
            )
    os_source = base / "os_interaction" / "data" / "dev.json"
    if os_source.exists():
        for index, row in enumerate(json.loads(os_source.read_text(encoding="utf-8"))):
            task_id = f"os:dev:{index}"
            tasks.append(
                ReferenceTask(
                    benchmark="agentbench",
                    task_id=task_id,
                    group_id=f"agentbench:{task_id}",
                    source_revision=revision,
                    substrate=EvidenceSubstrate.PUBLIC_SIMULATION,
                    prompt=str(row.get("description") or ""),
                    metadata={"domain": "os_interaction", "split": "dev", "task_only": True},
                )
            )
    return tuple(tasks)


def _plain_json(value: Any) -> Any:
    if value is None:
        return None
    try:
        if bool(math.isnan(value)):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def load_gaia(metadata_parquet: str | Path, revision: str) -> tuple[ReferenceTask, ...]:
    try:
        import pandas as pd
    except Exception as exc:  # pragma: no cover - publication extra
        raise RuntimeError("GAIA metadata loading requires pandas and pyarrow") from exc
    frame = pd.read_parquet(metadata_parquet)
    tasks: list[ReferenceTask] = []
    for index, row in frame.iterrows():
        record = {str(key): _plain_json(value) for key, value in row.to_dict().items()}
        task_id = str(
            record.get("task_id")
            or record.get("Task ID")
            or record.get("id")
            or index
        )
        question = str(record.get("Question") or record.get("question") or "")
        file_name = record.get("file_name") or record.get("File Name")
        tasks.append(
            ReferenceTask(
                benchmark="gaia_validation",
                task_id=task_id,
                group_id=f"gaia:{task_id}",
                source_revision=revision,
                substrate=EvidenceSubstrate.LIVE_WEB,
                prompt=question,
                metadata={
                    "level": record.get("Level") or record.get("level"),
                    "has_attached_file": bool(file_name),
                    "attached_file_suffix": Path(str(file_name)).suffix.lower() if file_name else "",
                    "task_only": True,
                    "gold_not_retained_in_analysis": True,
                },
            )
        )
    return tuple(tasks)


def load_swebench(metadata_parquet: str | Path, revision: str) -> tuple[ReferenceTask, ...]:
    try:
        import pandas as pd
    except Exception as exc:  # pragma: no cover - publication extra
        raise RuntimeError("SWE-bench metadata loading requires pandas and pyarrow") from exc
    frame = pd.read_parquet(metadata_parquet)
    tasks: list[ReferenceTask] = []
    for index, row in frame.iterrows():
        record = {str(key): _plain_json(value) for key, value in row.to_dict().items()}
        task_id = str(record.get("instance_id") or index)
        tasks.append(
            ReferenceTask(
                benchmark="swe_bench_verified",
                task_id=task_id,
                group_id=f"swe-bench:{task_id}",
                source_revision=revision,
                substrate=EvidenceSubstrate.REAL_WORLD_CONTAINER,
                prompt=str(record.get("problem_statement") or ""),
                metadata={
                    "repository": record.get("repo"),
                    "base_commit": record.get("base_commit"),
                    "task_only": True,
                    "gold_patch_not_retained_in_analysis": True,
                },
            )
        )
    return tuple(tasks)


def load_browsecomp(encrypted_csv: str | Path, revision: str) -> tuple[ReferenceTask, ...]:
    tasks: list[ReferenceTask] = []
    with Path(encrypted_csv).open(newline="", encoding="utf-8") as handle:
        for index, row in enumerate(csv.DictReader(handle)):
            encrypted_problem = str(row.get("problem") or "")
            task_hash = hashlib.sha256(encrypted_problem.encode("utf-8")).hexdigest()[:20]
            task_id = f"encrypted:{index}:{task_hash}"
            tasks.append(
                ReferenceTask(
                    benchmark="browsecomp",
                    task_id=task_id,
                    group_id=f"browsecomp:{task_id}",
                    source_revision=revision,
                    substrate=EvidenceSubstrate.LIVE_WEB,
                    metadata={
                        "task_only": True,
                        "encrypted_source": True,
                        "problem_and_answer_not_decrypted_or_retained": True,
                    },
                )
            )
    return tuple(tasks)
