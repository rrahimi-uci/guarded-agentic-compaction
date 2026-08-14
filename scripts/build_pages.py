#!/usr/bin/env python3
"""Build and validate the static GitHub Pages site without network access."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"

FIGURES = (
    "demo_suite.png",
    "family_reductions.png",
    "gac_aha_example.png",
    "gate_support.png",
    "live_efficiency.png",
    "natural_live_comparison.png",
    "paired_test.png",
    "pilot_ablation.png",
    "portfolio_selection.png",
)
DOWNLOADS = {
    ROOT / "paper" / "compiling-recurrent-agent-workflows-into-guarded-programs.pdf":
        "compiling-recurrent-agent-workflows.pdf",
    # The 27-slide seminar deck was removed; one deck ships, and it carries the
    # seminar design system. See paper/slides/gac-template-map.json.
    ROOT / "paper" / "slides" / "compiling-recurrent-agent-workflows-into-guarded-programs-detailed.pptx":
        "gac-technical-review.pptx",
}


class PageInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.links: list[str] = []
        self.images_without_alt: list[str] = []
        self.title_depth = 0
        self.title = ""
        self.has_description = False
        self.h1_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(str(values["id"]))
        if tag == "a" and values.get("href"):
            self.links.append(str(values["href"]))
        if tag == "img" and not (values.get("alt") or "").strip():
            self.images_without_alt.append(str(values.get("src", "<unknown>")))
        if tag == "meta" and values.get("name") == "description" and values.get("content"):
            self.has_description = True
        if tag == "title":
            self.title_depth += 1
        if tag == "h1":
            self.h1_count += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.title_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.title_depth:
            self.title += data


def safe_output(path: Path) -> Path:
    resolved = path.resolve()
    if resolved == ROOT or ROOT not in resolved.parents:
        raise SystemExit(f"refusing output outside repository: {resolved}")
    if resolved.name not in {"_site", "site-build"}:
        raise SystemExit("output directory must be named _site or site-build")
    return resolved


def validate_site(output: Path) -> None:
    errors: list[str] = []
    html_files = sorted(output.glob("*.html"))
    if not html_files:
        errors.append("no HTML pages were built")

    parsed: dict[Path, PageInspector] = {}
    for page in html_files:
        inspector = PageInspector()
        inspector.feed(page.read_text(encoding="utf-8"))
        parsed[page] = inspector
        duplicates = sorted({value for value in inspector.ids if inspector.ids.count(value) > 1})
        if duplicates:
            errors.append(f"{page.name}: duplicate ids {duplicates}")
        if not inspector.title.strip():
            errors.append(f"{page.name}: missing title")
        if not inspector.has_description:
            errors.append(f"{page.name}: missing meta description")
        if inspector.h1_count != 1:
            errors.append(f"{page.name}: expected one h1, found {inspector.h1_count}")
        if inspector.images_without_alt:
            errors.append(f"{page.name}: images without alt {inspector.images_without_alt}")

    for page, inspector in parsed.items():
        for raw_link in inspector.links:
            parts = urlsplit(raw_link)
            if parts.scheme or parts.netloc or raw_link.startswith(("mailto:", "#")):
                continue
            target = unquote(parts.path)
            candidate = (page.parent / target).resolve() if target else page.resolve()
            if candidate.is_dir():
                candidate /= "index.html"
            if not candidate.exists():
                errors.append(f"{page.name}: broken local link {raw_link}")
                continue
            if parts.fragment and candidate.suffix == ".html":
                target_parser = parsed.get(candidate)
                if target_parser and parts.fragment not in target_parser.ids:
                    errors.append(f"{page.name}: missing fragment target {raw_link}")

    if errors:
        raise SystemExit("site validation failed:\n- " + "\n- ".join(errors))
    print(f"Pages site valid: {len(html_files)} pages, {len(list(output.rglob('*')))} paths")


def ensure_benchmark_explorer_current() -> None:
    """Fail closed when the benchmark explorer drifts from the evidence it reports."""

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import build_benchmark_explorer as generator

    matrix = generator.load(generator.MATRIX)
    validation = generator.load(generator.MULTIDOMAIN)
    rows = generator.rows_from_matrix(matrix) + generator.rows_from_multidomain(validation)
    generator.verify_totals(matrix, rows)
    generator.attach_profiles(rows)
    content = generator.attach_content(rows, matrix)
    generator.verify_content(content, matrix)
    if generator.OUTPUT.read_text(encoding="utf-8") != generator.render(matrix, rows, content):
        raise SystemExit(
            "benchmarks/explorer/index.html is stale relative to paper/results/; "
            "regenerate it with: python scripts/build_benchmark_explorer.py"
        )


def ensure_paper_page_current() -> None:
    """Fail closed when site/method.html drifts from the result artifacts it quotes.

    The method page prints selective-risk bounds and per-family economics straight out of
    paper/results/, so deploying a copy that no longer matches those files would publish
    numbers the repository cannot support.
    """

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import build_paper_page as generator

    expected = generator.render(
        generator.verify_admission(generator.load("results/admission_register.json")),
        generator.verify_cache(generator.load("results/cache_accounting.json")),
        generator.verify_families(generator.load("results/github_workflow_families/summary.json")),
    )
    if (SITE / "method.html").read_text(encoding="utf-8") != expected:
        raise SystemExit(
            "site/method.html is stale relative to paper/results/; "
            "regenerate it with: python scripts/build_paper_page.py"
        )


def ensure_article_page_current() -> None:
    """Fail closed when site/article.html drifts from the manuscript it renders.

    The article page is generated from paper/tex/ by scripts/build_article_page.py, which
    needs pandoc.  This job installs only pyyaml, so re-rendering here is not an option;
    instead the generator stamps a digest of its sources into the page and this check
    recomputes that digest with the standard library alone.  Publishing an article page
    that no longer matches the manuscript would misattribute prose to the paper, so a
    mismatch stops the deploy rather than shipping quietly.
    """

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import build_article_page as generator

    page = SITE / "article.html"
    if not page.exists():
        raise SystemExit("missing site source: site/article.html")
    stamped = re.search(
        r'<meta name="gac-article-sources" content="([0-9a-f]{64})">',
        page.read_text(encoding="utf-8"),
    )
    if stamped is None:
        raise SystemExit("site/article.html carries no source digest; regenerate it")
    if stamped.group(1) != generator.source_digest():
        raise SystemExit(
            "site/article.html is stale relative to paper/tex/; "
            "regenerate it with: python scripts/build_article_page.py"
        )


def build(output: Path) -> None:
    ensure_paper_page_current()
    ensure_article_page_current()
    ensure_benchmark_explorer_current()
    required = [SITE / "index.html", SITE / "assets" / "css" / "styles.css"]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"missing site sources: {missing}")
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(SITE, output)

    figure_dir = output / "assets" / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    for name in FIGURES:
        source = ROOT / "paper" / "generated_figures" / name
        if not source.exists():
            raise SystemExit(f"missing publication figure: {source.relative_to(ROOT)}")
        shutil.copy2(source, figure_dir / name)

    # The explorer is a standalone, self-contained page that lives with the benchmark
    # suite it describes; publishing a copy makes it browsable from the site without
    # giving it a second source of truth.
    explorer_source = ROOT / "benchmarks" / "explorer" / "index.html"
    explorer_dir = output / "benchmarks" / "explorer"
    explorer_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(explorer_source, explorer_dir / "index.html")

    download_dir = output / "downloads"
    download_dir.mkdir(parents=True, exist_ok=True)
    for source, name in DOWNLOADS.items():
        if not source.exists():
            raise SystemExit(f"missing publication download: {source.relative_to(ROOT)}")
        shutil.copy2(source, download_dir / name)

    validate_site(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    build(safe_output(args.output))


if __name__ == "__main__":
    main()
