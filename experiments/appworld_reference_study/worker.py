"""JSON-only AppWorld boundary. Run in the pinned, networkless container.

The agent receives public task context and public APIs only. Grading occurs after
the interaction ends. Reference solutions are accessible only in a separate
development-only control mode, never via an agent tool.
"""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys


def emit(value):
    sys.__stdout__.write(json.dumps(value, default=str, sort_keys=True) + "\n")
    sys.__stdout__.flush()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    # Only this disposable directory is writable; original data stays read-only.
    os.environ["APPWORLD_ROOT"] = "/work"
    Path("/work/data").symlink_to("/opt/world/data", target_is_directory=True)
    from appworld import AppWorld, load_task_ids
    from appworld.evaluator import evaluate_task
    from appworld.common.constants import DATA_VERSION

    request = json.loads(sys.stdin.readline())
    mode = request["mode"]
    if mode == "inventory":
        splits = {s: load_task_ids(s) for s in ("train", "dev", "test_normal", "test_challenge")}
        # No task instruction, test, reference answer, or model result is inspected.
        files = sorted(p for p in Path("/opt/world/data").rglob("*") if p.is_file())
        tree = hashlib.sha256()
        for path in files:
            tree.update((str(path.relative_to("/opt/world/data")) + ":" + digest(path) + "\n").encode())
        emit({"type": "inventory", "data_version": DATA_VERSION, "data_tree_sha256": tree.hexdigest(),
              "data_file_count": len(files), "splits": splits})
        return
    if mode not in {"reference", "empty", "false_completion", "agent"}:
        raise ValueError("unsupported mode")
    task_id = request["task_id"]
    # This implementation is deliberately unable to open benchmark test tasks.
    if task_id not in load_task_ids("train"):
        raise ValueError("development runner only accepts the official train split")
    experiment = "gac_development"
    reference = mode == "reference"
    with contextlib.redirect_stdout(io.StringIO()):
        world = AppWorld(task_id=task_id, experiment_name=experiment,
            load_ground_truth=reference, ground_truth_mode="full" if reference else "minimal",
            random_seed=20261106, max_interactions=64, max_api_calls_per_interaction=1000 if reference else 64,
            timeout_seconds=30, raise_on_failure=False,
            raise_on_unsafe_syntax=True, raise_on_unsafe_execution=True)
    public = {(app, name) for app, docs in world.task.api_docs.items() for name in docs}
    calls = []
    try:
        if reference:
            with contextlib.redirect_stdout(io.StringIO()):
                code = world.task.ground_truth.compiled_solution_code
                output = world.execute(code + "\nsolution(apis, requester)")
            # Retained only in encrypted development evidence by the host.
            emit({"type": "reference_output", "output": output})
        elif mode == "false_completion":
            with contextlib.redirect_stdout(io.StringIO()):
                output = world.execute('apis.supervisor.complete_task(answer="UNSUPPORTED ANSWER")')
            emit({"type": "control_output", "output": output})
        elif mode == "agent":
            emit({"type": "context", "instruction": world.task.instruction,
                  "datetime": str(world.task.datetime), "apps": world.task.app_descriptions,
                  "documentation": world.task.api_docs.get("api_docs", {})})
            for _ in range(64):
                line = sys.stdin.readline()
                if not line:
                    raise RuntimeError("agent disconnected before finish")
                message = json.loads(line)
                if message.get("type") == "finish":
                    break
                if message.get("type") != "call":
                    raise ValueError("invalid agent command")
                app, api, arguments = message.get("app"), message.get("api"), message.get("arguments")
                if not isinstance(app, str) or not isinstance(api, str) or not isinstance(arguments, dict):
                    raise ValueError("invalid API call shape")
                if (app, api) not in public:
                    result = {"error": "unknown_or_private_api"}
                elif any(k in arguments for k in ("_app_name", "_api_name", "client", "track", "show", "raise_on_failure")):
                    result = {"error": "reserved_argument"}
                else:
                    try:
                        with contextlib.redirect_stdout(io.StringIO()):
                            result = world.requester.request(app, api, **arguments)
                    except Exception as exc:
                        result = {"error": type(exc).__name__, "detail": str(exc)[:500]}
                calls.append({"tool": app + "." + api, "arguments": arguments, "result": result})
                emit({"type": "result", "result": result})
            else:
                raise RuntimeError("64 API call limit")
    finally:
        with contextlib.redirect_stdout(io.StringIO()):
            world.close()
    # The official evaluator loads its tests in trusted code after the agent ends.
    with contextlib.redirect_stdout(io.StringIO()):
        tracker = evaluate_task(task_id=task_id, experiment_name=experiment, suppress_errors=True)
    if tracker.num_tests <= 0:
        raise RuntimeError("empty evaluator cannot count as a pass")
    emit({"type": "evaluation", "success": tracker.success, "tests": tracker.num_tests,
          "passed_tests": tracker.pass_count, "calls": calls})


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        emit({"type": "failure", "error": type(exc).__name__, "detail": str(exc)[:500]})
        sys.exit(1)
