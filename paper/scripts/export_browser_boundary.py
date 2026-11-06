"""Retain every setup/control attempt and verify a bounded mechanism report."""
import argparse
import json
from pathlib import Path
import tarfile

from adaptive_benchmark_screen import ROOT, sha
from browser_staging_boundary import OUT
from browser_boundary_controls import CASES
from webarena_verified_development import SOURCE, write

CACHE = ROOT / "benchmarks/.cache/browser_boundary"


def export(attempt_names):
    if (OUT / "report.json").exists():
        raise ValueError("published evidence exists; version amendments instead of overwriting")
    if len(attempt_names) != len(set(attempt_names)) or not attempt_names:
        raise ValueError("explicit distinct attempt directories required")
    attempts = []
    for name in attempt_names:
        if Path(name).name != name:
            raise ValueError("attempt name must be one path component")
        path = CACHE / name
        seal = json.loads((path / "seal.json").read_text())
        report = json.loads((path / "report.json").read_text())
        if [r["case"] for r in report["rows"]] != seal["cases"]:
            raise ValueError("missing, repeated or reordered control")
        if any(r["status"] not in {"completed", "failed"} for r in report["rows"]):
            raise ValueError("nonterminal attempt")
        # Early setup attempt used flat source copies; preserve them and add
        # canonical copies only after checking the original pre-run hashes.
        for rel, expected in seal["source_hashes"].items():
            canonical = path / "sealed_sources" / rel
            candidates = [canonical, path / "sealed_sources" / Path(rel).name, ROOT / rel]
            source = next((p for p in candidates if p.is_file() and sha(p) == expected), None)
            if source is None:
                raise ValueError("cannot recover sealed source: " + rel)
            if not canonical.exists():
                canonical.parent.mkdir(parents=True, exist_ok=True)
                canonical.write_bytes(source.read_bytes())
        attempts.append({"name": name, "seal": seal, "report": report})
    final = attempts[-1]
    if (final["seal"]["cases"] != list(CASES) or not final["report"]["all_passed"]
            or not final["report"]["ledger_unchanged"] or final["report"]["remaining_owned_containers"]
            or final["report"]["remaining_owned_networks"]):
        raise ValueError("final controls or cleanup incomplete")
    for rel, expected in final["seal"]["source_hashes"].items():
        if sha(ROOT / rel) != expected:
            raise ValueError("current implementation differs from final control seal: " + rel)
    if sha(OUT / "discovery.json") != final["seal"]["candidate_sha256"]:
        raise ValueError("discovery changed after controls")
    OUT.mkdir(parents=True, exist_ok=True)
    files = []
    archive = OUT / "raw_evidence.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for attempt in attempts:
            for path in sorted((CACHE / attempt["name"]).rglob("*")):
                if not path.is_file():
                    continue
                rel = str(path.relative_to(CACHE))
                tar.add(path, arcname=rel, recursive=False)
                files.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha(path)})
        license_path = SOURCE / "LICENSE"
        tar.add(license_path, arcname="upstream/LICENSE", recursive=False)
        files.append({"path": "upstream/LICENSE", "bytes": license_path.stat().st_size, "sha256": sha(license_path)})
        postmill_license = OUT / "Postmill-LICENSE.txt"
        tar.add(postmill_license, arcname="upstream/Postmill-LICENSE.txt", recursive=False)
        files.append({"path": "upstream/Postmill-LICENSE.txt", "bytes": postmill_license.stat().st_size, "sha256": sha(postmill_license)})
    ledger = json.loads((ROOT / "benchmarks/.cache/adaptive_compiler_pilot/ledger.json").read_text())
    report = {"schema": "browser-boundary-mechanism-v1", "status": "RESEARCH_ONLY_NO_ADMISSION",
        "provider_calls": 0, "new_api_spend_usd": 0, "campaign_accounted_upper_usd": ledger["accounted_upper_usd"],
        "remaining_campaign_cap_usd": ledger["cap_usd"] - ledger["accounted_upper_usd"],
        "raw_archive_sha256": sha(archive), "raw_files": files, "final_attempt": final["name"],
        "attempts": [{"name": a["name"], "all_passed": a["report"]["all_passed"],
            "cases": [{k: r.get(k) for k in ("case", "status", "passed", "error", "detail", "elapsed_seconds_including_setup_cleanup")}
                      for r in a["report"]["rows"]],
            "ledger_unchanged": a["report"]["ledger_unchanged"],
            "remaining_owned_containers": a["report"]["remaining_owned_containers"],
            "remaining_owned_networks": a["report"]["remaining_owned_networks"]} for a in attempts],
        "final_controls": final["report"], "source_hashes": final["seal"]["source_hashes"],
        "export_source_sha256": sha(__file__), "discovery_sha256": sha(OUT / "discovery.json"),
        "interpretation": "One development task; handwritten continuation and unadmitted program controls. No adaptive GAC task-success, independent holdout, calibration, admission, comparator superiority or efficiency evidence.",
        "amendments": ["Attempt 1: missing matching Chromium executable; all four setup controls failed. Browser installed afterward.",
            "Attempt 2: strict static URL filtering rejected five pinned cache-busting URLs and an SVG resource; native-select control did not match the fully loaded Select2 UI. Entire attempt is setup evidence, including its confounded negative-control passes.",
            "Attempt 3: exact static URLs permitted, Select2 interactions corrected, and negative controls require the intended isolated failure. All five controls passed.",
            "Attempt 4: repeat all five controls after adding a final postcondition/network-policy check following the data digest; a unit regression covers a violation arriving during that digest.",
            "Attempt 5: repeat all five controls after registering network cleanup before creation; a unit regression simulates Docker creating the network but losing the CLI response. No provider calls in any attempt."]}
    write(OUT / "report.json", report)
    write(OUT / "seal.json", final["seal"])
    table = []
    for row in final["report"]["rows"]:
        table.append(f"| {row['case']} | {row['boundary']['outcome']} | {row['evaluation']['status']} | {row['elapsed_seconds_including_setup_cleanup']:.1f} |")
    text = """# Browser boundary: development mechanism evidence

**Status: research controls passed; no admitted artifact and no new paper performance claim.**

The compiler found one single-call candidate from four of six retained development
templates, then rejected it at `no_dev_groups`. All six tasks, 42 provider responses,
36 browser actions and six action errors remain in discovery. The candidate opens
the submission form; a handwritten shortcut performs the same action.

The final controls use **one already exposed development task (634)**, a pinned
website and official independent HAR grader. Continuation is handwritten, not
adaptive model execution. The automatic candidate is executed only as an explicitly
unadmitted mechanism control, never through an activated registry.

| Final control | Boundary outcome | Official task grade | Seconds including setup/cleanup |
|---|---|---|---:|
""" + "\n".join(table) + """

For the two handoff controls, the original staged application, context and page
are promoted. After verifier rejection, the staged instance is destroyed and the
handwritten continuation posts through a fresh baseline. Database mutation is
detected; the fresh baseline's full data digest equals the original entry digest.
The blocked POST never reaches the backend. The latter two controls take no
baseline action and the official grader rejects their false success responses.
No owned containers or networks remained after any completed run.

All five attempts are retained. Attempt 1 failed four controls because the matching
Chromium executable was missing. Attempt 2 failed its three positive/fallback
controls because of the static URL policy and the hidden native select; its two
negative passes are confounded setup evidence. Attempt 3 corrected the exact static
URLs and Select2 interactions and required each negative test to isolate its intended
failure; all five controls passed. A review then added a final form/network-policy
check after the data digest to reject late changes, with a targeted unit regression.
Attempt 4 repeats all five controls against that hardened implementation. A second
review fix registers network cleanup before creation, covering a lost CLI response
after Docker creates a resource; a unit regression injects that failure. Attempt 5
repeats all controls against the final implementation. Earlier failures were not
replaced or counted as final successful evidence.

**No new provider calls or API charges.** The shared campaign ledger is unchanged;
""" + f"its accounted upper estimate is ${ledger['accounted_upper_usd']:.7f}, leaving ${ledger['cap_usd'] - ledger['accounted_upper_usd']:.7f} of the $300 cap.\n" + """
These figures are conservative ledger accounting, not an invoice. Local compute
is unpriced. Control durations are descriptive, include expensive data dumps and
container lifecycle work, and are not speed or cost comparisons. Failed staging
costs remain recorded and cannot be rolled back.

The boundary applies only before a fresh episode exists. It does not restore an
arbitrary live browser or prove exact equality of all external state. File sessions,
CSRF tokens and logs remain within the owned container. Full business-data hashing
does not prove the absence of every side effect. The pinned backend uses its own
bridge; browser request filtering is not a general server egress sandbox.

The current candidate lacks a task-selective routing rule: root-page access also
matches a retrieval task. There is no held-out calibration, admitted GAC arm, native
Agent JIT run, matched compiler experiment, independent population estimate or net
economic result. The manuscript and PDFs remain unchanged. The next scientific
decision is whether a diverse candidate with meaningful guard failures survives
development, then whether fresh matched evaluation is affordable.

See [the protocol](../../supplementary/browser-boundary-development.md),
[discovery](discovery.json), [complete report](report.json), [successful seal](seal.json),
[source audit](source_audit.json), [local runtime](runtime.json), and [all raw attempts](raw_evidence.tar.gz).
The raw archive includes HARs, terminal outcomes, source copies and setup failures;
its file hashes are listed in `report.json`. The baseline corpus remains in the
earlier development archive. Upstream benchmark and Postmill license texts are
retained with the archive. No hidden task answers entered a provider prompt.
"""
    (OUT / "REPORT.md").write_text(text)
    print(json.dumps({"attempts_retained": len(attempts), "final_controls": len(final["report"]["rows"]),
                      "all_passed": True, "provider_calls": 0, "archive_bytes": archive.stat().st_size}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("attempts", nargs="+")
    export(parser.parse_args().attempts)
