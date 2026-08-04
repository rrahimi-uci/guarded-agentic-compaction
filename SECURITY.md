# Security policy

## Supported versions

The latest released `0.x` version receives security fixes. The package is research-alpha
software: live deployment still requires application-specific effect review, shadow
evidence, a kill switch, and rollback.

## Reporting a vulnerability

Report vulnerabilities privately through the repository host's security-advisory feature.
Do not include credentials, production traces, personal data, or exploit payloads in a
public issue. Include the affected version, execution mode, effect catalog entry, minimal
reproduction, and whether an external effect was committed.

## Security boundaries

Unknown tools, writes, approvals, unsupported SDK surfaces, invalid modes, manifest drift,
and unverifiable signed artifacts fail closed. HMAC registry signing detects tampering but
is not a public-key software-supply-chain signature. Trace storage and deletion policy are
owned by the deploying application.
