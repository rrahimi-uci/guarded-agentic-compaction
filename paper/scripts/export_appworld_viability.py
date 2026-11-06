"""Encrypt protected development records and publish only aggregate evidence."""
import json
import subprocess

from adaptive_pilot import ROOT, digest, write
from appworld_adaptive_viability import BASE, CACHE, IMAGE, OUT, verify_records
from analyze_appworld_viability import build

# Executed in the trusted pinned image, never supplied by an agent. No provider key
# or host home directory is mounted. Upstream license notices are included.
PACK = """
import hashlib,json,shutil
from pathlib import Path
from appworld.common.crypto import pack_bundle,unpack_bundle
from appworld.common.constants import PASSWORD,SALT
shutil.copytree('/input','/work/evidence',ignore=shutil.ignore_patterns('*.lock','*.tmp'))
before={str(p.relative_to('/work')):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in Path('/work/evidence').rglob('*') if p.is_file()}
files=pack_bundle('/output/operational_evidence.bundle','/work',['evidence'],PASSWORD,SALT)
unpack_bundle('/output/operational_evidence.bundle','/work/roundtrip',PASSWORD,SALT)
assert all(hashlib.sha256((Path('/work/roundtrip')/p).read_bytes()).hexdigest()==h for p,h in before.items())
Path('/output/bundle_verification.json').write_text(json.dumps({'files_before_notices':len(before),
    'packed_files':len(files),'roundtrip_original_files_verified':len(before),'passed':True},indent=2)+'\\n')
"""


def export():
    if (OUT / "operational_evidence.bundle").exists():
        raise ValueError("published bundle exists; retain it and version amendments")
    seal = verify_records()
    build()
    report = json.loads((OUT / "report.json").read_text())
    planned = json.loads((CACHE / "analysis_plan.json").read_text())
    original = CACHE / "sealed_sources/paper/scripts/analyze_appworld_viability.py"
    if digest(original) != planned["analysis_sha256"]:
        raise ValueError("original analysis plan drift")
    amendment = json.loads((BASE / "persistence_repair/analysis_amendment.json").read_text())
    if digest(ROOT / "paper/scripts/analyze_appworld_viability.py") != amendment["amended_analysis_sha256"]:
        raise ValueError("amended analysis drift")
    # The public seal contains task identifiers and generic tool schemas, never
    # instructions or expected outputs. Raw examples/program literals are encrypted.
    write(OUT / "seal.json", seal)
    write(OUT / "analysis_plan.json", planned)
    write(OUT / "analysis_amendment.json", amendment)
    write(OUT / "repair_plan.json", json.loads((BASE / "persistence_repair/plan.json").read_text()))
    subprocess.run(["docker", "run", "--rm", "--network", "none", "--read-only",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--memory", "4g",
        "--tmpfs", "/work:rw,nosuid,size=2g,mode=1777", "-v", f"{BASE}:/input:ro",
        "-v", f"{OUT}:/output:rw", IMAGE, "-I", "-c", PACK], check=True, timeout=120)
    report["encrypted_evidence_sha256"] = digest(OUT / "operational_evidence.bundle")
    report["bundle_verification"] = json.loads((OUT / "bundle_verification.json").read_text())
    report["export_source_sha256"] = digest(__file__)
    report["sealed_source_hashes"] = seal["source_hashes"]
    report["prior_seal_sha256"] = digest(BASE / "seal.json")
    # Retain structural accounting without redistributing protected raw content.
    files = [p for p in BASE.rglob("*") if p.is_file() and p.suffix not in {".lock", ".tmp"}]
    report["protected_raw_files"] = [{"path": str(p.relative_to(BASE)), "bytes": p.stat().st_size, "sha256": digest(p)} for p in sorted(files)]
    write(OUT / "report.json", report)
    a = report["summary"]["arms"]
    table = "\n".join(f"| {arm} | {r['scheduled']} | {r['statuses'].get('completed', 0)} | {r['statuses'].get('failed', 0)} | {r['statuses'].get('unstarted', 0)} | {r['model_requests']} | ${r['accounted_upper_usd']:.6f} |"
                      for arm, r in a.items())
    repair = report["persistence_repair"]
    valid = [r for r in repair["regrades"] if r["diagnostic_valid"]]
    text = """# AppWorld adaptive development pilot: interrupted measurement

**Decision: NO_GO for confirmatory compiler-value claims. The original task grades
are invalid because the direct-API adapter did not persist final state.** Paid
execution stopped as soon as this boundary defect was suspected. There were no
paid retries or replacement tasks. This report does not estimate comparative quality.

| Arm | Scheduled | Completed with invalid grade | Interrupted | Unstarted | Model responses | Accounted API upper estimate |
|---|---:|---:|---:|---:|---:|---:|
""" + table + "\n\n" + """
The planned comparison selected 12 official training scenarios, one variation per
scenario, in a fixed hash order. All were development-only and previously exposed.
The handwritten arm executed two actual supervisor reads, counted in the same API
limit, before the same model continuation. Arm order alternated. Model, context
policy, task list and limits were never tuned in response to scores.

## Two independent environment findings

Before paid execution, the original dependency environment passed 11/12 reference
controls and all 24 negative controls. One reference grader raised SQLite
missing-table exceptions. A SQLAlchemy 2.0.44 / SQLModel 0.0.44 image resolved the
same unmodified case. All 36 controls passed on that image. The complete data tree
is unchanged: 14,885 files with the same aggregate hash. This identifies a working
dependency pair, not the individual cause. Upstream's
[separate compatibility issue](https://github.com/StonyBrookNLP/appworld/issues/229)
motivated investigation but does not establish the cause of our different error.

Those reference controls used `AppWorld.execute`, which saves state automatically.
The model adapter used `Requester.request`, which does not; `AppWorld.close` does
not save either. The official evaluator consequently read the initialization
snapshot. The original negative controls could not detect this defect.

A provider-free reproduction sent the same 25 known-correct public API calls
through the agent path. All responses matched the reference. The original worker
passed 0/6 grading assertions; explicit `world.save()` before `world.close()`
passed 6/6. The correction now fails the worker if persistence fails, and cleanup
still closes the environment. Saving is trusted evaluator plumbing, outside the
agent tool's SQL-effect diagnostic. It is not an added agent capability.

The corrected actual agent path passed all three controls: known-correct public
calls, empty interaction and false completion. A separately sealed repair then
replayed every completed original history, with no model calls, requiring exact
public-context and API-result equality. Original records were never overwritten.
""" + f"\nDiagnostic regrades with exact parity: {len(valid)}/{len(repair['regrades'])}; official task successes among those replays: {sum(r['success'] is True for r in valid)}. These are deterministic regrades of an interrupted development run, not fresh adaptive trials or a comparative estimate.\n\n" + """
## Compiler interpretation

Discovery retains every scheduled baseline disposition, including failed and
unstarted attempts; all original outcome labels are marked unknown. The first
eight scenarios are discovery groups and the last four development challenge
groups. There are no calibration/test groups and no admitted artifacts.

""" + "```text\n" + report["compiler"]["report"] + "\n```\n\n" + """
Before paid execution, the analysis plan recorded that the audited initial-prefix
catalog permits only documentation/profile/password reads. Authentication remains
a write barrier; other APIs remain unknown. This scope cannot establish two
nontrivial compiler families, regardless of task scores. No gate was relaxed to
produce a candidate. The interrupted traces provide neither compiler superiority
nor learned-gate, population-risk or maintenance-economics evidence.

## Next decision and retained evidence

Do not scale or resume this sealed pilot. A new workload/entry protocol must expose
meaningful audited reads before a write barrier, with identical initialization and
information across arms. An explicitly preauthenticated entry is one possible new
protocol, not an implemented result or a reason to reclassify login. Before further
paid trials, validate known-correct sequences through the exact model-call and
grading path, then establish candidate viability and a competent baseline. Freeze
fresh independent calibration/testing only after those gates pass. Alternatively,
narrow the paper to the contribution already supported.

The $8 local allocation and $300 campaign cap remain binding. All interrupted-call
reservations remain charged. API amounts are conservative accounting, not invoices
or total lifecycle costs. No manuscript numerical claim or PDF changed.

See [aggregate report](report.json), [original seal](seal.json),
[original pre-execution analysis plan](analysis_plan.json),
[explicit analysis amendment](analysis_amendment.json), [provider-free repair plan](repair_plan.json),
[ledger excerpt](ledger_excerpt.json), [encrypted records](operational_evidence.bundle),
and [protocol](../../../experiments/appworld_adaptive_viability/README.md).
Original frozen source bytes, failed controls, diagnostics and regrades are retained
inside the bundle. Historical seals refer to those original bytes; the checked-in
worker includes the separately documented persistence correction. The original
runner refuses source drift and stopped attempts, so it cannot resume this pilot.

Use the pinned upstream bundle utility and public distribution constants to inspect
protected records locally; do not redistribute decrypted contents. Export verifies
an encrypt/decrypt round trip against every original raw file hash.
"""
    (OUT / "REPORT.md").write_text(text)
    print(json.dumps({"decision": report["decision"], "bundle_sha256": report["encrypted_evidence_sha256"], "budget": report["budget"]}))


if __name__ == "__main__":
    export()
