# SEC preflight candidate frame

The provider-free SEC acquisition began on 2026-10-15 from the SEC's
[`company_tickers.json`](https://www.sec.gov/files/company_tickers.json).
`company_tickers.source.json` preserves the exact response; its SHA-256 and
the candidate-file SHA-256 are recorded in `sec-source.json`. Before issuer
acquisition, we selected the first 700 distinct CIKs in source order and
froze them in `sec-ciks.json`. No failed issuer is replaced outside that list.

This is a convenience frame of ticker-listed issuers, not a random or
representative sample of SEC filers. The pool builder may inspect candidates
in this fixed order until it has 520 complete groups, then retains 420 with
its predefined hard-state stratification. Its rejection list and all selected
case/source digests belong in the resulting `preflight/sec/report.json`.
The cohort freeze precedes the full acquisition, so any shortfall or parser
disagreement must be reported rather than silently changing the frame.

The SEC requests use the contact identity supplied for this project. That
identity is held in the process environment and is not retained in these
artifacts. No model-provider calls are part of acquisition.
