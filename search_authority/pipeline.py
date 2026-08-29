"""End-to-end blog pipeline: audit → schema → package."""

import json
import os
from pathlib import Path

from .content_auditor import audit_text, audit_file
from .history import record as record_history
from .models import Owner, ContentAnalysis
from .report import (
    generate_markdown_report,
    generate_json_report,
    generate_agency_handoff,
)
from .schema import (
    generate_blog_schema,
    generate_breadcrumb_schema,
    schemas_to_jsonld,
)


def run_pipeline(
    input_path: str | None = None,
    text: str | None = None,
    slug: str = "blog",
    output_dir: str = "output",
    url_base: str = "https://countygroup.in/blog",
    date_published: str | None = None,
    strict: bool = False,
) -> dict:
    """Run the full audit → schema → package pipeline.

    Args:
        input_path: Path to DOCX or markdown file.
        text: Raw text content (used if input_path is None).
        slug: URL slug for the blog post.
        output_dir: Directory to write output files.
        url_base: Base URL for schema generation.
        date_published: The post's real publication date (ISO). Required for
            schema. Auditing must never invent one — a rerun would otherwise
            rewrite publication history and put a false date in structured
            data.
        strict: When True, content that fails a gate gets diagnostics only.
            No schema and no agency package, so "audited" can never be
            mistaken for "approved".

    Returns:
        dict with keys: audit_result, schema, output_files
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Stage 1: Audit
    if input_path:
        result = audit_file(input_path)
        source_name = Path(input_path).stem
    elif text:
        result = audit_text(text)
        source_name = slug
    else:
        raise ValueError("Provide input_path or text")

    if slug == "blog":
        slug = _slugify(source_name)

    # Read source text for headline extraction
    if input_path and not text:
        p = Path(input_path)
        if p.suffix == ".docx":
            text = ""
        else:
            text = p.read_text(encoding="utf-8")

    headline = _extract_headline(result, text or "")

    # Content that failed a gate must not receive a CMS-looking package.
    blocked = strict and not result.publishable
    if blocked:
        out = out / "failed-audits"
        out.mkdir(parents=True, exist_ok=True)

    # Stage 2: Schema — only for content that passed, and only with a real
    # publication date supplied by the caller.
    combined_schema = None
    if not blocked and date_published:
        blog_schema = generate_blog_schema(
            headline=headline,
            description=result.metadata.meta_description or f"County Group blog: {headline}",
            url=f"{url_base}/{slug}",
            date_published=date_published,
        )
        breadcrumb = generate_breadcrumb_schema([
            {"name": "Home", "url": "https://countygroup.in/"},
            {"name": "Blog", "url": "https://countygroup.in/blog/"},
            {"name": headline},
        ])
        combined_schema = schemas_to_jsonld(blog_schema, breadcrumb)

    # Every run is recorded before packaging, pass or fail. The value of the
    # ledger comes from it being complete: a history that only kept successes
    # could not show that a problem keeps coming back.
    try:
        record_history(result, slug=slug, source=input_path)
    except OSError:
        # A read-only filesystem must not stop an audit from completing.
        pass

    # Stage 3: Package
    files = {}

    # Audit report (markdown)
    report_md = generate_markdown_report(result)
    report_path = out / f"{slug}-audit-report.md"
    report_path.write_text(report_md, encoding="utf-8")
    files["audit_report_md"] = str(report_path)

    # Audit report (JSON)
    report_json = generate_json_report(result)
    json_path = out / f"{slug}-audit-report.json"
    json_path.write_text(report_json, encoding="utf-8")
    files["audit_report_json"] = str(json_path)

    # Schema
    if combined_schema:
        schema_path = out / f"{slug}-schema.json"
        schema_path.write_text(combined_schema, encoding="utf-8")
        files["schema"] = str(schema_path)

    # ROI handoff
    roi = generate_agency_handoff([result], Owner.ROI)
    roi_path = out / f"{slug}-roi-handoff.md"
    roi_path.write_text(roi, encoding="utf-8")
    files["roi_handoff"] = str(roi_path)

    # AGO handoff
    ago = generate_agency_handoff([result], Owner.AGO)
    ago_path = out / f"{slug}-ago-handoff.md"
    ago_path.write_text(ago, encoding="utf-8")
    files["ago_handoff"] = str(ago_path)

    return {
        "slug": slug,
        "publishable": result.publishable,
        "blocked": blocked,
        "schema_emitted": combined_schema is not None,
        "schema_skipped_reason": (
            "gates failed" if blocked
            else None if combined_schema
            else "no date_published supplied"
        ),
        "score": result.score,
        "issue_count": len(result.issues),
        "critical_count": sum(1 for i in result.issues if i.severity.name == "CRITICAL"),
        "gates": {g.gate_name: g.status.value for g in result.gates},
        "output_files": files,
    }


def _extract_headline(result: ContentAnalysis, text: str) -> str:
    if result.metadata.title:
        return result.metadata.title
    for line in text.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return "Untitled Blog"


def _slugify(name: str) -> str:
    import re
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return s[:80].strip("-")


def _today() -> str:
    from datetime import date
    return date.today().isoformat()
