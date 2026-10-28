"""Capture adapters for released agent trajectories (the prefix census).

These adapters normalize three public corpora of *executed* multi-step tool-using agent
trajectories into the compiler's :class:`Episode` IR so that the paper's own stages
(provenance, Algorithm 2 window mining) can be run over them provider-free:

* ``openhands``  -- ``nebius/SWE-rebench-openhands-trajectories`` (OpenHands v0.54.0,
  CodeAct scaffold with native function calling, Qwen3-Coder-480B);
* ``sweagent``   -- ``nebius/SWE-agent-trajectories`` (legacy SWE-agent text-action ReAct
  scaffold, fine-tuned Llama-3 action generators);
* ``taubench``   -- ``sierra-research/tau-bench`` ``historical_trajectories`` (function-calling
  ReAct customer-service agents, gpt-4o and claude-3-5-sonnet, airline and retail).

Conventions, chosen to match how the paper treats AppWorld's released baselines:

* **The first model boundary is the first agent turn after the task prompt.**  Normalized
  position 0 is the first tool call the agent issues.  A text-only turn (no tool call) is a
  model boundary with no call.
* **Entry state** is the structured task record the scaffold's first prompt is filled from
  (instance id, repository, problem statement, workspace path; for tau-bench the user's
  opening utterance).  It is seeded as pseudo-producer 0, exactly as in Algorithm 1.
* **A new user utterance after the first boundary is a region barrier.**  It is recorded as a
  ``HANDOFF`` event: a compiled prefix dispatched at entry cannot consume input that did not
  exist at entry.  Tool observations are not user utterances.
* **Tool identity is closed.**  Editor sub-commands are qualified (``str_replace_editor.view``)
  so a read and a write of the same tool are different catalog entries.  A raw shell command
  resolves to ``shell.<utility>`` only when it is one simple invocation of a closed read-only
  utility set with no shell metacharacters; every other command is the opaque ``shell.exec``.
  The signed catalogs declare the whole ``shell.*`` namespace ``UNKNOWN`` (never a read); the
  census's sensitivity arm flips the allowlisted utilities and nothing else.
* **Opening-only ingestion.**  Only the first ``max_calls`` tool calls of a trajectory are
  retained (``w_max + 1`` by default: the call after the longest admissible window is what
  Algorithm 2's partial-run test inspects), and ingestion may stop one call after the first
  catalog barrier when the caller supplies one.  Neither truncation changes any window that
  starts at the first boundary.

The adapters never execute corpus content.  They parse released records only.
"""

from __future__ import annotations

import hashlib
import json
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator, Sequence

from guarded_agentic_compaction.schema.traces import (
    Episode,
    EventKind,
    EventNode,
    ExecutionManifest,
    OutcomeLabels,
    TraceEnvelope,
)

__all__ = [
    "DEFAULT_MAX_CALLS",
    "MAX_OBSERVATION_CHARS",
    "Call",
    "Turn",
    "TrajectoryRecord",
    "shell_tool_identity",
    "parse_sweagent_action",
    "openhands_tool_identity",
    "build_episode",
    "iter_openhands",
    "iter_sweagent",
    "iter_taubench",
    "census_manifest",
]


#: ``w_max`` (12) plus the one call Algorithm 2's partial-run test looks at after a window.
DEFAULT_MAX_CALLS = 13

#: Observations longer than this are cut.  A cut observation can only *lose* producers, so
#: the census under-counts grounding; it never invents it.
MAX_OBSERVATION_CHARS = 32_000


@dataclass(slots=True)
class Call:
    """One tool call the released log records, with its observed result."""

    tool: str
    arguments: dict[str, Any]
    result: Any
    call_id: str
    status: str = "ok"


@dataclass(slots=True)
class Turn:
    """One model boundary: whether a new user utterance preceded it and what it emitted."""

    calls: list[Call] = field(default_factory=list)
    user_text: str | None = None
    text: str | None = None


@dataclass(slots=True)
class TrajectoryRecord:
    """A released trajectory, scaffold-agnostic, before it becomes an :class:`Episode`."""

    corpus: str
    episode_id: str
    group_id: str
    entry_state: dict[str, Any]
    turns: list[Turn]
    model: str
    attributes: dict[str, Any] = field(default_factory=dict)
    success: bool | None = None


# ---------------------------------------------------------------------------
# closed tool identities
# ---------------------------------------------------------------------------

_SHELL_META = re.compile(r"[|;&<>`$\n\r]")
_SHELL_READ_UTILITIES = frozenset(
    {"ls", "cat", "pwd", "find", "grep", "head", "tail", "wc", "tree", "stat", "file", "which"}
)
_FIND_MUTATING_FLAGS = frozenset(
    {"-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprintf", "-fls", "-fprint0"}
)
_GIT_READ_SUBCOMMANDS = frozenset(
    {"status", "log", "diff", "show", "ls-files", "blame", "grep", "rev-parse"}
)


def shell_tool_identity(command: str) -> str:
    """Map a raw shell command onto the closed ``shell.*`` identity space.

    ``shell.<utility>`` is returned only for a single simple invocation (no pipes,
    redirections, command separators, substitutions or newlines) of a utility in a closed
    read-only set, with ``find`` refused when it carries a mutating or executing flag and
    ``git`` admitted only for read subcommands.  Everything else is ``shell.exec``, including
    ``cd`` (it changes session state), ``echo`` and any interpreter invocation.
    """

    text = (command or "").strip()
    if not text or _SHELL_META.search(text):
        return "shell.exec"
    try:
        argv = shlex.split(text)
    except ValueError:
        return "shell.exec"
    if not argv:
        return "shell.exec"
    head = argv[0]
    if head in _SHELL_READ_UTILITIES:
        if head == "find" and any(item in _FIND_MUTATING_FLAGS for item in argv[1:]):
            return "shell.exec"
        return f"shell.{head}"
    if head == "git" and len(argv) > 1 and argv[1] in _GIT_READ_SUBCOMMANDS:
        return "shell.git_" + argv[1].replace("-", "_")
    return "shell.exec"


_CODE_BLOCK = re.compile(r"```[A-Za-z0-9_+-]*\n(.*?)```", re.S)
_SWEAGENT_READS = {
    "open": ("path", "line_number"),
    "goto": ("line_number",),
    "scroll_down": (),
    "scroll_up": (),
    "search_dir": ("search_term", "dir"),
    "search_file": ("search_term", "file"),
    "find_file": ("file_name", "dir"),
    "create": ("filename",),
    "submit": (),
}
_INT_SLOTS = {"line_number"}


def parse_sweagent_action(text: str) -> tuple[str, dict[str, Any]] | None:
    """Recover ``(tool, arguments)`` from a legacy SWE-agent ``ai`` message.

    The scaffold executes the last fenced code block of the message.  Scaffold commands keep
    their documented argument names; anything else is a raw shell command and resolves
    through :func:`shell_tool_identity`.  ``None`` means the turn carried no action.
    """

    blocks = _CODE_BLOCK.findall(text or "")
    if not blocks:
        return None
    raw = blocks[-1].strip()
    if not raw:
        return None
    first_line = raw.split("\n", 1)[0].strip()
    try:
        argv = shlex.split(first_line)
    except ValueError:
        argv = first_line.split()
    if not argv:
        return None
    head = argv[0]
    if head == "edit":
        return "edit", {"range": argv[1] if len(argv) > 1 else "", "lines": raw.count("\n")}
    if head in _SWEAGENT_READS:
        arguments: dict[str, Any] = {}
        for name, value in zip(_SWEAGENT_READS[head], argv[1:]):
            if name in _INT_SLOTS:
                try:
                    arguments[name] = int(value)
                except ValueError:
                    arguments[name] = value
            else:
                arguments[name] = value
        return head, arguments
    return shell_tool_identity(raw), {"command": raw}


def openhands_tool_identity(name: str, arguments: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Qualify OpenHands tool calls by sub-command and resolve shell commands."""

    if name in {"str_replace_editor", "task_tracker"}:
        command = str(arguments.get("command") or "unknown")
        rest = {key: value for key, value in arguments.items() if key != "command"}
        return f"{name}.{command}", rest
    if name == "execute_bash":
        command = arguments.get("command")
        is_input = str(arguments.get("is_input", "false")).lower() == "true"
        if is_input:
            return "shell.stdin", {"command": command}
        return shell_tool_identity(str(command or "")), {"command": command}
    return name, dict(arguments)


# ---------------------------------------------------------------------------
# Episode construction
# ---------------------------------------------------------------------------


def _clip(value: Any) -> Any:
    if isinstance(value, str) and len(value) > MAX_OBSERVATION_CHARS:
        return value[:MAX_OBSERVATION_CHARS]
    return value


def build_episode(
    record: TrajectoryRecord,
    manifest: ExecutionManifest,
    *,
    tools: Sequence[str],
    max_calls: int = DEFAULT_MAX_CALLS,
    barrier: Callable[[str], bool] | None = None,
) -> Episode:
    """Linearize a record into ``MODEL_REQ, MODEL_RESP, (TOOL_CALL, TOOL_RESULT)*`` events.

    ``barrier`` is an optional predicate on tool identity; when given, ingestion stops after
    the first call it accepts (that call is kept as the sentinel the partial-run test needs).
    """

    events: list[EventNode] = []
    cursor = 0
    ingested = 0
    stopped: str | None = None
    tool_list = sorted(set(tools))

    def add(kind: EventKind, **kwargs: Any) -> None:
        nonlocal cursor
        events.append(EventNode(node_id=f"{record.episode_id}-e{cursor}", kind=kind, index=cursor, **kwargs))
        cursor += 1

    for turn_index, turn in enumerate(record.turns):
        if stopped:
            break
        if turn_index > 0 and turn.user_text is not None:
            add(
                EventKind.HANDOFF,
                actor="user",
                output={"target": "user_turn"},
                attributes={"reason": "new_user_utterance"},
            )
        add(EventKind.MODEL_REQ, input={"tools": tool_list, "turn": turn_index})
        if turn.calls:
            first = turn.calls[0]
            add(EventKind.MODEL_RESP, output={"name": first.tool, "arguments": first.arguments})
        else:
            add(EventKind.MODEL_RESP, output={"text": (turn.text or "")[:2000]})
        for call in turn.calls:
            add(
                EventKind.TOOL_CALL,
                tool=call.tool,
                input=call.arguments,
                call_id=call.call_id,
            )
            add(
                EventKind.TOOL_RESULT,
                tool=call.tool,
                output=_clip(call.result),
                call_id=call.call_id,
                status=call.status,
            )
            ingested += 1
            if barrier is not None and barrier(call.tool):
                stopped = "barrier"
                break
            if ingested >= max_calls:
                stopped = "max_calls"
                break

    total_calls = sum(len(turn.calls) for turn in record.turns)
    envelope = TraceEnvelope(
        trace_id=f"{record.corpus}:{record.episode_id}",
        episode_id=record.episode_id,
        group_id=record.group_id,
        manifest_id=manifest.manifest_id,
        principal=record.model,
        tenant_partition="public",
        policy_version="released-trajectory",
        day="1970-01-01",
        privacy_class="public",
        external_state_version=manifest.commit,
    )
    return Episode(
        envelope=envelope,
        manifest=manifest,
        entry_state=record.entry_state,
        events=events,
        outcome=OutcomeLabels(task_success=record.success),
        attributes={
            **record.attributes,
            "corpus": record.corpus,
            "model": record.model,
            "n_turns_total": len(record.turns),
            "n_calls_total": total_calls,
            "n_calls_ingested": ingested,
            "ingestion_stopped_by": stopped,
        },
    )


def census_manifest(
    corpus: str,
    *,
    revision: str,
    catalog_version: str,
    tools: Sequence[str],
    scaffold: str,
    entry_contract: str,
) -> ExecutionManifest:
    """A manifest for counting, not for compiling: the models in a corpus are pooled."""

    return ExecutionManifest(
        manifest_id=f"prefix-census-{corpus}",
        commit=revision,
        model="pooled-released-models",
        prompt_hash=f"released-{scaffold}-prompt",
        tools_hash=hashlib.sha256("|".join(sorted(set(tools))).encode()).hexdigest()[:16],
        policy_hash="prefix-census-opening-only",
        guardrail_hash="none-trace-analysis-only",
        effect_catalog_version=catalog_version,
        entry_contract_version=entry_contract,
        sdk_version=scaffold,
        tracer_version="prefix-census-adapter-v1",
    )


# ---------------------------------------------------------------------------
# parquet helpers
# ---------------------------------------------------------------------------


def _iter_parquet_rows(path: Path, columns: Sequence[str], batch_size: int = 256) -> Iterator[dict[str, Any]]:
    try:
        import pyarrow.parquet as pq
    except Exception as exc:  # pragma: no cover - publication extra
        raise RuntimeError("the prefix census adapters require pyarrow") from exc
    reader = pq.ParquetFile(path)
    for batch in reader.iter_batches(batch_size=batch_size, columns=list(columns)):
        yield from batch.to_pylist()


def _json_arguments(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except ValueError:
            return {"_unparsed": value}
        return parsed if isinstance(parsed, dict) else {"_value": parsed}
    return {}


def _json_result(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped[:1] in "{[":
            try:
                return json.loads(stripped)
            except ValueError:
                return value
    return value


# ---------------------------------------------------------------------------
# OpenHands (nebius/SWE-rebench-openhands-trajectories)
# ---------------------------------------------------------------------------

_UPLOADED = re.compile(r"<uploaded_files>\s*(.*?)\s*</uploaded_files>", re.S)
_ISSUE = re.compile(r"<issue_description>\s*(.*?)\s*</issue_description>", re.S)

OPENHANDS_TOOLS = (
    "execute_bash", "finish", "str_replace_editor", "task_tracker", "think",
)


def iter_openhands(path: str | Path, *, limit: int | None = None) -> Iterator[TrajectoryRecord]:
    """Yield records from the released OpenHands parquet in file order."""

    columns = ("trajectory_id", "instance_id", "repo", "trajectory", "exit_status", "resolved")
    for ordinal, row in enumerate(_iter_parquet_rows(Path(path), columns)):
        if limit is not None and ordinal >= limit:
            return
        messages = row["trajectory"] or []
        task_text = next((m.get("content") or "" for m in messages if m.get("role") == "user"), "")
        workspace = _UPLOADED.search(task_text)
        issue = _ISSUE.search(task_text)
        entry = {
            "inputs": {
                "instance_id": row["instance_id"],
                "repo": row["repo"],
                "workspace": workspace.group(1) if workspace else None,
                "problem_statement": issue.group(1) if issue else task_text,
            }
        }
        turns: list[Turn] = []
        pending_user: str | None = None
        seen_user = False
        seen_assistant = False
        results: dict[str, tuple[Any, str]] = {}
        open_calls: list[Call] = []
        for message in messages:
            role = message.get("role")
            if role == "user":
                if seen_user and seen_assistant:
                    pending_user = message.get("content") or ""
                seen_user = True
            elif role == "assistant":
                seen_assistant = True
                turn = Turn(user_text=pending_user, text=message.get("content"))
                pending_user = None
                for tool_call in message.get("tool_calls") or []:
                    function = tool_call.get("function") or {}
                    tool, arguments = openhands_tool_identity(
                        str(function.get("name") or "unknown"), _json_arguments(function.get("arguments"))
                    )
                    call = Call(tool=tool, arguments=arguments, result=None, call_id=str(tool_call.get("id") or ""))
                    turn.calls.append(call)
                    open_calls.append(call)
                turns.append(turn)
            elif role == "tool":
                call_id = str(message.get("tool_call_id") or "")
                content = message.get("content")
                target = next((c for c in open_calls if c.call_id == call_id), None)
                if target is None and open_calls:
                    target = open_calls[0]
                if target is not None:
                    target.result = content
                    open_calls.remove(target)
        resolved = row.get("resolved")
        yield TrajectoryRecord(
            corpus="openhands",
            episode_id=str(row["trajectory_id"]),
            group_id=str(row["instance_id"]),
            entry_state=entry,
            turns=turns,
            model="qwen3-coder-480b-a35b-instruct",
            attributes={
                "architecture": "codeact_function_calling",
                "exit_status": row.get("exit_status"),
                "repo": row["repo"],
            },
            success=bool(int(resolved)) if resolved not in (None, "") else None,
        )


# ---------------------------------------------------------------------------
# SWE-agent (nebius/SWE-agent-trajectories)
# ---------------------------------------------------------------------------

SWEAGENT_TOOLS = (
    "create", "edit", "find_file", "goto", "open", "scroll_down", "scroll_up",
    "search_dir", "search_file", "submit",
)
_SWE_ISSUE = re.compile(r"ISSUE:\s*(.*?)\s*(?:\n\s*INSTRUCTIONS:|\Z)", re.S)


def iter_sweagent(root: str | Path, *, limit: int | None = None) -> Iterator[TrajectoryRecord]:
    """Yield records from the released SWE-agent parquet shards in shard, row order."""

    shards = sorted(Path(root).glob("data/train-*.parquet")) or sorted(Path(root).glob("*.parquet"))
    ordinal = 0
    for shard in shards:
        columns = ("instance_id", "model_name", "target", "trajectory", "exit_status")
        for row_index, row in enumerate(_iter_parquet_rows(shard, columns)):
            if limit is not None and ordinal >= limit:
                return
            ordinal += 1
            messages = row["trajectory"] or []
            task_text = next((m.get("text") or "" for m in messages if m.get("role") == "user"), "")
            issue = _SWE_ISSUE.search(task_text)
            instance_id = str(row["instance_id"])
            repo = instance_id.rsplit("-", 1)[0].replace("__", "/", 1)
            entry = {
                "inputs": {
                    "instance_id": instance_id,
                    "repo": repo,
                    "problem_statement": issue.group(1) if issue else task_text,
                }
            }
            turns: list[Turn] = []
            seen_task = False
            awaiting: Call | None = None
            turns_without_action = 0
            for message in messages:
                role = message.get("role")
                text = message.get("text") or ""
                if role == "user":
                    if not seen_task:
                        seen_task = True
                        continue
                    if awaiting is not None:
                        awaiting.result = text
                        awaiting = None
                    continue
                if role != "ai":
                    continue
                parsed = parse_sweagent_action(text)
                if parsed is None:
                    turns_without_action += 1
                    turns.append(Turn(text=text))
                    continue
                tool, arguments = parsed
                call = Call(tool=tool, arguments=arguments, result=None, call_id=f"c{len(turns)}")
                awaiting = call
                turns.append(Turn(calls=[call]))
            yield TrajectoryRecord(
                corpus="sweagent",
                episode_id=f"{shard.stem}:{row_index}:{instance_id}",
                group_id=instance_id,
                entry_state=entry,
                turns=turns,
                model=str(row.get("model_name") or "unknown"),
                attributes={
                    "architecture": "react_text_actions",
                    "exit_status": row.get("exit_status"),
                    "turns_without_action": turns_without_action,
                },
                success=bool(row.get("target")) if row.get("target") is not None else None,
            )


# ---------------------------------------------------------------------------
# tau-bench historical trajectories
# ---------------------------------------------------------------------------

TAUBENCH_TOOLS = (
    "book_reservation", "calculate", "cancel_pending_order", "cancel_reservation",
    "exchange_delivered_order_items", "find_user_id_by_email", "find_user_id_by_name_zip",
    "get_order_details", "get_product_details", "get_reservation_details", "get_user_details",
    "list_all_airports", "list_all_product_types", "modify_pending_order_address",
    "modify_pending_order_items", "modify_pending_order_payment", "modify_user_address",
    "return_delivered_order_items", "search_direct_flight", "search_onestop_flight",
    "send_certificate", "think", "transfer_to_human_agents", "update_reservation_baggages",
    "update_reservation_flights", "update_reservation_passengers",
)
_TAU_FILE = re.compile(r"^(?P<model>.+?)-(?P<domain>airline|retail)\.json$")


def iter_taubench(
    root: str | Path,
    *,
    fold_pre_tool_user_turns: bool = False,
    limit: int | None = None,
) -> Iterator[TrajectoryRecord]:
    """Yield records from tau-bench's ``historical_trajectories/*.json``.

    With ``fold_pre_tool_user_turns`` (the census's labelled diagnostic arm, never the
    primary measure) every user utterance before the first tool-issuing turn is folded into
    the entry state and the opening is measured from that turn; user turns after it remain
    barriers.
    """

    ordinal = 0
    for source in sorted(Path(root).glob("*.json")):
        match = _TAU_FILE.match(source.name)
        if not match:
            continue
        model, domain = match.group("model"), match.group("domain")
        for record in json.loads(source.read_text(encoding="utf-8")):
            if limit is not None and ordinal >= limit:
                return
            ordinal += 1
            messages = record.get("traj") or []
            user_messages = [str(m.get("content") or "").strip() for m in messages if m.get("role") == "user"]
            turns: list[Turn] = []
            pending_user: str | None = None
            first_user_consumed = False
            open_calls: list[Call] = []
            for message in messages:
                role = message.get("role")
                if role == "user":
                    text = str(message.get("content") or "").strip()
                    if not first_user_consumed:
                        first_user_consumed = True
                        continue
                    pending_user = text
                elif role == "assistant":
                    turn = Turn(user_text=pending_user, text=message.get("content"))
                    pending_user = None
                    for tool_call in message.get("tool_calls") or []:
                        function = tool_call.get("function") or {}
                        call = Call(
                            tool=str(function.get("name") or "unknown"),
                            arguments=_json_arguments(function.get("arguments")),
                            result=None,
                            call_id=str(tool_call.get("id") or ""),
                        )
                        turn.calls.append(call)
                        open_calls.append(call)
                    turns.append(turn)
                elif role == "tool":
                    call_id = str(message.get("tool_call_id") or "")
                    target = next((c for c in open_calls if c.call_id == call_id), None)
                    if target is None and open_calls:
                        target = open_calls[0]
                    if target is not None:
                        target.result = _json_result(message.get("content"))
                        open_calls.remove(target)
            entry_inputs: dict[str, Any] = {
                "domain": domain,
                "task_id": record.get("task_id"),
                "user_message": user_messages[0] if user_messages else "",
            }
            folded = 0
            if fold_pre_tool_user_turns:
                first_tool_turn = next((i for i, t in enumerate(turns) if t.calls), None)
                if first_tool_turn is not None:
                    pre = [t.user_text for t in turns[:first_tool_turn + 1] if t.user_text]
                    folded = len(pre)
                    entry_inputs["user_turns_before_first_tool_call"] = [entry_inputs["user_message"], *pre]
                    turns = turns[first_tool_turn:]
                    turns[0] = Turn(calls=turns[0].calls, user_text=None, text=turns[0].text)
            yield TrajectoryRecord(
                corpus="taubench",
                episode_id=f"{model}:{domain}:{record.get('task_id')}:{record.get('trial')}",
                group_id=f"{domain}:{record.get('task_id')}",
                entry_state={"inputs": entry_inputs},
                turns=turns,
                model=model,
                attributes={
                    "architecture": "react_function_calling_conversational",
                    "domain": domain,
                    "trial": record.get("trial"),
                    "folded_user_turns": folded,
                },
                success=bool(record.get("reward")) if record.get("reward") is not None else None,
            )
