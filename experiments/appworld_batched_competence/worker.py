"""Pinned AppWorld common-entry batch API and official-grader worker.

This code runs only in an isolated development container. It cannot open the
ground truth or test split. The host supplies protected references only to
provider-free controls; model-facing agent mode receives public task material.
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


def saved_state_digest(directory):
    digest = hashlib.sha256()
    for path in sorted(Path(directory).rglob("*")):
        if path.is_file():
            digest.update(str(path.relative_to(directory)).encode() + b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def validate_batch(commands, public):
    if not isinstance(commands, list) or not 1 <= len(commands) <= 8:
        raise ValueError("batch must contain 1 to 8 calls")
    for command in commands:
        if not isinstance(command, dict) or set(command) != {"app", "api", "arguments"}:
            raise ValueError("invalid API command shape")
        app, api, arguments = command["app"], command["api"], command["arguments"]
        if not isinstance(app, str) or not isinstance(api, str) or not isinstance(arguments, dict):
            raise ValueError("invalid API command types")
        if (app, api) not in public:
            raise ValueError("unknown or private API")
        if api == "login" or (app, api) in {("supervisor", "show_profile"),
                                      ("supervisor", "show_account_passwords")}:
            raise ValueError("common-entry setup API is not an agent action")
        if set(arguments) & {"_app_name", "_api_name", "client", "track", "show", "raise_on_failure"}:
            raise ValueError("reserved requester argument")
        if "access_token" in arguments and arguments["access_token"] != "AUTO":
            raise ValueError("access_token must use the AUTO marker")
    return commands


def main():
    os.environ["APPWORLD_ROOT"] = "/work"
    Path("/work/data").symlink_to("/opt/world/data", target_is_directory=True)
    from appworld import AppWorld, load_task_ids
    from appworld.evaluator import evaluate_task

    request = json.loads(sys.stdin.readline())
    task_id = request["task_id"]
    mode = request["mode"]
    if task_id not in load_task_ids("train") or mode not in {"agent", "reference", "empty", "false_completion"}:
        raise ValueError("only selected training controls and agents are allowed")
    if mode == "reference" and not isinstance(request.get("commands"), list):
        raise ValueError("reference control needs host-supplied public calls")
    experiment = "gac_batched_competence"
    with contextlib.redirect_stdout(io.StringIO()):
        world = AppWorld(task_id=task_id, experiment_name=experiment,
            load_ground_truth=False, ground_truth_mode="minimal", random_seed=20261106,
            max_interactions=128, max_api_calls_per_interaction=256,
            timeout_seconds=30, raise_on_failure=False,
            raise_on_unsafe_syntax=True, raise_on_unsafe_execution=True)
    public = {(app, api) for app, docs in world.task.api_docs.items() for api in docs}
    tokens = {}
    calls = []
    setup = []
    try:
        def raw_call(app, api, arguments):
            with contextlib.redirect_stdout(io.StringIO()):
                return world.requester.request(app, api, **arguments)

        profile = raw_call("supervisor", "show_profile", {})
        passwords = {r["account_name"]: r["password"]
                     for r in raw_call("supervisor", "show_account_passwords", {})}
        setup.extend(["supervisor.show_profile", "supervisor.show_account_passwords"])
        apps = sorted(app for app, api in public if api == "login")
        for app in apps:
            result = raw_call(app, "login", {
                "username": profile["phone_number" if app == "phone" else "email"],
                "password": passwords[app]})
            if not isinstance(result, dict) or not isinstance(result.get("access_token"), str):
                raise ValueError("common-entry login failed")
            tokens[app] = result["access_token"]
            setup.append(app + ".login")
        if len(setup) != 11:
            raise ValueError("unexpected common-entry call count")
        with contextlib.redirect_stdout(io.StringIO()):
            world.save()
        entry_digest = saved_state_digest(world.output_db_home_path_on_disk)

        def execute_batch(commands):
            validate_batch(commands, public)  # reject malformed tail before any effect
            outputs = []
            for command in commands:
                app, api = command["app"], command["api"]
                args = dict(command["arguments"])
                if args.get("access_token") == "AUTO":
                    if app not in tokens:
                        raise ValueError("no authenticated token for app")
                    args["access_token"] = tokens[app]
                try:
                    result = raw_call(app, api, args)
                except Exception as exc:
                    result = {"error": type(exc).__name__, "detail": str(exc)[:500]}
                row = {"app": app, "api": api, "arguments": command["arguments"], "result": result}
                calls.append(row)
                outputs.append(row)
                if isinstance(result, dict) and "error" in result:
                    break
            return outputs

        if mode == "reference":
            for i in range(0, len(request["commands"]), 8):
                outcomes = execute_batch(request["commands"][i:i + 8])
                if len(outcomes) < len(request["commands"][i:i + 8]):
                    break
        elif mode == "false_completion":
            execute_batch([{"app": "supervisor", "api": "complete_task",
                            "arguments": {"answer": "UNSUPPORTED ANSWER"}}])
        elif mode == "agent":
            emit({"type": "context", "instruction": world.task.instruction,
                  "datetime": str(world.task.datetime), "apps": world.task.app_descriptions,
                  "documentation": world.task.api_docs.get("api_docs", {}),
                  "authenticated_apps": apps, "setup_calls": len(setup),
                  "entry_state_sha256": entry_digest})
            for _ in range(128):
                line = sys.stdin.readline()
                if not line:
                    raise RuntimeError("agent disconnected before finish")
                command = json.loads(line)
                if command.get("type") == "finish":
                    break
                if command.get("type") != "batch":
                    raise ValueError("invalid agent message")
                if len(calls) >= 192:
                    emit({"type": "batch_result", "error": "api_call_cap", "calls": []})
                    continue
                try:
                    batch_commands = validate_batch(command.get("commands"), public)
                    if len(calls) + len(batch_commands) > 192:
                        raise ValueError("api_call_cap")
                    results = execute_batch(batch_commands)
                    emit({"type": "batch_result", "calls": results,
                          "stopped_on_error": len(results) != len(batch_commands)})
                except ValueError as exc:
                    emit({"type": "batch_result", "error": str(exc)[:300], "calls": []})
            else:
                raise RuntimeError("batch request limit")
        with contextlib.redirect_stdout(io.StringIO()):
            world.save()
        final_digest = saved_state_digest(world.output_db_home_path_on_disk)
    finally:
        with contextlib.redirect_stdout(io.StringIO()):
            world.close()
    with contextlib.redirect_stdout(io.StringIO()):
        grade = evaluate_task(task_id=task_id, experiment_name=experiment, suppress_errors=True)
    if grade.num_tests <= 0:
        raise RuntimeError("empty official evaluator")
    emit({"type": "evaluation", "success": grade.success,
          "tests": grade.num_tests, "passed_tests": grade.pass_count,
          "setup_calls": len(setup), "agent_calls": len(calls),
          "entry_state_sha256": entry_digest,
          "final_state_sha256": final_digest,
          "calls": calls})


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        emit({"type": "failure", "error": type(exc).__name__, "detail": str(exc)[:500]})
        sys.exit(1)
