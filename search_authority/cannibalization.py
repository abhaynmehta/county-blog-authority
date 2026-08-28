"""Keyword cannibalisation detection across the blog corpus.

Cannibalisation is two or more pages competing for the same search query.
Google picks one and often not the one you wanted, so both rank worse than a
single consolidated page would.

This is frequently confused with duplicate content. They are different
problems with different fixes, and the distinction is what this module exists
to make arguable:

  Duplicate content — the same content reachable at several URLs.
      Fixed by a canonical tag, which tells Google which URL to index.

  Cannibalisation — different content targeting the same query.
      A canonical tag does not fix this. Pointing one page's canonical at
      another tells Google to drop the first page from the index entirely,
      which is a deletion, not a fix. Schema markup does not fix it either:
      schema changes how a result is displayed, not which page is chosen for
      a query.

  The actual fixes are: consolidate the pages, differentiate them so they
  target genuinely different intents, or nominate one target page and point
  the others at it with internal links.

Reference: Google Search Central, "Consolidate duplicate URLs" (canonical
tags) and "Structured data general guidelines" (schema affects appearance).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Words too common in Indian real estate copy to signal intent on their own.
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "are", "was", "were", "be",
    "been", "your", "you", "our", "we", "it", "its", "this", "that", "these",
    "those", "have", "has", "had", "will", "would", "can", "could", "should",
    "more", "most", "best", "top", "new", "why", "how", "what", "when",
    "where", "which", "who", "all", "any", "some", "one", "two", "about",
    "into", "over", "under", "than", "then", "there", "here", "also",
}

# Query-shaped terms: what a buyer would actually type.
INTENT_MARKERS = {
    "flats", "flat", "apartment", "apartments", "property", "properties",
    "bhk", "residential", "project", "projects", "builder", "developer",
    "price", "prices", "investment", "possession", "luxury", "premium",
    "ready", "move", "sale", "buy", "booking",
}


@dataclass
class PageKeywords:
    """The terms one page appears to be targeting."""

    slug: str
    title: Optional[str] = None
    h1: Optional[str] = None
    primary_terms: list[str] = field(default_factory=list)
    body_terms: list[str] = field(default_factory=list)

    def all_terms(self) -> set[str]:
        return set(self.primary_terms) | set(self.body_terms)


@dataclass
class Collision:
    """Two pages competing for the same terms."""

    slug_a: str
    slug_b: str
    shared_terms: list[str]
    shared_in_title: list[str]
    severity: str  # high | medium | low

    def as_dict(self) -> dict:
        return {
            "page_a": self.slug_a,
            "page_b": self.slug_b,
            "shared_terms": self.shared_terms,
            "shared_in_title": self.shared_in_title,
            "severity": self.severity,
        }


def _ngrams(words: list[str], n: int) -> list[str]:
    return [" ".join(words[i:i + n]) for i in range(len(words) - n + 1)]


def _clean_words(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 2]


def extract_keywords(text: str, slug: str, title: Optional[str] = None,
                     h1: Optional[str] = None) -> PageKeywords:
    """Infer the terms a page targets.

    Title and H1 carry the most weight, because that is where a writer
    declares intent. Body phrases are secondary evidence.
    """
    page = PageKeywords(slug=slug, title=title, h1=h1)

    # Primary: multi-word phrases from title and H1.
    declared = " ".join(filter(None, [title, h1]))
    dwords = _clean_words(declared)
    primary = set()
    for n in (2, 3):
        for gram in _ngrams(dwords, n):
            if any(marker in gram.split() for marker in INTENT_MARKERS):
                primary.add(gram)
    # Single strong tokens too (sector numbers, project names).
    for w in dwords:
        if w.isdigit() and len(w) == 3:      # sector numbers: 151, 115, 150
            primary.add(f"sector {w}")
    page.primary_terms = sorted(primary)

    # Secondary: repeated body phrases that look like target queries.
    bwords = _clean_words(text)
    counts = Counter()
    for n in (2, 3):
        for gram in _ngrams(bwords, n):
            if any(marker in gram.split() for marker in INTENT_MARKERS):
                counts[gram] += 1
    page.body_terms = [g for g, c in counts.most_common(25) if c >= 3]

    return page


def find_collisions(pages: list[PageKeywords],
                    min_shared: int = 2) -> list[Collision]:
    """Find pairs of pages competing for the same terms.

    Severity reflects where the overlap sits. Two pages sharing a term in
    their titles are directly competing; overlap only in body text is weaker
    evidence, since a passing mention is not a target.
    """
    collisions: list[Collision] = []

    for i, a in enumerate(pages):
        for b in pages[i + 1:]:
            shared = sorted(a.all_terms() & b.all_terms())
            if len(shared) < min_shared:
                continue

            title_shared = sorted(set(a.primary_terms) & set(b.primary_terms))

            if len(title_shared) >= 2:
                severity = "high"
            elif title_shared:
                severity = "medium"
            elif len(shared) >= 5:
                severity = "medium"
            else:
                severity = "low"

            collisions.append(Collision(
                slug_a=a.slug, slug_b=b.slug,
                shared_terms=shared[:12],
                shared_in_title=title_shared,
                severity=severity,
            ))

    order = {"high": 0, "medium": 1, "low": 2}
    collisions.sort(key=lambda c: (order[c.severity], -len(c.shared_terms)))
    return collisions


def recommend_fix(collision: Collision) -> dict:
    """The defensible fix for one collision, and what does not fix it.

    The "not_fixed_by" field exists because the usual pushback is that
    canonical tags or distinct schema already handle this. Neither does.
    """
    if collision.severity == "high":
        action = (
            "Consolidate. These two pages declare the same target in their "
            "titles. Merge the weaker into the stronger and 301-redirect it, "
            "or rewrite one to target a genuinely different query."
        )
    elif collision.severity == "medium":
        action = (
            "Differentiate. Rewrite one page's title, H1, and opening so it "
            "targets a distinct intent — a different sector, configuration, "
            "or buyer question — then internally link it to the primary page."
        )
    else:
        action = (
            "Monitor. Overlap is in body text only. Confirm in Search Console "
            "that both pages are not surfacing for the same query before acting."
        )

    return {
        "pages": [collision.slug_a, collision.slug_b],
        "severity": collision.severity,
        "shared_terms": collision.shared_terms,
        "recommended_action": action,
        "not_fixed_by": [
            "Canonical tags — they resolve duplicate URLs serving the same "
            "content. These pages have different content targeting one query. "
            "A canonical here removes one page from the index rather than "
            "fixing the competition.",
            "Distinct schema markup — schema controls how a result is "
            "displayed, not which page Google selects for a query.",
            "Different meta descriptions — these influence click-through, "
            "not which page ranks.",
        ],
        "how_to_verify": (
            "Search Console → Performance → filter by the shared query, then "
            "group by page. Two of your own URLs appearing for one query, "
            "each with low average position, is the confirming signal."
        ),
    }


def analyse_corpus(inventory_entries: list[dict]) -> dict:
    """Run cannibalisation analysis over every audited local file."""
    pages: list[PageKeywords] = []

    for entry in inventory_entries:
        local = entry.get("local_file") or entry.get("file")
        if not local or not Path(local).exists():
            continue
        try:
            text = Path(local).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        title = None
        for line in text.split("\n"):
            low = line.strip().lower()
            if low.startswith("meta title:") or low.startswith("title tag:"):
                title = line.split(":", 1)[1].strip().strip('"\'')
                break

        h1 = None
        match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if match:
            h1 = match.group(1).strip()

        pages.append(extract_keywords(
            text, slug=Path(local).stem, title=title, h1=h1,
        ))

    collisions = find_collisions(pages)

    return {
        "pages_analysed": len(pages),
        "collisions": len(collisions),
        "by_severity": {
            sev: sum(1 for c in collisions if c.severity == sev)
            for sev in ("high", "medium", "low")
        },
        "details": [recommend_fix(c) for c in collisions[:40]],
    }
