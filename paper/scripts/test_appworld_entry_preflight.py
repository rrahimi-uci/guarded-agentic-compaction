"""Offline boundary and publication checks; no AppWorld installation or provider."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from adaptive_pilot import ROOT, digest
from appworld_entry_preflight import OUT
from appworld_entry_controls import commands_for
from export_appworld_entry_preflight import summarize_references


def worker():
    spec = importlib.util.spec_from_file_location('entry_worker_test', ROOT/'experiments/appworld_entry_preflight/entry_worker.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_direct_boundary_rejects_private_or_reserved_calls_before_execution():
    calls = []
    world = SimpleNamespace(requester=SimpleNamespace(request=lambda *args, **kwargs: calls.append((args, kwargs))))
    module = worker()
    for command in [
        {'tool': 'spotify.private', 'arguments': {}},
        {'tool': 'spotify.show_song_library', 'arguments': {'_api_name': 'remove_song_from_library'}},
        {'tool': 'spotify.show_song_library', 'arguments': {'track': False}},
        {'tool': 'spotify.show_song_library', 'arguments': {}, 'extra': 'unexpected'},
    ]:
        with pytest.raises(ValueError):
            module.public_call(world, {'spotify.show_song_library'}, command)
    assert calls == []
    module.public_call(world, {'spotify.show_song_library'}, {'tool': 'spotify.show_song_library', 'arguments': {'page_index': 0}})
    assert calls == [(('spotify', 'show_song_library'), {'page_index': 0})]


def test_saved_state_tree_detects_content_and_file_changes(tmp_path):
    module = worker()
    (tmp_path/'one').write_text('state')
    first = module.tree(tmp_path)
    assert first == module.tree(tmp_path)
    (tmp_path/'one').write_text('changed')
    assert first != module.tree(tmp_path)
    (tmp_path/'one').write_text('state')
    (tmp_path/'two').write_text('extra')
    assert first != module.tree(tmp_path)


def test_reference_control_removes_only_common_entry_not_task_writes():
    calls = [{'tool': name, 'arguments': {}} for name in ['supervisor.show_profile', 'spotify.login',
        'spotify.show_song_library', 'spotify.remove_song_from_library', 'supervisor.complete_task']]
    actual = commands_for({'calls': calls}, 'reference')
    assert [c['tool'] for c in actual] == ['spotify.show_song_library', 'spotify.remove_song_from_library', 'supervisor.complete_task']
    with pytest.raises(ValueError):
        commands_for({'calls': calls}, 'unknown')


def test_reference_summary_does_not_drop_failures_or_invent_model_boundaries():
    rows = [{'task_id': name, 'status': 'completed', 'reference_success': success, 'calls': [], 'tests': 2, 'passed_tests': 2 if success else 0}
            for name, success in [('a_1', True), ('b_1', False)]]
    seal = {'tasks': ['a_1', 'b_1']}
    summary = summarize_references(seal, rows)
    assert summary['reference_successes'] == 1 and len(summary['tasks']) == 2
    assert summary['posthoc_reference_prefix_hypotheses'] == {'songs': [], 'playlists': []}
    for invalid in [rows[:1], rows+[rows[0]], [dict(r, status='started') for r in rows]]:
        with pytest.raises(ValueError):
            summarize_references(seal, invalid)


def test_retained_entry_controls_are_complete_and_do_not_claim_admission():
    report = json.loads((OUT/'report.json').read_text())
    seal = json.loads((OUT/'entry_control_seal.json').read_text())
    rows = report['controls']
    assert len(rows) == 60
    assert {(r['task_id'], r['mode']) for r in rows} == {(t, m) for t in seal['tasks'] for m in seal['modes']}
    assert all(r['passed'] for r in rows)
    assert all(r['setup_calls'] == 11 and len(r['setup_apps']) == 9 for r in rows)
    for row in rows:
        if row['mode'] in {'songs', 'playlists'}:
            assert row['saved_state_unchanged'] is True and row['control_calls'] == 2
        else:
            assert row['official_success'] is (row['mode'] == 'reference')
    assert len(report['common_entry_parity']) == 12
    assert all(r['identical_setup'] and r['identical_saved_entry'] for r in report['common_entry_parity'])
    for task in seal['tasks']:
        assert len({r['entry_setup_sha256'] for r in rows if r['task_id'] == task}) == 1
        assert len({r['entry_saved_state_sha256'] for r in rows if r['task_id'] == task}) == 1
    summary = report['reference_summary']
    assert len(summary['tasks']) == summary['reference_successes'] == 12
    assert sum(r['api_calls'] for r in summary['tasks']) == summary['total_reference_api_calls'] == 701
    assert summary['min_reference_api_calls'] == 8 and summary['max_reference_api_calls'] == 145
    assert summary['references_above_old_24_request_limit'] == 9
    assert all(len(ids) == 3 for ids in summary['posthoc_reference_prefix_hypotheses'].values())
    assert report['effect_boundary']['catalog_changed'] is False
    assert report['effect_boundary']['artifacts_emitted'] == report['effect_boundary']['calibration_groups'] == report['effect_boundary']['test_groups'] == 0
    assert report['budget']['new_model_requests'] == report['budget']['new_model_cost_usd'] == 0
    assert report['decision'] == 'COMMON_ENTRY_VALIDATED_NO_CONFIRMATORY_GO'
    assert digest(OUT/'operational_evidence.bundle') == report['encrypted_evidence_sha256']
    assert report['bundle_verification']['passed']
    assert report['bundle_verification']['roundtrip_original_files_verified'] == len(report['protected_raw_files'])
    for rel, sha in seal['source_hashes'].items():
        assert digest(ROOT/rel) == sha
    assert report['export_source_sha256'] == digest(ROOT/'paper/scripts/export_appworld_entry_preflight.py')
