"""Competitor blog benchmarking.

The question this answers is not "are their blogs good" but "what do the
pages that outrank us actually do that ours do not". So it measures the same
structural signals on both sides and reports the difference.

Two deliberate limits:

Competitor pages are measured, never treated as sources of fact. A competitor
saying a project has 1,200 sq ft carpet area is not evidence of anything; it
is a claim by a rival. Nothing here feeds the truth registry.

County-specific checks are not applied to competitor content. Their pages are
not bound by our project registry, so running location or carpet-area checks
against them would produce nonsense. Only signals that are universal — length,
structure, schema, citations, images — are compared.

Fetching respects robots.txt. These are public pages being read once for
analysis, but a crawler that ignores robots is a crawler that eventually
causes a problem.
"""

from __future__ import annotations

import gzip
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from dataclasses import dataclass, field
from datetime import date
from statistics import mean, median
from typing import Optional

USER_AGENT = "CountyGroup-Benchmark/1.0"
TIMEOUT = 25

# What the comparison measures. Each is a signal Google's own guidance treats
# as material, or a structural property that affects whether a passage can be
# extracted into an AI answer.
SIGNALS = (
    "word_count", "headings", "h2_count", "schema_types", "faq_present",
    "internal_links", "external_links", "images", "images_with_alt",
    "tables", "lists", "has_author", "has_date",
)


@dataclass
class PageProfile:
    """Structural measurements of one page."""

    url: str
    status: Optional[int] = None
    error: Optional[str] = None
    title: Optional[str] = None
    word_count: int = 0
    headings: int = 0
    h2_count: int = 0
    schema_types: list[str] = field(default_factory=list)
    faq_present: bool = False
    internal_links: int = 0
    external_links: int = 0
    images: int = 0
    images_with_alt: int = 0
    tables: int = 0
    lists: int = 0
    has_author: bool = False
    has_date: bool = False

    @property
    def ok(self) -> bool:
        return self.status is not None and 200 <= self.status < 300

    def as_dict(self) -> dict:
        return {
            "url": self.url, "status": self.status, "error": self.error,
            "title": self.title,
            **{name: getattr(self, name) for name in SIGNALS},
        }


def _robots_allows(url: str) -> tuple[bool, Optional[str]]:
    """Check robots.txt before fetching. Returns (allowed, note)."""
    parts = urllib.parse.urlparse(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    try:
        parser.read()
    except Exception:
        # No reachable robots.txt is not permission to ignore it, but it is
        # also not a prohibition. Proceed and say so.
        return True, "robots.txt unreachable; proceeded"
    return parser.can_fetch(USER_AGENT, url), None


def _fetch(url: str) -> tuple[Optional[int], str, Optional[str]]:
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


def _resolution_base(html: str, url: str) -> str:
    """The URL relative links should resolve against.

    A <base href> overrides the document URL. countygroup.in sets one, and
    ignoring it turns every relative link on the blog index into a 404 that
    is not actually broken — a false finding about the live site.
    """
    match = re.search(r'(?i)<base[^>]+href=["\']([^"\']+)["\']', html)
    return urllib.parse.urljoin(url, match.group(1)) if match else url


def _visible_text(html: str) -> str:
    body = re.sub(r"(?is)<(script|style|noscript|nav|footer|header)[^>]*>.*?</\1>", " ", html)
    return " ".join(re.sub(r"(?s)<[^>]+>", " ", body).split())


def _schema_types(html: str) -> list[str]:
    """Types declared in JSON-LD blocks."""
    found: set[str] = set()
    for block in re.findall(
        r'(?is)<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html
    ):
        try:
            data = json.loads(block.strip())
        except json.JSONDecodeError:
            # Malformed JSON-LD is common; fall back to naming the types.
            found.update(re.findall(r'"@type"\s*:\s*"([^"]+)"', block))
            continue
        for node in _walk(data):
            kind = node.get("@type")
            if isinstance(kind, str):
                found.add(kind)
            elif isinstance(kind, list):
                found.update(k for k in kind if isinstance(k, str))
    return sorted(found)


def _walk(data):
    if isinstance(data, dict):
        yield data
        for value in data.values():
            yield from _walk(value)
    elif isinstance(data, list):
        for item in data:
            yield from _walk(item)


def profile_page(url: str, own_domains: tuple[str, ...] = ()) -> PageProfile:
    """Measure one page's structural signals."""
    allowed, note = _robots_allows(url)
    if not allowed:
        return PageProfile(url=url, error="disallowed by robots.txt")

    status, html, error = _fetch(url)
    page = PageProfile(url=url, status=status, error=error or note)
    if not html:
        return page

    text = _visible_text(html)
    page.word_count = len(text.split())

    title = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    page.title = " ".join(title.group(1).split()) if title else None

    page.headings = len(re.findall(r"(?i)<h[1-6][\s>]", html))
    page.h2_count = len(re.findall(r"(?i)<h2[\s>]", html))
    page.schema_types = _schema_types(html)
    page.faq_present = "FAQPage" in page.schema_types or bool(
        re.search(r"(?i)frequently asked questions", text)
    )

    resolve_from = _resolution_base(html, url)
    host = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
    domains = tuple(d.lower() for d in own_domains) or (host,)
    for href in re.findall(r'(?i)<a[^>]+href=["\']([^"\']+)["\']', html):
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        target = urllib.parse.urlparse(urllib.parse.urljoin(resolve_from, href)).netloc.lower()
        target = target.removeprefix("www.")
        if not target or any(target.endswith(d) for d in domains):
            page.internal_links += 1
        else:
            page.external_links += 1

    images = re.findall(r"(?i)<img[^>]*>", html)
    page.images = len(images)
    page.images_with_alt = sum(
        1 for tag in images if re.search(r'(?i)\balt=["\'][^"\']+["\']', tag)
    )

    page.tables = len(re.findall(r"(?i)<table[\s>]", html))
    page.lists = len(re.findall(r"(?i)<[uo]l[\s>]", html))
    page.has_author = bool(
        re.search(r'(?i)(rel=["\']author|itemprop=["\']author|"author"\s*:|\bby\s+[A-Z][a-z]+)', html)
    )
    page.has_date = bool(
        re.search(r'(?i)(datePublished|dateModified|<time[\s>]|published\s+on)', html)
    )
    return page


def benchmark(competitor_urls: list[str], own_urls: list[str],
              own_domains: tuple[str, ...] = ("countygroup.in", "cleocounty.com")) -> dict:
    """Profile competitor and own pages, then report the difference."""
    competitors = [profile_page(u) for u in competitor_urls]
    own = [profile_page(u, own_domains=own_domains) for u in own_urls]

    reachable_competitors = [p for p in competitors if p.ok and p.word_count]
    reachable_own = [p for p in own if p.ok and p.word_count]

    return {
        "checked_at": date.today().isoformat(),
        "competitor_pages": [p.as_dict() for p in competitors],
        "own_pages": [p.as_dict() for p in own],
        "unreachable": [p.url for p in competitors + own if not p.ok],
        "comparison": _compare(reachable_own, reachable_competitors),
        "findings": _findings(reachable_own, reachable_competitors),
    }


def _stat(pages: list[PageProfile], signal: str) -> Optional[float]:
    values = []
    for page in pages:
        raw = getattr(page, signal)
        if isinstance(raw, bool):
            values.append(1.0 if raw else 0.0)
        elif isinstance(raw, (int, float)):
            values.append(float(raw))
        elif isinstance(raw, list):
            values.append(float(len(raw)))
    return round(median(values), 1) if values else None


def _compare(own: list[PageProfile], rivals: list[PageProfile]) -> dict:
    """Median of each signal on both sides.

    Median rather than mean: one 6,000-word outlier should not make a
    competitor's typical page look twice as long as it is.
    """
    rows = {}
    for signal in SIGNALS:
        if signal == "schema_types":
            continue
        ours, theirs = _stat(own, signal), _stat(rivals, signal)
        rows[signal] = {
            "ours": ours,
            "theirs": theirs,
            "gap": round(ours - theirs, 1) if ours is not None and theirs is not None else None,
        }

    our_schema = {t for p in own for t in p.schema_types}
    their_schema = {t for p in rivals for t in p.schema_types}
    rows["schema_types"] = {
        "ours": sorted(our_schema),
        "theirs": sorted(their_schema),
        "they_have_we_do_not": sorted(their_schema - our_schema),
        "we_have_they_do_not": sorted(our_schema - their_schema),
    }
    return rows


# Signals worth acting on, with what a shortfall actually means.
_MEANING = {
    "word_count": ("Their pages are longer",
                   "Length is not a ranking factor on its own, but it usually "
                   "means they answer more of the question on one page."),
    "external_links": ("They cite more outside sources",
                       "Citations to authorities are what separate a page that "
                       "asserts from one that evidences. This is the clearest "
                       "single gap to close."),
    "images_with_alt": ("They use more described images",
                        "Alt text is both an accessibility requirement and how "
                        "an image gets understood."),
    "h2_count": ("Their pages are more sectioned",
                 "Clear section headings are how a passage gets extracted into "
                 "an AI answer or a featured snippet."),
    "tables": ("They use more comparison tables",
               "Tables are among the most extractable structures on a page."),
    "internal_links": ("They link internally more",
                       "Internal links pass authority and keep a reader moving "
                       "through related pages."),
}


def _findings(own: list[PageProfile], rivals: list[PageProfile]) -> list[dict]:
    if not own or not rivals:
        return [{
            "severity": "high",
            "headline": "Not enough reachable pages to compare",
            "why": f"{len(own)} of ours, {len(rivals)} of theirs could be read.",
            "action": "Check the URLs and whether robots.txt permits fetching.",
        }]

    findings = []
    comparison = _compare(own, rivals)

    for signal, (headline, meaning) in _MEANING.items():
        row = comparison.get(signal, {})
        ours, theirs = row.get("ours"), row.get("theirs")
        if ours is None or theirs is None or theirs == 0:
            continue
        if ours >= theirs:
            continue
        shortfall = round((theirs - ours) / theirs * 100)
        if shortfall < 20:
            continue
        findings.append({
            "severity": "high" if shortfall >= 50 else "medium",
            "headline": f"{headline}: {theirs} against our {ours}",
            "why": meaning,
            "action": f"Close roughly {shortfall}% of this gap on new content first, "
                      f"then work backwards through the corpus.",
        })

    schema = comparison["schema_types"]
    if schema["they_have_we_do_not"]:
        findings.append({
            "severity": "high",
            "headline": "Schema types they deploy and we do not: "
                        + ", ".join(schema["they_have_we_do_not"]),
            "why": "Structured data does not make a page rank, but it governs "
                   "how the result is displayed and what a machine can read "
                   "from it without guessing.",
            "action": "Add the types that describe content actually visible on "
                      "the page. Never add schema for content that is not there.",
        })
    elif schema["we_have_they_do_not"]:
        findings.append({
            "severity": "good",
            "headline": "Schema types we deploy and they do not: "
                        + ", ".join(schema["we_have_they_do_not"]),
            "why": "A real advantage, and an unusual one in this market.",
            "action": "Keep it, and extend it to pages that lack it.",
        })

    wins = [s for s in ("word_count", "external_links", "h2_count", "tables")
            if (comparison.get(s) or {}).get("gap") is not None
            and comparison[s]["gap"] > 0]
    if wins:
        findings.append({
            "severity": "good",
            "headline": "Ahead on: " + ", ".join(w.replace("_", " ") for w in wins),
            "why": "Measured on the same signals across both sets of pages.",
            "action": "Hold these while closing the gaps above.",
        })

    if not findings:
        findings.append({
            "severity": "info",
            "headline": "No material structural difference",
            "why": "Every measured signal is within 20% on both sides.",
            "action": "The difference is in substance rather than structure. "
                      "Compare what each page actually answers.",
        })
    return findings


def discover_articles(index_url: str, limit: int = 8) -> list[str]:
    """Find article URLs from a blog index page.

    Comparing index pages tells you little — they are link lists. This pulls
    the articles themselves so the comparison is like for like.
    """
    allowed, _ = _robots_allows(index_url)
    if not allowed:
        return []

    status, html, _ = _fetch(index_url)
    if not html:
        return []

    resolve_from = _resolution_base(html, index_url)
    base = urllib.parse.urlparse(index_url)
    index_path = base.path.rstrip("/")

    seen: list[str] = []
    for href in re.findall(r'(?i)<a[^>]+href=["\']([^"\']+)["\']', html):
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = urllib.parse.urljoin(resolve_from, href).split("#")[0].rstrip("/")
        parsed = urllib.parse.urlparse(absolute)

        if parsed.netloc.lower().removeprefix("www.") != base.netloc.lower().removeprefix("www."):
            continue
        # Deeper than the index, and not the index itself.
        if not parsed.path.rstrip("/").startswith(index_path) or parsed.path.rstrip("/") == index_path:
            continue
        # Skip pagination and category listings.
        if re.search(r"/(page|category|tag|author)/", parsed.path, re.IGNORECASE):
            continue
        if absolute not in seen:
            seen.append(absolute)
        if len(seen) >= limit:
            break
    return seen
