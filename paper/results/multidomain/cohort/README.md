# SEC preflight candidate frame

The provider-free SEC acquisition began on 2026-10-15 from the SEC's
[`company_tickers.json`](https://www.sec.gov/files/company_tickers.json).
`company_tickers.source.json` preserves the exact response; its SHA-256 and
the candidate-file SHA-256 are recorded in `sec-source.json`. Before issuer
acquisition, we selected the first 700 distinct CIKs in source order and
froze them in `sec-ciks.json`. No failed issuer is replaced outside that list.

This is a convenience frame of ticker-listed issuers, not a random or
representative sample of SEC filers. The builder inspects candidates in this
fixed order until it has 520 complete groups, then retains 420. The initial
live acquisition reached 520 complete groups but failed to select 420 because
the implementation treated the 10% hard-state minimum as exactly 10% and
found only 363 ordinary groups. The selection rule was amended after this
failure to fill those 15 slots from already qualified hard-state groups. The
candidate list was unchanged; the [amendment record](../preflight/sec/acquisition_amendment.json)
is part of the result. This cohort must not be described as confirmatory
pre-registered selection.

The SEC requests use the contact identity supplied for this project. That
identity is held in the process environment and is not retained in these
artifacts. No model-provider calls are part of acquisition.
