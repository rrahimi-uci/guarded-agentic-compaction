# Exploratory SEC EdgarTools pilot

On 2026-10-15, the provider-free SEC acquisition ran with four CIKs in this
order: Microsoft `0000789019`, JPMorgan Chase `0000019617`, Walmart
`0000104169`, and Intel `0000050863`. The first single-issuer Apple
`0000320193` probe exposed a filing-index path check that rejected the SEC's
full directory name; the same defect affected the four-issuer probe. After
correcting the path check, all four issuers yielded complete candidates and
the existing deterministic selector retained one hard-state Walmart case.
The source requests used a user-supplied contact identity, which is not stored
here. Raw SEC responses remain in the local, ignored acquisition cache.

The retained `cases.jsonl`, `gold.jsonl`, `snapshot.json`, and `report.json`
record the selected case and source digests. `edgartools_audit.json` binds to
that snapshot and case file and records **1/1 pass** for accession, period,
filing date, unit, and value against the checksum-pinned Company Facts JSON.
The audit made **zero model-provider calls**. It can be replayed offline from
the original cache with:

```bash
python -m benchmarks.audit_sec_edgartools \
  --pool paper/results/multidomain/pilots/sec_edgartools \
  --cache /path/to/original-sec-cache
```

This was an exploratory implementation probe, not a sealed sample or a
three-domain study. It checks an independent parser over the **same SEC Company
Facts response**, not an independent filing-derived gold answer. The planned
420-group SEC pool, independent gold review, macro comparison, and live agent
study were outstanding at the time of this pilot. The later
[420-group provider-free preflight](../../preflight/sec/README.md) completed
acquisition and code-level checks; independent human review and the live study
remain outstanding. No paper score or acceptance claim follows from this one
pilot case.
