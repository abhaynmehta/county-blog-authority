"""Digital hygiene: does what is live match what the registry says?

Fetches County pages and checks the facts on them against the registry.
Prices change and that is expected — but areas and unit plans do not, so a
live page showing a carpet area that is not a registered configuration is a
defect regardless of when the page was written.

Uses stdlib only. A page rendered entirely by JavaScript will return little
text; `text_chars` in the result makes that visible rather than silently
reporting a clean page.
"""

from __future__ import annotations

import gzip
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from .truth_layer import TruthLayer, load_truth_layer, raw_site_urls

USER_AGENT = "CountyGroup-HygieneCheck/1.0"
TIMEOUT = 20


@dataclass
class PageFindings:
    url: str
    status: Optional[int] = None
    error: Optional[str] = None
    text_chars: int = 0
    title: Optional[str] = None
    has_canonical: bool = False
    has_jsonld: bool = False
    has_meta_description: bool = False
    findings: list[dict] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status is not None and 200 <= self.status < 300


def _fetch(url: str) -> tuple[Optional[int], str, Optional[str]]:
    """Return (status, html, error)."""
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"}
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read()
            if response.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            return response.status, raw.decode("utf-8", errors="replace"), None
    except urllib.error.HTTPError as exc:
        return exc.code, "", None
    except Exception as exc:
        return None, "", str(exc)[:160]


def _visible_text(html: str) -> str:
    body = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    return " ".join(re.sub(r"(?s)<[^>]+>", " ", body).split())


def check_page(url: str, layer: Optional[TruthLayer] = None) -> PageFindings:
    """Check one live page against the registry."""
    layer = layer or load_truth_layer()
    status, html, error = _fetch(url)
    page = PageFindings(url=url, status=status, error=error)
    if not html:
        return page

    text = _visible_text(html)
    page.text_chars = len(text)
    page.has_canonical = bool(re.search(r'(?i)<link[^>]+rel=["\']?canonical', html))
    page.has_jsonld = bool(re.search(r'(?i)application/ld\+json', html))
    page.has_meta_description = bool(re.search(r'(?i)<meta[^>]+name=["\']?description', html))

    title_match = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    page.title = " ".join(title_match.group(1).split()) if title_match else None

    def add(kind: str, severity: str, detail: str, fix: str, owner: str = "AGO"):
        page.findings.append({
            "type": kind, "severity": severity,
            "detail": detail, "fix": fix, "owner": owner,
        })

    # Technical hygiene.
    if not page.has_canonical:
        add("canonical", "medium", "No canonical link element",
            "Add <link rel=\"canonical\"> pointing at the page's own URL")
    if not page.has_jsonld:
        add("schema", "medium", "No JSON-LD structured data",
            "Deploy the schema the pipeline generates for this page")
    if not page.has_meta_description:
        add("meta", "medium", "No meta description",
            "Add a 120-160 character meta description")
    if page.title and len(page.title) > 60:
        add("title", "low", f"Title tag is {len(page.title)} characters",
            "Shorten to 60 characters or fewer so it does not truncate")

    # A page that renders its content in the browser gives us almost no text
    # to check. Say so rather than reporting a clean page.
    if page.text_chars < 500:
        add("rendering", "low",
            f"Only {page.text_chars} characters of text in the HTML source",
            "Page may be JavaScript-rendered; verify manually or crawl with a "
            "headless browser", owner="INTERNAL")
        return page

    _check_facts(page, text, layer, add)
    return page


def _is_table_header(text: str, position: int) -> bool:
    """True when "carpet area" here is a column heading, not a label.

    Flattening an HTML table puts the headings ("Super Area Built-up Area
    Carpet Area") immediately before the row's values, so the first number
    after "Carpet Area" is the *super* area. A correctly-labelled table
    would otherwise be reported as a wrong figure.
    """
    preceding = text[max(0, position - 80):position].lower()
    return "super area" in preceding or "built-up area" in preceding or "built up area" in preceding


def _near(text: str, name: str, position: int, window: int = 300) -> bool:
    """True when `name` appears within `window` characters of `position`."""
    lo = max(0, position - window)
    hi = min(len(text), position + window)
    return bool(re.search(re.escape(name), text[lo:hi], re.IGNORECASE))


def _check_facts(page: PageFindings, text: str, layer: TruthLayer, add) -> None:
    """Compare the facts on the page against the registry.

    Areas are the strict check: unit plans do not change, so a figure that
    matches no registered configuration is wrong. Prices are volatile and
    only checked for the disclosures that must accompany them.
    """
    for project in layer.projects:
        if not re.search(r"\b" + re.escape(project.name) + r"\b", text, re.IGNORECASE):
            continue

        # Wrong city for a named project.
        if project.city:
            for other in ("Noida", "Greater Noida", "Gurugram", "Ghaziabad", "Delhi"):
                if other.lower() == project.city.lower():
                    continue
                if {other.lower(), project.city.lower()} == {"gurgaon", "gurugram"}:
                    continue
                if re.search(
                    re.escape(project.name) + r"[^.]{0,40}?\bin\s+" + re.escape(other) + r"\b",
                    text, re.IGNORECASE,
                ):
                    add("location", "critical",
                        f"{project.name} shown as being in {other}; "
                        f"the registry says {project.city}",
                        f"Correct the location to {project.city}", owner="AGO")
                    break

        # Carpet areas. Unit plans are immutable, so this is a hard check.
        #
        # The figure must sit near the project name. Every County page lists
        # the whole portfolio in its navigation, so mere co-occurrence would
        # attribute one project's areas to every other project named on the
        # page — which produced 15 false criticals on the first run.
        registered = set(project.carpet_areas())
        unverified = set(project.unverified_carpet_areas())
        if registered:
            for match in re.finditer(
                r"carpet\s+area\b(?![^.]{0,40}\b(?:super|built[- ]?up)\b)[^.\n]{0,22}?([\d,]{3,7})\s*(?:sq\.?\s*ft|square\s+feet)",
                text, re.IGNORECASE,
            ):
                try:
                    stated = int(match.group(1).replace(",", ""))
                except ValueError:
                    continue
                if _is_table_header(text, match.start()):
                    continue
                if any(abs(stated - r) <= 5 for r in registered):
                    continue
                if not _near(text, project.name, match.start(), window=300):
                    continue
                if any(abs(stated - u) <= 5 for u in unverified):
                    add("area", "high",
                        f"{project.name} carpet area {stated} sq ft is live but "
                        f"has no source document on file",
                        "Obtain the price list covering this unit, or remove the figure",
                        owner="INTERNAL")
                    continue
                add("area", "critical",
                    f"{project.name} carpet area {stated} sq ft is live and matches "
                    f"no registered configuration "
                    f"(registered: {sorted(registered)})",
                    "Correct the figure to a registered carpet area", owner="AGO")

    # Any price on the page must carry its effective date, since prices move.
    if re.search(r"(?:₹|Rs\.?)\s*[\d,]+(?:\.\d+)?\s*(?:Cr|Lakh|L\b)", text, re.IGNORECASE):
        if not re.search(r"(?i)w\.e\.f|effective\s+from|as\s+of\s+\d|subject\s+to\s+change", text):
            add("pricing", "high",
                "A price is shown with no effective date or 'subject to change' note",
                "Add the effective date and a subject-to-change line beside the price",
                owner="AGO")


def run(urls: Optional[list[str]] = None) -> dict:
    """Check every registered County URL, or the ones given."""
    layer = load_truth_layer()
    targets = urls or raw_site_urls()
    pages = [check_page(url, layer) for url in targets]

    findings = [
        {**f, "url": p.url}
        for p in pages for f in p.findings
    ]
    by_severity = {
        level: sum(1 for f in findings if f["severity"] == level)
        for level in ("critical", "high", "medium", "low")
    }

    return {
        "checked_at": date.today().isoformat(),
        "pages_checked": len(pages),
        "unreachable": sum(1 for p in pages if not p.ok),
        "total_findings": len(findings),
        "by_severity": by_severity,
        "pages": [
            {
                "url": p.url, "status": p.status, "error": p.error,
                "title": p.title, "text_chars": p.text_chars,
                "has_canonical": p.has_canonical, "has_jsonld": p.has_jsonld,
                "has_meta_description": p.has_meta_description,
                "findings": p.findings,
            }
            for p in pages
        ],
        "findings": sorted(
            findings,
            key=lambda f: ("critical", "high", "medium", "low").index(f["severity"]),
        ),
    }
