"""Provider-free acquisition entry point for the real-record benchmark pools."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Sequence

from .build.hmda_pool import build_pool as build_hmda_pool
from .build.nvd_subset import build_subset as build_nvd_subset
from .build.sec_pool import build_pool as build_sec_pool
from .build.vulnerability_pool import build_pool as build_vulnerability_pool
from .fetch.hmda import fetch_public_lar_csv
from .fetch.vulnerability import fetch_kev, fetch_osv_archive


def _load_ciks(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    try:
        parsed = json.loads(text)
        values = parsed.values() if isinstance(parsed, dict) else parsed
        return [
            str(item.get("cik_str") or item.get("cik") or item.get("cikStr"))
            if isinstance(item, dict)
            else str(item)
            for item in values
        ]
    except json.JSONDecodeError:
        return [line.strip() for line in text.splitlines() if line.strip()]


def _vulnerability(args: argparse.Namespace) -> dict[str, object]:
    osv = fetch_osv_archive("PyPI", args.cache, offline=args.offline)
    kev = fetch_kev(args.cache, offline=args.offline)
    with tempfile.TemporaryDirectory(prefix="agent-compaction-vulnerability-") as temporary:
        candidate = Path(temporary)
        build_vulnerability_pool(
            osv_zip=Path(osv.path),
            osv_digest=osv.sha256,
            kev_json=Path(kev.path),
            kev_digest=kev.sha256,
            cache_dir=args.cache,
            output_dir=candidate,
            minimum_groups=args.minimum_groups,
            offline=args.offline,
        )
        nvd_path = args.out / "nvd_subset.json"
        build_nvd_subset(
            cases_path=candidate / "cases.jsonl",
            cache_dir=args.cache,
            output_path=nvd_path,
            offline=args.offline,
        )
    return build_vulnerability_pool(
        osv_zip=Path(osv.path),
        osv_digest=osv.sha256,
        kev_json=Path(kev.path),
        kev_digest=kev.sha256,
        cache_dir=args.cache,
        output_dir=args.out,
        nvd_subset=nvd_path,
        minimum_groups=args.minimum_groups,
        offline=args.offline,
    )


def _hmda(args: argparse.Namespace) -> dict[str, object]:
    inputs = []
    urls: dict[int, str] = {}
    for year in args.year:
        record = fetch_public_lar_csv(
            year=year,
            states=tuple(args.state),
            cache_dir=args.cache,
            offline=args.offline,
        )
        inputs.append((year, Path(record.path)))
        urls[year] = record.url
    return build_hmda_pool(
        inputs,
        args.out,
        minimum_groups=args.minimum_groups,
        source_urls=urls,
    )


def _sec(args: argparse.Namespace) -> dict[str, object]:
    return build_sec_pool(
        ciks=_load_ciks(args.ciks),
        cache_dir=args.cache,
        output_dir=args.out,
        minimum_groups=args.minimum_groups,
        offline=args.offline,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="domain", required=True)

    def common(name: str) -> argparse.ArgumentParser:
        command = subparsers.add_parser(name)
        command.add_argument("--cache", type=Path, default=Path("benchmarks/.cache"))
        command.add_argument("--out", type=Path, required=True)
        command.add_argument("--minimum-groups", type=int, default=420)
        command.add_argument("--offline", action="store_true")
        return command

    vulnerability = common("vulnerability")
    vulnerability.set_defaults(handler=_vulnerability)

    hmda = common("hmda")
    hmda.add_argument("--year", type=int, action="append", required=True)
    hmda.add_argument("--state", action="append", required=True)
    hmda.set_defaults(handler=_hmda)

    sec = common("sec")
    sec.add_argument("--ciks", type=Path, required=True)
    sec.set_defaults(handler=_sec)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.minimum_groups < 1:
        raise SystemExit("--minimum-groups must be positive")
    report = args.handler(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
