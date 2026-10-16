"""Pinned AWM offline workflow-memory adaptation; no browser or provider imports.

Only explicitly named, unchanged upstream function bodies are loaded. Domain
serialization and the SDK transport are study adaptations, not native AWM runs.
"""
from __future__ import annotations
import ast
import hashlib
import json
import os
import random
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / 'experiments/matched_reuse_baseline/vendor/awm'


def verify_vendor():
    pins = json.loads((VENDOR / 'PINS.json').read_text())
    for name, expected in pins['sha256'].items():
        if hashlib.sha256((VENDOR / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'upstream source changed: {name}')
    return pins


def functions(relative, names, namespace):
    """Load audited pure function bodies without upstream import-time clients."""
    verify_vendor()
    tree = ast.parse((VENDOR / relative).read_text())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    if {n.name for n in nodes} != set(names):
        raise ValueError('missing upstream function')
    scope = dict(namespace)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(VENDOR / relative), 'exec'), scope)
    return {name: scope[name] for name in names}


def induction_request(examples, model, tool_schemas):
    """Execute upstream llm_generate against a capture-only client; no network."""
    if not examples or any(set(e) != {'confirmed_task', 'action_reprs'} for e in examples):
        raise ValueError('induction requires action-only discovery examples')
    data = functions('mind2web/utils/data.py', ['format_examples'], {})
    requests = []
    def create(**kwargs):
        requests.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='capture-only'))])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    generate = functions('mind2web/offline_induction.py', ['llm_generate'],
                         {'client': client, **data})['llm_generate']
    instruction = (VENDOR / 'mind2web/prompt/instruction_action.txt').read_text()
    if not instruction.startswith('Given a list of web nagivation tasks,'):
        raise ValueError('unexpected upstream domain instruction')
    instruction = instruction.replace('web nagivation tasks', 'read-only API tasks', 1)
    instruction += '\nThe action space for these tasks is:\n' + json.dumps(tool_schemas, sort_keys=True)
    args = SimpleNamespace(INSTRUCTION=instruction,
        ONE_SHOT=(VENDOR / 'mind2web/prompt/one_shot_action.txt').read_text(),
        prefix=None, suffix='# Summary Workflows', model_name=model, temperature=0.0)
    assert generate(('Software', 'Issue triage', 'github'), examples, args) == 'capture-only'
    if len(requests) != 1:
        raise ValueError('unexpected upstream request count')
    return requests[0]


def filter_memory(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError('empty induction response')
    funcs = functions('mind2web/utils/data.py', ['is_website_header', 'filter_workflows'], {})
    memory = funcs['filter_workflows'](text, 'github').strip()
    if not memory:
        raise ValueError('upstream filter removed every workflow')
    return memory


def memory_messages(memory):
    """Use upstream workflow-only memory (retrieve_top_k=0), without test updates."""
    if not memory.strip():
        raise ValueError('missing frozen workflow memory')
    get = functions('mind2web/memory.py', ['get_exemplars'],
                    {'os': os, 'json': json, 'random': random.Random(20261019)})['get_exemplars']
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        (base/'workflow.txt').write_text(memory)
        (base/'exemplars.json').write_text('[]')
        args = SimpleNamespace(workflow_path=str(base/'workflow.txt'), memory_path=directory,
                               website='github', subdomain='Issue triage', domain='Software', retrieve_top_k=0)
        nested = get(args)
    return [message for example in nested for message in example]
