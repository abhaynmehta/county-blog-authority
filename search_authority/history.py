"""Audit history: a record of every run, so repeat mistakes are visible.

A single audit says what is wrong today. A history says whether the same
thing keeps coming back — which is the difference between "this blog has a
RERA problem" and "ROI has shipped this same RERA problem eleven times since
June, and twice on documents we already sent back".

The second is what changes an agency conversation, so it is what this stores.

Records are append-only JSONL. One line per audit, never rewritten, so the
record of what was true on a date cannot be quietly revised.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Optional

LEDGER = Path("audit-history/ledger.jsonl")

# An issue that disappears and later returns on the same document is a
# regression: it was fixed, then reintroduced. Those matter more than a
# problem that was simply never addressed.
REGRESSION = "regression"
UNRESOLVED = "unresolved"
FIXED = "fixed"


@dataclass
class Entry:
    """One audit of one document at one moment."""

    slug: str
    audited_at: str
    score: int
    publishable: bool
    issue_ids: list[str]
    categories: list[str]
    owners: list[str]
    failed_gates: list[str]
    source: Optional[str] = None

    @property
    def day(self) -> date:
        return datetime.fromisoformat(self.audited_at).date()

    def as_dict(self) -> dict:
        return {
            "slug": self.slug, "audited_at": self.audited_at, "score": self.score,
            "publishable": self.publishable, "issue_ids": self.issue_ids,
            "categories": self.categories, "owners": self.owners,
            "failed_gates": self.failed_gates, "source": self.source,
        }


def record(analysis, slug: str, source: Optional[str] = None,
           ledger: Path = LEDGER, when: Optional[datetime] = None) -> Entry:
    """Append one audit result to the ledger."""
    entry = Entry(
        slug=slug,
        audited_at=(when or datetime.now()).isoformat(timespec="seconds"),
        score=analysis.score,
        publishable=analysis.publishable,
        # Category rather than issue_id is what identifies "the same mistake":
        # ids are positional and shift when unrelated text is edited.
        issue_ids=sorted(i.issue_id for i in analysis.issues),
        categories=sorted({i.category.value for i in analysis.issues}),
        owners=sorted({i.owner.value for i in analysis.issues}),
        failed_gates=[g.gate_name for g in analysis.gates if g.status.value == "FAIL"],
        source=source,
    )
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry.as_dict()) + "\n")
    return entry


def load(ledger: Path = LEDGER) -> list[Entry]:
    """Read the ledger, skipping any line that will not parse."""
    if not Path(ledger).exists():
        return []
    entries = []
    for line in Path(ledger).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entries.append(Entry(**json.loads(line)))
        except (json.JSONDecodeError, TypeError):
            continue
    return sorted(entries, key=lambda e: e.audited_at)


def _by_document(entries: Iterable[Entry]) -> dict[str, list[Entry]]:
    grouped: dict[str, list[Entry]] = defaultdict(list)
    for entry in entries:
        grouped[entry.slug].append(entry)
    return {k: sorted(v, key=lambda e: e.audited_at) for k, v in grouped.items()}


def document_trend(entries: Iterable[Entry]) -> list[dict]:
    """Per document: first score, latest score, and whether it moved."""
    trends = []
    for slug, runs in _by_document(entries).items():
        if len(runs) < 2:
            continue
        first, last = runs[0], runs[-1]
        trends.append({
            "slug": slug,
            "runs": len(runs),
            "first_score": first.score,
            "latest_score": last.score,
            "change": last.score - first.score,
            "first_seen": first.day.isoformat(),
            "last_seen": last.day.isoformat(),
            "publishable_now": last.publishable,
        })
    return sorted(trends, key=lambda t: t["change"])


def recurring_mistakes(entries: Iterable[Entry], min_documents: int = 2) -> list[dict]:
    """Issue categories appearing across several documents.

    Counted by distinct document, not by occurrence: one blog audited twenty
    times would otherwise look like a systemic problem when it is one blog.
    """
    documents_by_category: dict[str, set[str]] = defaultdict(set)
    latest_by_document = {slug: runs[-1] for slug, runs in _by_document(entries).items()}

    for slug, entry in latest_by_document.items():
        for category in entry.categories:
            documents_by_category[category].add(slug)

    total = len(latest_by_document) or 1
    return sorted(
        (
            {
                "category": category,
                "documents": len(slugs),
                "share_pct": round(len(slugs) / total * 100, 1),
                "examples": sorted(slugs)[:5],
            }
            for category, slugs in documents_by_category.items()
            if len(slugs) >= min_documents
        ),
        key=lambda r: -r["documents"],
    )


def regressions(entries: Iterable[Entry]) -> list[dict]:
    """Issues that were fixed on a document and later came back.

    These are the ones worth raising: the fix was understood and applied
    once, so the problem is process rather than knowledge.
    """
    found = []
    for slug, runs in _by_document(entries).items():
        if len(runs) < 3:
            continue
        seen_categories = [set(r.categories) for r in runs]
        for category in set().union(*seen_categories):
            present = [category in s for s in seen_categories]
            # present, then absent, then present again.
            if True in present and False in present:
                for i in range(1, len(present) - 1):
                    if present[i - 1] and not present[i] and any(present[i + 1:]):
                        found.append({
                            "slug": slug,
                            "category": category,
                            "fixed_on": runs[i].day.isoformat(),
                            "returned_on": runs[
                                next(j for j in range(i + 1, len(present)) if present[j])
                            ].day.isoformat(),
                            "status": REGRESSION,
                        })
                        break
    return sorted(found, key=lambda r: r["returned_on"], reverse=True)


def owner_scorecard(entries: Iterable[Entry]) -> dict:
    """How many documents currently carry issues owned by each agency."""
    latest = {slug: runs[-1] for slug, runs in _by_document(entries).items()}
    counts: Counter = Counter()
    for entry in latest.values():
        for owner in entry.owners:
            counts[owner] += 1
    return {
        "documents": len(latest),
        "by_owner": dict(counts.most_common()),
    }


def summary(ledger: Path = LEDGER) -> dict:
    """Everything the history can say, in one call."""
    entries = load(ledger)
    if not entries:
        return {
            "runs": 0,
            "message": "No audit history yet. Run an audit and it will start "
                       "recording, so repeat mistakes become visible over time.",
        }

    latest = {slug: runs[-1] for slug, runs in _by_document(entries).items()}
    scores = [e.score for e in latest.values()]
    trends = document_trend(entries)

    return {
        "runs": len(entries),
        "documents": len(latest),
        "first_run": entries[0].day.isoformat(),
        "latest_run": entries[-1].day.isoformat(),
        "average_score_now": round(sum(scores) / len(scores), 1) if scores else 0,
        "publishable_now": sum(1 for e in latest.values() if e.publishable),
        "improved": [t for t in trends if t["change"] > 0],
        "declined": [t for t in trends if t["change"] < 0],
        "recurring_mistakes": recurring_mistakes(entries),
        "regressions": regressions(entries),
        "owners": owner_scorecard(entries),
    }
