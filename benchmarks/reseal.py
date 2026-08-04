"""Provider-free resealing of retained normalized benchmark pools."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .build.hmda_pool import reseal_normalized_pool


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="domain", required=True)
    hmda = subparsers.add_parser("hmda")
    hmda.add_argument("--pool", required=True, type=Path)
    args = parser.parse_args(argv)
    report = reseal_normalized_pool(args.pool)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
