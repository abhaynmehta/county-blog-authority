"""Prose-quality checks: the tells that mark copy as machine-written or
carelessly edited.

Kept separate from content_auditor because these are style findings, not
factual or compliance ones — they should never fail a publication gate, only
lower the score and give the writer something specific to fix.
"""

from __future__ import annotations

import re
from collections import Counter

from .models import AuditIssue, IssueCategory, Owner, Severity

# Each rule: (id, pattern, what it means, how to fix it).
# Ordered roughly by how strongly it signals unedited machine output.
RULES: list[tuple[str, str, str, str]] = [
    ("EM_DASH",
     r"\s—\s|\w—\w",
     "Em dashes used as general connectors",
     "Use a comma, a colon, or a full stop. Em dashes in this density read as machine-written."),
    ("RULE_OF_THREE",
     r"(?i)\bnot only\b[^.]{5,80}?\bbut also\b",
     "'Not only… but also' construction",
     "Rewrite as a plain sentence."),
    ("DELVE",
     r"(?i)\b(?:delve|delving)\s+into\b",
     "'Delve into'",
     "Use 'look at', 'examine', or just say the thing."),
    ("TAPESTRY",
     r"(?i)\b(?:tapestry|symphony|testament)\s+(?:of|to)\b",
     "Decorative metaphor ('tapestry of', 'testament to')",
     "Replace with a concrete statement."),
    ("NAVIGATE_LANDSCAPE",
     r"(?i)\bnavigat(?:e|ing)\s+the\s+(?:complex\s+)?(?:landscape|world|realm)\b",
     "'Navigating the landscape'",
     "Say what the reader actually does."),
    ("IN_TODAYS",
     r"(?i)\bin\s+today'?s\s+(?:fast[- ]paced|ever[- ]changing|dynamic|modern|digital)\b",
     "Filler opener ('in today's fast-paced…')",
     "Delete the opener and start with the substance."),
    ("ELEVATE",
     r"(?i)\b(?:elevate|unlock|unleash|embark\s+on)\s+(?:your|a|the)\b",
     "Marketing verb ('elevate your', 'unlock the')",
     "Use a plain verb."),
    ("MOREOVER",
     r"(?i)^\s*(?:Moreover|Furthermore|Additionally|In conclusion),",
     "Essay connector opening a paragraph",
     "Start with the point. Connectors like this are padding."),
    ("NESTLED",
     r"(?i)\bnestled\s+(?:in|amidst|among|within)\b",
     "'Nestled in' — property-listing cliche",
     "State the location plainly."),
    ("DOUBLE_HYPHEN",
     r"\w--\w|\s--\s",
     "Double hyphen used as a dash",
     "Use a single dash or rewrite; '--' is a typing artefact."),
    # A SPACED_HYPHEN rule sat here. Markdown bullet markers ("- item")
    # produced 70 matches across the corpus against almost no real ones,
    # and a spaced hyphen in a title is ordinary punctuation. A noisy rule
    # costs more credibility than it earns.
    ("TRIPLE_ADJECTIVE",
     r"(?i)\b(?:luxurious|premium|modern|spacious|elegant|exclusive),\s+"
     r"(?:luxurious|premium|modern|spacious|elegant|exclusive),\s+and\s+"
     r"(?:luxurious|premium|modern|spacious|elegant|exclusive)\b",
     "Three stacked adjectives",
     "Keep the one that carries information."),
]

# Some patterns are only a problem in quantity. A single em dash is a style
# choice; a dozen is a tell. Both conditions must hold: at least MIN_COUNT
# occurrences, and a rate above the per-1,000-word limit — the count floor
# stops a short paragraph reading as high density off one usage.
DENSITY_LIMIT = {"EM_DASH": 2.0}
MIN_COUNT = {"EM_DASH": 3}


# Published web content uses typographic quotes far more often than straight
# ones. Matching only the straight apostrophe missed "In today's fast-paced
# world" on real pages — the single most recognisable tell there is.
_SMART_QUOTES = {
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"',
}


def _normalise_quotes(text: str) -> str:
    for smart, plain in _SMART_QUOTES.items():
        text = text.replace(smart, plain)
    return text


def check_prose(text: str, issue_counter: list[int]) -> list[AuditIssue]:
    """Return style findings for `text`.

    Every finding quotes the offending phrase, because "your writing sounds
    generated" is not actionable and "paragraph 4 says 'delve into'" is.
    """
    text = _normalise_quotes(text)
    issues: list[AuditIssue] = []
    words = max(1, len(text.split()))
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    for rule_id, pattern, summary, fix in RULES:
        flags = re.MULTILINE
        matches = list(re.finditer(pattern, text, flags))
        if not matches:
            continue

        if len(matches) < MIN_COUNT.get(rule_id, 1):
            continue
        per_1000 = len(matches) * 1000 / words
        if rule_id in DENSITY_LIMIT and per_1000 < DENSITY_LIMIT[rule_id]:
            continue

        paragraph = _paragraph_of(paragraphs, matches[0].group(0))
        count = len(matches)
        issue_counter[0] += 1
        issues.append(AuditIssue(
            issue_id=f"CG-PROSE-{issue_counter[0]:03d}",
            category=IssueCategory.GRAMMAR,
            severity=Severity.MEDIUM if count >= 3 else Severity.LOW,
            owner=Owner.ROI,
            summary=f"{summary} ({count}x)" if count > 1 else summary,
            paragraph=paragraph,
            claim=_context(text, matches[0]),
            reason="Reads as unedited machine output or boilerplate",
            recommended_action=fix,
            acceptance_test=f"No remaining instances of: {summary.lower()}",
            editorial_rule=f"PROSE_{rule_id}",
        ))

    issues.extend(_check_repetition(paragraphs, issue_counter))
    return issues


def _check_repetition(paragraphs: list[str], issue_counter: list[int]) -> list[AuditIssue]:
    """Flag paragraphs that open with the same word — a drafting habit that
    makes copy feel templated."""
    openers = Counter()
    for para in paragraphs:
        first = re.match(r"\s*#*\s*(\w+)", para)
        if first:
            openers[first.group(1).lower()] += 1

    issues = []
    for word, count in openers.most_common(3):
        # Skip single letters: "Q"/"A" are FAQ markers, not a habit.
        if count >= 4 and len(word) > 1 and word not in {"the", "a"}:
            issue_counter[0] += 1
            issues.append(AuditIssue(
                issue_id=f"CG-PROSE-{issue_counter[0]:03d}",
                category=IssueCategory.GRAMMAR,
                severity=Severity.LOW,
                owner=Owner.ROI,
                summary=f"{count} paragraphs open with '{word}'",
                recommended_action="Vary the sentence openings.",
                acceptance_test="No word opens more than three paragraphs",
                editorial_rule="PROSE_REPEATED_OPENER",
            ))
            break
    return issues


def _paragraph_of(paragraphs: list[str], snippet: str) -> int | None:
    for index, para in enumerate(paragraphs, 1):
        if snippet in para:
            return index
    return None


def _context(text: str, match: re.Match, window: int = 60) -> str:
    start = max(0, match.start() - window)
    end = min(len(text), match.end() + window)
    return " ".join(text[start:end].split())
