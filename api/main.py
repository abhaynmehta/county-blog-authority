"""FastAPI service exposing the audit engine over HTTP.

This is the boundary that lets a browser do what previously needed a
terminal. The engine itself is unchanged and still deterministic — the API
is a thin transport layer over `search_authority`, deliberately holding no
audit logic of its own, so the CLI and the dashboard can never disagree.

Run locally:
    uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from search_authority import __version__ as engine_version
from search_authority.cannibalization import analyse_corpus
from search_authority.content_auditor import audit_text
from search_authority.dashboard import collect_data
from search_authority.competitors import benchmark, discover_articles
from search_authority.history import storage_status, summary as history_summary
from search_authority.hygiene import run as run_hygiene
from search_authority.reports import compare, explain, load_leads, load_rows
from search_authority.social import social_report
from search_authority.models import Severity
from search_authority.schema import (
    generate_blog_schema, generate_breadcrumb_schema, schemas_to_jsonld,
)
from search_authority.truth_layer import load_truth_layer, registry_report

app = FastAPI(
    title="County Group Blog Authority API",
    version=engine_version,
    description="Deterministic content audit for County Group real estate content.",
)

# The dashboard is served from a different origin in development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

MAX_CONTENT_CHARS = 200_000


# ── Schemas ───────────────────────────────────────────────────────────────

class AuditRequest(BaseModel):
    content: str = Field(..., description="Raw blog text or markdown")
    slug: str = Field("untitled", description="Slug used for schema URLs")


class SchemaRequest(AuditRequest):
    # No default. Auditing must never invent a publication date: a rerun
    # would rewrite the post's history and put a false date into structured
    # data, which Google's structured-data policy treats as misrepresentation.
    date_published: str = Field(..., description="Real publication date, ISO (YYYY-MM-DD)")
    date_modified: Optional[str] = Field(None, description="Set only after an approved visible change")
    canonical_url: Optional[str] = Field(None, description="The page's canonical URL")


class IssueOut(BaseModel):
    issue_id: str
    severity: str
    owner: str
    category: str
    summary: str
    paragraph: Optional[int] = None
    quoted_text: Optional[str] = None
    verified_fact: Optional[str] = None
    source: Optional[str] = None
    recommended_action: str
    acceptance_test: str
    rule: Optional[str] = None


class GateOut(BaseModel):
    gate: str
    status: str
    details: str


class MetaTagsOut(BaseModel):
    title: Optional[str] = None
    title_length: int = 0
    meta_description: Optional[str] = None
    meta_description_length: int = 0
    keywords: Optional[str] = None
    category: Optional[str] = None
    image_alt: Optional[str] = None
    image_filename: Optional[str] = None
    faq_schema_present: bool = False
    h1: Optional[str] = None
    headings_count: int = 0


class SectionOut(BaseModel):
    index: int
    heading: Optional[str] = None
    word_count: int = 0
    text: str = ""
    issues: list[IssueOut] = []


class AuditResponse(BaseModel):
    slug: str
    score: int
    publishable: bool
    word_count: int
    gates: list[GateOut]
    issues: list[IssueOut]
    counts: dict
    meta_tags: Optional[MetaTagsOut] = None
    sections: list[SectionOut] = []
    audited_at: str


# ── Helpers ───────────────────────────────────────────────────────────────

def _to_issue(issue) -> IssueOut:
    return IssueOut(
        issue_id=issue.issue_id,
        severity=issue.severity.value,
        owner=issue.owner.value,
        category=issue.category.value,
        summary=issue.summary,
        paragraph=issue.paragraph,
        quoted_text=issue.claim,
        verified_fact=issue.verified_status,
        source=issue.evidence_source,
        recommended_action=issue.recommended_action,
        acceptance_test=issue.acceptance_test,
        rule=issue.google_rule or issue.editorial_rule,
    )


def _split_sections(content: str, issues: list, meta) -> list[SectionOut]:
    """Split content into sections by heading for section-level analysis."""
    lines = content.split("\n")
    sections: list[dict] = []
    current: dict = {"heading": None, "lines": [], "index": 0}

    heading_re = re.compile(r"^(?:#{1,6}\s+|(\d+)\.\s+)(.+)$")

    for line in lines:
        m = heading_re.match(line.strip())
        if m:
            if current["lines"]:
                sections.append(current)
            current = {
                "heading": m.group(2).strip() if m.group(2) else line.strip(),
                "lines": [line],
                "index": len(sections),
            }
        else:
            current["lines"].append(line)

    if current["lines"]:
        sections.append(current)

    result = []
    for sec in sections:
        text = "\n".join(sec["lines"])
        words = len(text.split())
        sec_issues = []
        for issue in issues:
            if issue.paragraph:
                para_text = content.split("\n\n")[issue.paragraph - 1] if issue.paragraph <= len(content.split("\n\n")) else ""
                if para_text and para_text.strip() in text:
                    sec_issues.append(_to_issue(issue))
        result.append(SectionOut(
            index=sec["index"],
            heading=sec["heading"],
            word_count=words,
            text=text[:2000],
            issues=sec_issues,
        ))

    return result


def _run_audit(content: str, slug: str) -> AuditResponse:
    if not content.strip():
        raise HTTPException(422, "content is empty")
    if len(content) > MAX_CONTENT_CHARS:
        raise HTTPException(
            413, f"content exceeds {MAX_CONTENT_CHARS} characters"
        )

    result = audit_text(content)
    m = result.metadata

    meta_tags = MetaTagsOut(
        title=m.title,
        title_length=m.title_length,
        meta_description=m.meta_description,
        meta_description_length=m.meta_description_length,
        keywords=m.keywords,
        category=m.category,
        image_alt=m.image_alt,
        image_filename=m.image_filename,
        faq_schema_present=bool(m.faq_schema),
        h1=m.h1,
        headings_count=len(m.headings),
    )

    sections = _split_sections(content, result.issues, m)

    return AuditResponse(
        slug=slug,
        score=result.score,
        publishable=result.publishable,
        word_count=result.word_count,
        gates=[GateOut(gate=g.gate_name, status=g.status.value, details=g.details)
               for g in result.gates],
        issues=[_to_issue(i) for i in result.issues],
        counts={
            sev.value: sum(1 for i in result.issues if i.severity == sev)
            for sev in Severity
        },
        meta_tags=meta_tags,
        sections=sections,
        audited_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


# ── Routes ────────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"])
def health() -> dict:
    """Liveness probe. Confirms the engine and registry both load."""
    layer = load_truth_layer()
    return {
        "status": "ok",
        "engine_version": engine_version,
        "projects_loaded": len(layer.projects),
        "claims_loaded": len(layer.claims),
        "registry_errors": layer.load_errors,
        "storage": storage_status(),
    }


@app.post("/audit", response_model=AuditResponse, tags=["audit"])
def audit(request: AuditRequest) -> AuditResponse:
    """Audit pasted content. The same engine the CLI uses."""
    return _run_audit(request.content, request.slug)


@app.post("/audit/file", tags=["audit"])
async def audit_file_upload(file: UploadFile = File(..., description="DOCX or text file")) -> AuditResponse:
    """Audit an uploaded DOCX or text file."""
    import tempfile

    suffix = Path(file.filename or "blog.txt").suffix or ".txt"
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    handle.write(await file.read())
    handle.close()
    path = Path(handle.name)
    try:
        from search_authority.content_auditor import audit_file as _audit_file
        result = _audit_file(str(path))
        m = result.metadata
        content = path.read_text(encoding="utf-8", errors="replace") if suffix != ".docx" else ""
        if suffix == ".docx":
            try:
                from search_authority.content_auditor import _read_docx
                content = _read_docx(path)
            except Exception:
                content = ""

        meta_tags = MetaTagsOut(
            title=m.title, title_length=m.title_length,
            meta_description=m.meta_description,
            meta_description_length=m.meta_description_length,
            keywords=m.keywords, category=m.category,
            image_alt=m.image_alt, image_filename=m.image_filename,
            faq_schema_present=bool(m.faq_schema),
            h1=m.h1, headings_count=len(m.headings),
        )
        sections = _split_sections(content, result.issues, m) if content else []
        slug = Path(file.filename or "unknown").stem

        return AuditResponse(
            slug=slug, score=result.score, publishable=result.publishable,
            word_count=result.word_count,
            gates=[GateOut(gate=g.gate_name, status=g.status.value, details=g.details)
                   for g in result.gates],
            issues=[_to_issue(i) for i in result.issues],
            counts={sev.value: sum(1 for i in result.issues if i.severity == sev) for sev in Severity},
            meta_tags=meta_tags, sections=sections,
            audited_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
    finally:
        path.unlink(missing_ok=True)


class ReviseRequest(BaseModel):
    content: str = Field(..., description="Original blog text")
    slug: str = Field("untitled", description="Slug for identification")


@app.post("/revise", tags=["audit"])
def revise(request: ReviseRequest) -> dict:
    """Generate section-by-section revision suggestions for a blog.

    Takes the same content as /audit, runs the audit internally, then
    produces actionable revision briefs for each section that has issues.
    """
    if not request.content.strip():
        raise HTTPException(422, "content is empty")
    if len(request.content) > MAX_CONTENT_CHARS:
        raise HTTPException(413, f"content exceeds {MAX_CONTENT_CHARS} characters")

    result = audit_text(request.content)
    m = result.metadata
    sections = _split_sections(request.content, result.issues, m)

    # Build revision briefs per section
    revision_sections = []
    for sec in sections:
        if not sec.issues:
            revision_sections.append({
                "index": sec.index,
                "heading": sec.heading,
                "word_count": sec.word_count,
                "status": "ok",
                "issues": [],
                "suggestions": [],
                "original": sec.text,
            })
            continue

        suggestions = []
        for iss in sec.issues:
            sug = {
                "severity": iss.severity,
                "category": iss.category,
                "problem": iss.summary,
                "fix": iss.recommended_action,
                "done_when": iss.acceptance_test,
            }
            if iss.verified_fact:
                sug["correct_fact"] = iss.verified_fact
            if iss.source:
                sug["source"] = iss.source
            suggestions.append(sug)

        revision_sections.append({
            "index": sec.index,
            "heading": sec.heading,
            "word_count": sec.word_count,
            "status": "needs_revision",
            "issue_count": len(sec.issues),
            "issues": [{"severity": i.severity, "summary": i.summary} for i in sec.issues],
            "suggestions": suggestions,
            "original": sec.text,
        })

    # Corrected meta tags block
    corrected_meta = {}
    if m.title:
        corrected_meta["title"] = m.title
        corrected_meta["title_length"] = m.title_length
        if m.title_length > 60:
            corrected_meta["title_note"] = f"Currently {m.title_length} chars — trim to ≤60"
    if m.meta_description:
        desc = m.meta_description
        corrected_meta["description"] = desc
        corrected_meta["description_length"] = m.meta_description_length
        if m.meta_description_length > 155:
            corrected_meta["description_trimmed"] = desc[:152] + "..."
            corrected_meta["description_note"] = f"Currently {m.meta_description_length} chars — trimmed to ≤155"
    if m.keywords:
        corrected_meta["keywords"] = m.keywords
    if m.category:
        corrected_meta["category"] = m.category
    if m.image_alt:
        corrected_meta["image_alt"] = m.image_alt
    if m.image_filename:
        corrected_meta["image_filename"] = m.image_filename

    # Checklist
    checklist = []
    for iss in result.issues:
        checklist.append({
            "severity": iss.severity.value,
            "category": iss.category.value,
            "action": iss.recommended_action,
            "done_when": iss.acceptance_test,
        })

    return {
        "slug": request.slug,
        "score": result.score,
        "publishable": result.publishable,
        "total_issues": len(result.issues),
        "sections": revision_sections,
        "corrected_meta": corrected_meta,
        "checklist": checklist,
        "revised_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


@app.post("/schema", tags=["audit"])
def schema(request: SchemaRequest) -> dict:
    """Generate JSON-LD for a post, ready for AGO to paste into the CMS.

    Refuses content that fails a gate: structured data must describe a page
    that is fit to publish, and emitting it for failed content invites
    someone to deploy it.
    """
    result = audit_text(request.content)
    if not result.publishable:
        failed = [g.gate_name for g in result.gates if g.status.value == "FAIL"]
        raise HTTPException(409, {
            "message": "Content failed a publication gate; no schema emitted",
            "failed_gates": failed,
            "score": result.score,
        })

    headline = result.metadata.title or result.metadata.h1 or request.slug
    url = request.canonical_url or f"https://www.countygroup.in/blog/{request.slug}"
    blog = generate_blog_schema(
        headline=headline,
        description=result.metadata.meta_description or headline,
        url=url,
        date_published=request.date_published,
    )
    if request.date_modified:
        blog["dateModified"] = request.date_modified
    crumbs = generate_breadcrumb_schema([
        {"name": "Home", "url": "https://www.countygroup.in/"},
        {"name": "Blog", "url": "https://www.countygroup.in/blog/"},
        {"name": headline},
    ])
    return {"slug": request.slug, "canonical_url": url,
            "jsonld": schemas_to_jsonld(blog, crumbs)}


@app.get("/projects", tags=["registry"])
def projects() -> dict:
    """Every project the registry knows, with its verified figures.

    The dashboard shows these beside an audit so a writer can see the
    correct carpet area rather than guessing.
    """
    layer = load_truth_layer()
    return {
        "projects": [
            {
                "name": p.name,
                "slug": p.slug,
                "city": p.city,
                "state": p.state,
                "sector": p.sector,
                "rera_authority": p.rera_authority,
                "rera_number": p.rera_number,
                "promoter": p.promoter,
                "project_page": p.project_page,
                "configurations": p.configurations,
                "unverified_configurations": p.unverified_configurations,
                "prohibited": p.prohibited,
            }
            for p in layer.projects
        ],
        "prohibited_wording": layer.prohibited_wording,
        "load_errors": layer.load_errors,
    }


@app.get("/registry/health", tags=["registry"])
def registry_health() -> dict:
    """Which registry facts are stale or missing a source."""
    return registry_report()


@app.get("/corpus", tags=["corpus"])
def corpus() -> dict:
    """The audited corpus: scores, gates, and per-document issues."""
    try:
        return collect_data()
    except OSError as exc:
        raise HTTPException(503, f"corpus data unavailable: {exc}") from exc


@app.get("/cannibalization", tags=["corpus"])
def cannibalization() -> dict:
    """Pages competing for the same search terms, with the rebuttal text."""
    import yaml

    from search_authority.dashboard import INVENTORY_PATH

    try:
        inventory = yaml.safe_load(INVENTORY_PATH.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise HTTPException(503, f"inventory unavailable: {exc}") from exc

    entries = []
    for section in ("already_processed", "roi_google_docs", "old_agency_local"):
        entries.extend(inventory.get(section) or [])
    return analyse_corpus(entries)


@app.get("/hygiene", tags=["corpus"])
def hygiene() -> dict:
    """Check every live County page against the registry.

    Slow — it fetches ~21 pages — so the console calls it on demand rather
    than on load.
    """
    return run_hygiene()


@app.post("/report/weekly", tags=["reporting"])
async def weekly(
    previous: UploadFile = File(..., description="Last period's export"),
    current: UploadFile = File(..., description="This period's export"),
    leads: Optional[UploadFile] = File(None, description="Lead status export"),
) -> dict:
    """Compare two platform exports and explain what moved.

    Accepts whatever CSV the platform produced — Meta, Google Ads, GA4 and
    Search Console all name their columns differently, so the columns that
    were matched come back in the response for checking.
    """
    import tempfile

    def spool(upload: UploadFile) -> Path:
        suffix = Path(upload.filename or "export.csv").suffix or ".csv"
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        handle.write(upload.file.read())
        handle.close()
        return Path(handle.name)

    paths = []
    try:
        previous_path, current_path = spool(previous), spool(current)
        paths += [previous_path, current_path]

        previous_rows, previous_meta = load_rows(previous_path)
        current_rows, current_meta = load_rows(current_path)
        if not previous_rows and not current_rows:
            raise HTTPException(422, {
                "message": "Neither export could be read",
                "previous": previous_meta, "current": current_meta,
            })

        lead_data = None
        if leads is not None and leads.filename:
            leads_path = spool(leads)
            paths.append(leads_path)
            lead_data = load_leads(leads_path)

        comparison = compare(previous_rows, current_rows)
        return {
            "columns_used": current_meta.get("columns_used"),
            "rows_compared": len(comparison["rows"]),
            "totals": comparison["totals"],
            "leads": lead_data,
            "findings": explain(comparison, lead_data, current_meta),
            "campaigns": comparison["rows"],
            "warnings": {
                k: v for k, v in current_meta.items()
                if k in ("mixed_conversion_metrics", "header_row")
            },
        }
    finally:
        for path in paths:
            path.unlink(missing_ok=True)


@app.post("/report/social", tags=["reporting"])
async def social(
    export: UploadFile = File(..., description="Social post export (CSV)"),
    window_days: int = 28,
) -> dict:
    """Analyse social post performance.

    One file, not two: social exports carry a date per post, so the periods
    are split from the data rather than requiring separate uploads.
    """
    import tempfile

    suffix = Path(export.filename or "social.csv").suffix or ".csv"
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    handle.write(export.file.read())
    handle.close()
    path = Path(handle.name)
    try:
        result = social_report(path, split_days=window_days)
        if "error" in result:
            raise HTTPException(422, result)
        return result
    finally:
        path.unlink(missing_ok=True)


@app.get("/competitors", tags=["corpus"])
def competitors(pages: int = 5) -> dict:
    """Benchmark our blog against competitors on the same structural signals.

    Slow — it fetches several pages per site — so the console calls it on
    demand rather than on load.
    """
    import yaml

    config_path = Path("county_context/competitor_blogs.yaml")
    if not config_path.is_file():
        raise HTTPException(503, "county_context/competitor_blogs.yaml is missing")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    own_urls: list[str] = []
    for index in config.get("own") or []:
        own_urls.extend(discover_articles(index, limit=pages))

    rival_urls: list[str] = []
    names: dict[str, str] = {}
    for entry in config.get("competitors") or []:
        # Sites that render their article links in JavaScript cannot be
        # discovered by a plain fetch, so an explicit list stands in.
        found = list(entry.get("articles") or [])[:pages]
        if not found and entry.get("blog"):
            found = discover_articles(entry["blog"], limit=pages)
        rival_urls.extend(found)
        for url in found:
            names[url] = entry["name"]

    result = benchmark(rival_urls, own_urls)
    for page in result["competitor_pages"]:
        page["competitor"] = names.get(page["url"], "unknown")

    # A comparison against one rival must not read as a comparison against
    # the market. Name who was left out and why.
    result["compared_against"] = sorted({
        names[u] for u in names
    })
    result["not_compared"] = [
        {"name": e.get("name"), "reason": e.get("status"), "note": e.get("note")}
        for e in (config.get("unavailable") or [])
    ]

    # Per competitor as well as pooled. A median across four rivals hides
    # which of them is actually driving a gap, and one outlier can make the
    # field look stronger or weaker than it is.
    from collections import defaultdict

    from search_authority.competitors import PageProfile, _stat, SIGNALS

    grouped: dict[str, list[PageProfile]] = defaultdict(list)
    for profile, raw in zip(
        [PageProfile(**{k: v for k, v in p.items() if k != "competitor"})
         for p in result["competitor_pages"]],
        result["competitor_pages"],
    ):
        if profile.ok and profile.word_count:
            grouped[raw["competitor"]].append(profile)

    result["by_competitor"] = {
        name: {
            "pages": len(pages),
            **{signal: _stat(pages, signal) for signal in SIGNALS
               if signal != "schema_types"},
            "schema_types": sorted({t for p in pages for t in p.schema_types}),
        }
        for name, pages in sorted(grouped.items())
    }
    return result


@app.get("/history", tags=["corpus"])
def history() -> dict:
    """Audit history: what is improving, what recurs, what came back.

    An individual audit says what is wrong now. This says whether the same
    mistake keeps returning, which is the part worth raising with an agency.
    """
    return history_summary()


# ── Serve the built console from the same process ─────────────────────────
#
# With web/dist present this is one command on one port: no separate dev
# server, no CORS, and it works offline. `npm run dev` is still the better
# loop while editing the console, but for daily use one process is fewer
# things to get wrong on a machine that is not this one.

_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"

if _DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def console_index() -> FileResponse:
        return FileResponse(_DIST / "index.html")

    @app.get("/{path:path}", include_in_schema=False)
    def console_routes(path: str) -> FileResponse:
        """Serve a real file when one exists, otherwise the console shell.

        Registered last so every API route above still wins; this only ever
        sees paths the API did not claim.
        """
        candidate = (_DIST / path).resolve()
        # Containment check: a crafted path must not escape the dist folder.
        if candidate.is_file() and _DIST.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(_DIST / "index.html")
