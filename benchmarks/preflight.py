"""Repository entry point for the installable benchmark preflight."""

from agent_compaction.benchmarking.preflight import *  # noqa: F403
from agent_compaction.benchmarking.preflight import main


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
