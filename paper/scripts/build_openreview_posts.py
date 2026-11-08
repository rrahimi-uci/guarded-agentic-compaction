"""Split the reviewed response draft into one plain-text file per OpenReview post.

Reads ``paper/iclr/notes/review_response_2026-11-06.md`` (the blocks under ``### Post:`` headings),
writes ``paper/iclr/upload/posts/NN_<name>.md`` and refuses any block above the character limit.
The PDF to upload is ``paper/iclr/upload/GAC_ICLR2027_revised.pdf`` (a copy of ``build/main.pdf``).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "paper/iclr/notes/review_response_2026-11-06.md"
OUT = ROOT / "paper/iclr/upload/posts"
LIMIT = 4500
ORDER = ["global", "r1_part1", "r1_part2", "r2_part1", "r2_part2", "r3_part1", "r3_part2"]


def blocks(text: str) -> list[tuple[str, str]]:
    out = []
    for chunk in re.split(r"(?m)^### Post: ", text)[1:]:
        head, body = chunk.split("\n", 1)
        out.append((head.strip(), re.split(r"\n## ", body)[0].strip() + "\n"))
    return out


def main() -> int:
    found = blocks(SOURCE.read_text(encoding="utf-8"))
    if len(found) != len(ORDER):
        print(f"expected {len(ORDER)} posts, found {len(found)}", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.md"):
        old.unlink()
    for i, (name, (head, body)) in enumerate(zip(ORDER, found)):
        if len(body.strip()) > LIMIT:
            print(f"{head}: {len(body.strip())} characters exceeds {LIMIT}", file=sys.stderr)
            return 1
        (OUT / f"{i:02d}_{name}.md").write_text(body, encoding="utf-8")
        print(f"{i:02d}_{name}.md  {len(body.strip()):5d} chars  {head}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
