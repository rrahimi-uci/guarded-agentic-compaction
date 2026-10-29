"""Independent statistical references and fail-closed source-screening checks."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
from scipy.stats import beta, binom, binomtest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matched_compiler_feasibility as f


@pytest.mark.parametrize("better,worse", [(0.3, 0.1), (0.0, 0.1), (0.1, 0.0), (0.5, 0.5)])
def test_superiority_matches_enumerated_exact_tests(better, worse):
    n, alpha = 20, 0.1
    total = 0.0
    for m in range(1, n + 1):
        for k in range(m // 2 + 1, m + 1):
            if binomtest(k, m).pvalue <= alpha:
                total += binom.pmf(m, n, better + worse) * binom.pmf(k, m, better / (better + worse))
    assert f.superiority_power(n, better, worse, alpha) == pytest.approx(total, abs=1e-13)


def test_exact_tail_boundary_and_null():
    # Four favorable discordances: exact two-sided p=0.125, including equality.
    assert f.superiority_power(4, 1.0, 0.0, .125) == 1.0
    assert f.superiority_power(4, 1.0, 0.0, .124) == 0.0
    assert f.superiority_power(20, 0, 0) == 0
    assert f.superiority_power(300, .03, .03) <= .05 / 24 / 2


@pytest.mark.parametrize("args", [(0, .1, .1), (True, .1, .1), (10, -.1, .2),
                                   (10, .8, .3), (10, float('nan'), .1), (10, .1, .1, 0)])
def test_invalid_design_rejected(args):
    with pytest.raises(ValueError):
        f.superiority_power(*args)


def test_noninferiority_uses_strict_corrected_bound():
    assert f.ni_max_losses(300) == 4
    assert beta.ppf(1 - .05 / 24, 5, 296) < .05
    assert beta.ppf(1 - .05 / 24, 6, 295) >= .05
    assert f.ni_max_losses(305, .02) == -1
    assert f.ni_max_losses(306, .02) == 0
    assert f.ni_max_losses(614, .01) == -1
    assert f.ni_max_losses(615, .01) == 0


def test_power_numbers_and_scope():
    report = f.power_report()
    row = report['rows'][0]
    assert row['test_episodes_12_families_4_arms'] == 14400
    assert row['superiority_power'][1]['power'] == pytest.approx(.1538, abs=5e-5)
    assert row['five_point_ni_power'][1]['power'] == pytest.approx(.2824, abs=5e-5)
    assert report['candidate_calibration']['simultaneous_12_candidate_zero_error_minimum'] == 141
    assert 'not joint study power' in report['qualification']


def test_record_namespaces_and_ambiguous_selections():
    data = [
        {'repo': 'one/project', 'issue_number': 7},
        {'repository': 'two/project', 'splits': {'test_ids': [7, 8]}},
        {'record_number': 9}, {'selection': [10, True]},
        {'html_url': 'https://github.com/three/project/pull/11', 'number': 11, 'title': 'A'},
        {'html_url': 'https://github.com.evil.invalid/fake/repo/issues/99', 'value': 12},
        {'message': 'https://api.github.com/repos/four/project/issues/13'},
        {'requests': 300, 'seed': 20261028, 'correct': 17},
    ]
    qualified, ambiguous = f.mentioned_records(data)
    assert qualified == {'one/project': {7}, 'two/project': {7, 8}, 'three/project': {11}, 'four/project': {13}}
    assert ambiguous == {9, 10}


def test_comment_counts_are_not_comment_evidence_and_merge_missing_is_unknown():
    row = {'title': 'Example title with sufficient characters', 'state': 'closed',
           'comments': 3, 'pull_request': {'url': 'https://api.github.com/repos/a/b/pulls/1'}}
    result = f.classify_source_row(row)
    assert result['comment_text_available'] is False
    assert result['pr_outcome'] == 'unknown'
    row['pull_request']['merged_at'] = None
    assert f.classify_source_row(row)['pr_outcome'] == 'closed_unmerged'
    row['pull_request']['merged_at'] = '2026-01-01'
    assert f.classify_source_row(row)['pr_outcome'] == 'merged'
    row['comments'] = []
    assert f.classify_source_row(row)['comment_text_available'] is True


def test_inventory_verifies_checksum_excludes_ids_and_deduplicates(tmp_path, monkeypatch):
    import pyarrow as pa
    import pyarrow.parquet as pq
    monkeypatch.setattr(f, 'ROOT', tmp_path)
    rows = [{'number': 1, 'title': 'Example one', 'state': 'open', 'comments': ['actual text'],
             'updated_at': '2026-01-01', 'created_at': '2025-12-01'},
            {'number': 1, 'title': 'Updated one', 'state': 'closed', 'comments': ['actual text'],
             'updated_at': '2026-02-01', 'created_at': '2025-12-01'},
            {'number': 2, 'title': 'Excluded', 'state': 'open', 'comments': [],
             'updated_at': '2026-01-01', 'created_at': '2025-12-02'}]
    parquet = tmp_path / 'snapshot.parquet'
    pq.write_table(pa.Table.from_pylist(rows), parquet)
    manifest = tmp_path / 'source_manifest.json'
    manifest.write_text(json.dumps({'parquet_sha256': f.digest(parquet)}))
    actual = f.inventory_source('a/b', manifest, parquet, {2})
    assert actual['raw_rows'] == 3 and actual['unique_records'] == 2
    assert actual['counts']['remaining_records'] == 1
    assert actual['counts']['excluded_by_prior_screen'] == 1
    assert actual['counts']['is_open_issue'] == 0
    manifest.write_text(json.dumps({'parquet_sha256': 'bad'}))
    with pytest.raises(ValueError, match='checksum mismatch'):
        f.inventory_source('a/b', manifest, parquet, set())


def test_availability_preserves_incomplete_and_failed_requests(tmp_path, monkeypatch):
    calls = []
    def fake_run(argv, **kwargs):
        calls.append(argv)
        if len(calls) == 1:
            return SimpleNamespace(returncode=0, stdout='{"total_count": 123, "incomplete_results": true}')
        if len(calls) == 2:
            raise subprocess.TimeoutExpired(argv, 45)
        return SimpleNamespace(returncode=1, stdout='')
    monkeypatch.setattr(f.subprocess, 'run', fake_run)
    monkeypatch.setattr(f, 'REPOSITORIES', ('a/b',))
    path = tmp_path / 'availability.json'
    f.refresh_availability(path)
    rows = json.loads(path.read_text())['queries']
    assert len(rows) == 6
    assert rows[0]['incomplete_results'] is True
    assert rows[1]['status'] == 'unavailable'
    assert rows[2]['status'] == 'request_failed'
    assert all('--method' in argv and 'GET' in argv for argv in calls)
    assert all('total_count' not in row for row in rows[1:])
    with pytest.raises(ValueError, match='already exists'):
        f.refresh_availability(path)


def test_retained_report_reproduces_without_provider_or_optional_source_downloads():
    f.verify(f.OUT)


def test_verification_rejects_tampered_power(tmp_path):
    report = json.loads((f.OUT / 'report.json').read_text())
    report['power']['rows'][0]['superiority_power'][0]['power'] = .99
    f.write_json(tmp_path / 'report.json', report)
    (tmp_path / 'availability.json').write_text((f.OUT / 'availability.json').read_text())
    with pytest.raises(ValueError, match='do not reproduce'):
        f.verify(tmp_path)
