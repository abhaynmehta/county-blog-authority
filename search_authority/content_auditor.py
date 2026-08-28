"""Content auditor for DOCX and text blog content.

Produces per-paragraph, actionable audit findings with owner assignment.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from .models import (
    AuditIssue, ContentAnalysis, GateResult, GateStatus,
    IssueCategory, MetadataAnalysis, Owner, Severity,
)
from .truth_layer import load_truth_layer, _normalise_url


# Patterns that indicate prohibited language
PROHIBITED_PATTERNS = [
    (r"\bguaranteed\s+appreciation\b", "guaranteed appreciation", IssueCategory.PROHIBITED_LANGUAGE),
    (r"\bassured\s+returns?\b", "assured returns", IssueCategory.PROHIBITED_LANGUAGE),
    (r"\brisk[- ]free\s+investment\b", "risk-free investment", IssueCategory.PROHIBITED_LANGUAGE),
    (r"\bbest\s+investment\b", "best investment", IssueCategory.PROHIBITED_LANGUAGE),
    (r"\bbest\s+(?:flats?|property|properties|sector|place|location|area)\b",
     "superlative claim ('best') without evidence", IssueCategory.PROHIBITED_LANGUAGE),
    (r"\bguaranteed\s+rental\s+income\b", "guaranteed rental income", IssueCategory.PROHIBITED_LANGUAGE),
    (r"\bbest\s+developer\b", "best developer", IssueCategory.PROHIBITED_LANGUAGE),
    (r"\bonly\s+developer\s+(?:in|with)\b", "only developer claim", IssueCategory.PROHIBITED_LANGUAGE),
    (r"\bworld[- ]class\b", "world-class without evidence", IssueCategory.PROHIBITED_LANGUAGE),
    (r"\bunmatched\b", "unmatched claim", IssueCategory.PROHIBITED_LANGUAGE),
    (r"\bno\s+other\s+project\b", "no other project claim", IssueCategory.PROHIBITED_LANGUAGE),
]

# Infrastructure status patterns
STALE_INFRA_PATTERNS = [
    (r"\bupcoming\s+(?:airport|jewar|noida\s+international)\b",
     "Airport called 'upcoming' — Noida International Airport is operational since June 2026",
     "https://www.niairport.in/en/company/news/2026/2026-06-15"),
    (r"\b(?:proposed|in\s+the\s+pipeline)\s+(?:airport|jewar)\b",
     "Airport called 'proposed/in the pipeline' — it is operational",
     "https://www.niairport.in/en/company/news/2026/2026-06-15"),
    (r"(?i)\b(?:jewar|noida\s+international)\s+airport\s+(?:is\s+)?(?:expected|set|poised|slated)\s+to\b",
     "Airport described as future — Noida International Airport opened June 2026",
     "https://www.niairport.in/en/company/news/2026/2026-06-15"),
    (r"(?i)\b(?:jewar|noida\s+international)\s+airport\s+(?:is\s+)?(?:under\s+construction|being\s+built)\b",
     "Airport described as under construction — it is operational since June 2026",
     "https://www.niairport.in/en/company/news/2026/2026-06-15"),
    (r"(?i)\b(?:once|when|after)\s+(?:jewar|noida\s+international)\s+airport\s+(?:is\s+)?(?:completed?|operational|ready|opens?)\b",
     "Airport described as not yet open — it has been operational since June 2026",
     "https://www.niairport.in/en/company/news/2026/2026-06-15"),
]

# Unsupported claim patterns
UNSUPPORTED_CLAIM_PATTERNS = [
    (r"\b\d+%\s+(?:appreciation|growth|return|rental\s+yield)\b",
     "Percentage claim needs verified source"),
    (r"\b₹[\d,.]+\s+(?:per\s+sq\.?\s*ft|psf)\b",
     "Price claim needs current source and date"),
    (r"\b\d+\s+(?:minutes?|mins?)\s+(?:from|to|drive)\b",
     "Travel time claim needs verification — never state as guaranteed"),
]

# Clickbait / spam signal patterns in meta
CLICKBAIT_PATTERNS = [
    r"(?i)\bclick\s+(?:to|here|now)\s+(?:to\s+)?(?:know|read|learn|find|see)\b",
    r"(?i)\byou\s+won'?t\s+believe\b",
    r"(?i)\bdon'?t\s+miss\s+(?:this|out)\b",
    r"(?i)\bhurry\b",
    r"(?i)\blimited\s+(?:period|time)\s+offer\b",
]

# Implied appreciation / returns (softer than outright "guaranteed")
IMPLIED_APPRECIATION_PATTERNS = [
    (r"(?i)\bfuture\s+appreciation\s+potential\b",
     "Implies price appreciation without evidence"),
    (r"(?i)\bgap\s+between\s+current\s+prices?\s+and\s+future\s+value\b",
     "Implies certain price appreciation"),
    (r"(?i)\bproperty\s+(?:values?\s+)?(?:will|would|set\s+to)\s+(?:grow|rise|increase|appreciate)\b",
     "Predicts price movement without source"),
    (r"(?i)\bsupport\s+property\s+values\b",
     "Implies price support without evidence"),
]


def _extract_metadata_from_text(text: str) -> MetadataAnalysis:
    """Extract metadata markers from blog text (Meta Title:, Meta Description:, etc.)."""
    meta = MetadataAnalysis()
    lines = text.split("\n")

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()

        # Meta title detection
        if lower.startswith("meta title:") or lower.startswith("title tag:"):
            meta.title = stripped.split(":", 1)[1].strip().strip('"\'')
            meta.title_length = len(meta.title)
        elif lower.startswith("meta description:"):
            meta.meta_description = stripped.split(":", 1)[1].strip().strip('"\'')
            meta.meta_description_length = len(meta.meta_description)

    # Heading detection
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    for match in heading_pattern.finditer(text):
        level = len(match.group(1))
        heading_text = match.group(2).strip()
        meta.headings.append({"level": level, "text": heading_text})
        if level == 1:
            meta.h1 = heading_text
            meta.h1_count += 1

    # Also detect DOCX-style headings (lines that look like headings without #)
    # H1: / H2: / H3: labels sometimes appear in agency docs
    h_label_pattern = re.compile(r"^H([1-6])[\s:]+(.+)$", re.MULTILINE | re.IGNORECASE)
    for match in h_label_pattern.finditer(text):
        level = int(match.group(1))
        heading_text = match.group(2).strip()
        meta.headings.append({"level": level, "text": heading_text, "label_style": True})
        if level == 1:
            if not meta.h1:
                meta.h1 = heading_text
            meta.h1_count += 1

    return meta


def _check_metadata(meta: MetadataAnalysis, issues: list[AuditIssue], issue_counter: list[int]):
    """Check metadata quality and generate issues."""
    prefix = "CG-META"

    # Title checks
    if not meta.title:
        issue_counter[0] += 1
        issues.append(AuditIssue(
            issue_id=f"{prefix}-{issue_counter[0]:03d}",
            category=IssueCategory.META_TITLE,
            severity=Severity.HIGH,
            owner=Owner.ROI,
            summary="No meta title found",
            recommended_action="Add a unique meta title, 30-60 characters",
            acceptance_test="Meta title present and 30-60 characters",
        ))
    elif meta.title_length < 30:
        issue_counter[0] += 1
        issues.append(AuditIssue(
            issue_id=f"{prefix}-{issue_counter[0]:03d}",
            category=IssueCategory.META_TITLE,
            severity=Severity.MEDIUM,
            owner=Owner.ROI,
            summary=f"Meta title too short ({meta.title_length} chars)",
            claim=meta.title,
            recommended_action="Expand title to 30-60 characters",
            acceptance_test="Title is 30-60 characters",
        ))
    elif meta.title_length > 60:
        issue_counter[0] += 1
        issues.append(AuditIssue(
            issue_id=f"{prefix}-{issue_counter[0]:03d}",
            category=IssueCategory.META_TITLE,
            severity=Severity.MEDIUM,
            owner=Owner.ROI,
            summary=f"Meta title too long ({meta.title_length} chars, may truncate)",
            claim=meta.title,
            recommended_action="Shorten title to 60 characters or fewer",
            acceptance_test="Title is 30-60 characters",
        ))

    # Meta description checks
    if not meta.meta_description:
        issue_counter[0] += 1
        issues.append(AuditIssue(
            issue_id=f"{prefix}-{issue_counter[0]:03d}",
            category=IssueCategory.META_DESCRIPTION,
            severity=Severity.HIGH,
            owner=Owner.ROI,
            summary="No meta description found",
            recommended_action="Add a unique meta description, 120-160 characters",
            acceptance_test="Meta description present and 120-160 characters",
        ))
    elif meta.meta_description_length < 120:
        issue_counter[0] += 1
        issues.append(AuditIssue(
            issue_id=f"{prefix}-{issue_counter[0]:03d}",
            category=IssueCategory.META_DESCRIPTION,
            severity=Severity.MEDIUM,
            owner=Owner.ROI,
            summary=f"Meta description too short ({meta.meta_description_length} chars)",
            claim=meta.meta_description,
            recommended_action="Expand to 120-160 characters for optimal SERP display",
            acceptance_test="Description is 120-160 characters",
        ))
    elif meta.meta_description_length > 160:
        issue_counter[0] += 1
        issues.append(AuditIssue(
            issue_id=f"{prefix}-{issue_counter[0]:03d}",
            category=IssueCategory.META_DESCRIPTION,
            severity=Severity.MEDIUM,
            owner=Owner.ROI,
            summary=f"Meta description too long ({meta.meta_description_length} chars)",
            claim=meta.meta_description,
            recommended_action="Shorten to 120-160 characters",
            acceptance_test="Description is 120-160 characters",
        ))

    # Clickbait in meta description
    if meta.meta_description:
        for pattern in CLICKBAIT_PATTERNS:
            if re.search(pattern, meta.meta_description):
                issue_counter[0] += 1
                issues.append(AuditIssue(
                    issue_id=f"{prefix}-{issue_counter[0]:03d}",
                    category=IssueCategory.META_DESCRIPTION,
                    severity=Severity.MEDIUM,
                    owner=Owner.ROI,
                    summary="Clickbait CTA in meta description — spam signal per Google",
                    claim=meta.meta_description,
                    recommended_action="Remove clickbait CTA. Use a factual description of the content.",
                    acceptance_test="No 'click to', 'don't miss', 'hurry' etc. in meta",
                    google_rule="SPAM-CLICKBAIT-001",
                ))
                break

    # H1 checks
    if meta.h1_count == 0:
        issue_counter[0] += 1
        issues.append(AuditIssue(
            issue_id=f"{prefix}-{issue_counter[0]:03d}",
            category=IssueCategory.HEADING_STRUCTURE,
            severity=Severity.HIGH,
            owner=Owner.ROI,
            summary="No H1 heading found",
            recommended_action="Add exactly one H1 heading as the main title",
            acceptance_test="Exactly one H1 present",
            google_rule="CONTENT-HEADING-001",
        ))
    elif meta.h1_count > 1:
        issue_counter[0] += 1
        issues.append(AuditIssue(
            issue_id=f"{prefix}-{issue_counter[0]:03d}",
            category=IssueCategory.HEADING_STRUCTURE,
            severity=Severity.HIGH,
            owner=Owner.ROI,
            summary=f"Multiple H1 headings found ({meta.h1_count})",
            recommended_action="Use exactly one H1. Convert others to H2",
            acceptance_test="Exactly one H1 present",
            google_rule="CONTENT-HEADING-001",
        ))

    # Heading hierarchy check
    if meta.headings:
        prev_level = 0
        for h in meta.headings:
            level = h["level"]
            if level > prev_level + 1 and prev_level > 0:
                issue_counter[0] += 1
                issues.append(AuditIssue(
                    issue_id=f"{prefix}-{issue_counter[0]:03d}",
                    category=IssueCategory.HEADING_STRUCTURE,
                    severity=Severity.MEDIUM,
                    owner=Owner.ROI,
                    summary=f"Heading level skipped: H{prev_level} → H{level} ('{h['text']}')",
                    recommended_action=f"Change to H{prev_level + 1} or add intermediate heading",
                    acceptance_test="No heading levels skipped (H1→H2→H3)",
                    google_rule="CONTENT-HEADING-002",
                ))
            prev_level = level


def _check_paragraphs(text: str, issues: list[AuditIssue], issue_counter: list[int]):
    """Scan content paragraph by paragraph for issues."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    for i, para in enumerate(paragraphs, 1):
        para_lower = para.lower()

        # Check prohibited language
        for pattern, name, category in PROHIBITED_PATTERNS:
            if re.search(pattern, para_lower):
                issue_counter[0] += 1
                issues.append(AuditIssue(
                    issue_id=f"CG-CONTENT-{issue_counter[0]:03d}",
                    category=category,
                    severity=Severity.CRITICAL,
                    owner=Owner.ROI,
                    summary=f"Prohibited language: '{name}'",
                    paragraph=i,
                    claim=para[:200],
                    reason="Violates RERA compliance / editorial policy",
                    recommended_action=f"Remove or rephrase the '{name}' claim",
                    acceptance_test=f"No '{name}' language remains",
                    editorial_rule="BRAND_PROHIBITED_001",
                ))

        # Check stale infrastructure claims
        for pattern, message, source in STALE_INFRA_PATTERNS:
            if re.search(pattern, para_lower):
                issue_counter[0] += 1
                issues.append(AuditIssue(
                    issue_id=f"CG-CONTENT-{issue_counter[0]:03d}",
                    category=IssueCategory.INFRASTRUCTURE_STATUS,
                    severity=Severity.CRITICAL,
                    owner=Owner.ROI,
                    summary=message,
                    paragraph=i,
                    claim=para[:200],
                    evidence_source=source,
                    verified_status="Noida International Airport: commercial ops began 15 June 2026",
                    recommended_action="Update to reflect operational status with source link",
                    acceptance_test="Airport described as operational with official source",
                ))

        # Check unsupported quantitative claims
        for pattern, message in UNSUPPORTED_CLAIM_PATTERNS:
            match = re.search(pattern, para_lower)
            if match:
                issue_counter[0] += 1
                issues.append(AuditIssue(
                    issue_id=f"CG-CONTENT-{issue_counter[0]:03d}",
                    category=IssueCategory.UNSUPPORTED_CLAIM,
                    severity=Severity.HIGH,
                    owner=Owner.ROI,
                    summary=message,
                    paragraph=i,
                    claim=match.group(0),
                    recommended_action="Add verified source or remove claim",
                    acceptance_test="Claim has inline source attribution",
                ))

    # Check implied appreciation language
    for para_idx, para in enumerate(paragraphs, 1):
        for pattern, message in IMPLIED_APPRECIATION_PATTERNS:
            if re.search(pattern, para):
                issue_counter[0] += 1
                issues.append(AuditIssue(
                    issue_id=f"CG-CONTENT-{issue_counter[0]:03d}",
                    category=IssueCategory.UNSUPPORTED_CLAIM,
                    severity=Severity.MEDIUM,
                    owner=Owner.ROI,
                    summary=f"Implied appreciation: {message}",
                    paragraph=para_idx,
                    claim=para[:200],
                    recommended_action="Remove forward-looking price claim or add 'past performance does not indicate future results'",
                    acceptance_test="No implied price appreciation without disclaimer",
                    editorial_rule="EDITORIAL_INVESTMENT_001",
                ))

    # Check for travel time claims without source attribution
    travel_time_paras = []
    for para_idx, para in enumerate(paragraphs, 1):
        times_in_para = re.findall(
            r"\b\d+[\s–-]*(?:\d+\s+)?(?:minutes?|mins?)\s+(?:away|drive|from)",
            para, re.IGNORECASE,
        )
        if times_in_para and not re.search(r"(?:google\s+maps|source|as\s+per|according\s+to)", para, re.IGNORECASE):
            travel_time_paras.append((para_idx, len(times_in_para)))
    if travel_time_paras:
        total_claims = sum(count for _, count in travel_time_paras)
        issue_counter[0] += 1
        issues.append(AuditIssue(
            issue_id=f"CG-CONTENT-{issue_counter[0]:03d}",
            category=IssueCategory.UNSUPPORTED_CLAIM,
            severity=Severity.HIGH,
            owner=Owner.ROI,
            summary=f"{total_claims} travel time claim(s) without source attribution",
            recommended_action="Add source (e.g., 'via Google Maps as of [date]') or remove specific time claims",
            acceptance_test="Every travel time claim has inline source",
        ))

    # Check RERA mentioned in project context but no registration number provided
    text_lower = text.lower()
    rera_project_claim = bool(re.search(
        r"(?i)(?:rera\s+registered|registered\s+(?:with|under)\s+(?:\w+\s+)?rera|rera\s+registration)",
        text,
    ))
    rera_number_present = bool(re.search(
        r"(?:rera|registration)\s*(?:no\.?|number|#)\s*[:.]?\s*[A-Z0-9/-]+",
        text, re.IGNORECASE,
    ))
    if rera_project_claim and not rera_number_present:
        issue_counter[0] += 1
        issues.append(AuditIssue(
            issue_id=f"CG-CONTENT-{issue_counter[0]:03d}",
            category=IssueCategory.RERA_COMPLIANCE,
            severity=Severity.HIGH,
            owner=Owner.ROI,
            summary="RERA mentioned but no registration number provided",
            recommended_action="Add the actual RERA registration number with portal verification link",
            acceptance_test="RERA registration number is visible and verifiable",
            google_rule="CONTENT-RERA-001",
        ))

    # Check area claims not labeled as carpet area
    area_claims = re.findall(r"[\d,]+\s+sq\.?\s*ft\.?", text)
    if area_claims and not re.search(r"(?i)carpet\s+area", text):
        issue_counter[0] += 1
        issues.append(AuditIssue(
            issue_id=f"CG-CONTENT-{issue_counter[0]:03d}",
            category=IssueCategory.RERA_COMPLIANCE,
            severity=Severity.HIGH,
            owner=Owner.ROI,
            summary=f"Area figures ({len(area_claims)} mentions) not labeled as carpet area",
            recommended_action="Specify whether figures are carpet area (RERA) or super built-up. RERA mandates carpet area disclosure.",
            acceptance_test="All area figures explicitly labeled as carpet area or super built-up",
            google_rule="CONTENT-RERA-002",
        ))

    # Check keyword stuffing (same phrase 8+ times)
    words_total = len(text.split())
    if words_total > 200:
        text_lower_full = text.lower()
        for kw_len in range(2, 5):
            word_list = text_lower_full.split()
            ngrams = [" ".join(word_list[j:j+kw_len]) for j in range(len(word_list) - kw_len + 1)]
            from collections import Counter
            counts = Counter(ngrams)
            for phrase, count in counts.most_common(5):
                if count >= 8 and len(phrase) > 10:
                    issue_counter[0] += 1
                    issues.append(AuditIssue(
                        issue_id=f"CG-CONTENT-{issue_counter[0]:03d}",
                        category=IssueCategory.PROHIBITED_LANGUAGE,
                        severity=Severity.MEDIUM,
                        owner=Owner.ROI,
                        summary=f"Keyword stuffing: '{phrase}' appears {count} times",
                        recommended_action="Reduce repetition. Use synonyms and natural phrasing.",
                        acceptance_test="No phrase repeated more than 7 times in one article",
                        google_rule="SPAM-KEYWORD-001",
                    ))
                    break
            else:
                continue
            break

    # Check for missing internal links
    if "http" not in text and "[" not in text:
        issue_counter[0] += 1
        issues.append(AuditIssue(
            issue_id=f"CG-CONTENT-{issue_counter[0]:03d}",
            category=IssueCategory.INTERNAL_LINKS,
            severity=Severity.HIGH,
            owner=Owner.ROI,
            summary="No internal or external links found in content",
            recommended_action="Add 3-5 internal links and 1-3 external authority links",
            acceptance_test="At least 3 internal links and 1 external authority link present",
        ))

    # Check for missing image references
    if not re.search(r"!\[|<img|\.(?:jpg|jpeg|png|webp|avif|svg)", text, re.IGNORECASE):
        issue_counter[0] += 1
        issues.append(AuditIssue(
            issue_id=f"CG-CONTENT-{issue_counter[0]:03d}",
            category=IssueCategory.IMAGE_SEO,
            severity=Severity.MEDIUM,
            owner=Owner.ROI,
            summary="No images found in content",
            recommended_action="Add 1 hero image and 2-4 supporting visuals with descriptive alt text",
            acceptance_test="Hero image + 2 supporting images with specific alt text",
        ))

    # Thin content check
    if words_total < 800:
        issue_counter[0] += 1
        issues.append(AuditIssue(
            issue_id=f"CG-CONTENT-{issue_counter[0]:03d}",
            category=IssueCategory.AI_READINESS,
            severity=Severity.HIGH,
            owner=Owner.ROI,
            summary=f"Thin content: only {words_total} words (minimum 800 for ranking potential)",
            recommended_action="Expand content to at least 1200-1500 words with substantive sections",
            acceptance_test="Word count >= 1200",
            google_rule="CONTENT-THIN-001",
        ))

    # Body-text CTA spam ("Read more!", "Click here")
    body_cta_count = len(re.findall(
        r"(?i)\b(?:read\s+more|click\s+here|click\s+to|know\s+more|learn\s+more)\s*[!.]",
        text,
    ))
    if body_cta_count >= 2:
        issue_counter[0] += 1
        issues.append(AuditIssue(
            issue_id=f"CG-CONTENT-{issue_counter[0]:03d}",
            category=IssueCategory.PROHIBITED_LANGUAGE,
            severity=Severity.MEDIUM,
            owner=Owner.ROI,
            summary=f"CTA spam: {body_cta_count} generic 'read more/click here' CTAs in body text",
            recommended_action="Replace with descriptive anchor text linking to specific content",
            acceptance_test="No generic 'read more' or 'click here' CTAs in body",
            google_rule="SPAM-CLICKBAIT-002",
        ))


def _check_truth_layer(text: str, issues: list[AuditIssue], issue_counter: list[int],
                       truth_dir=None):
    """Enforce the registry's `prohibited_wording` against the content.

    These phrases come from county_context/, not from this file, so the
    editorial team can ban new wording by editing YAML rather than Python.

    A phrase is skipped when the paragraph containing it was already flagged
    for infrastructure or prohibited language, so a claim the built-in
    patterns catch is not reported twice.
    """
    layer = load_truth_layer(truth_dir) if truth_dir else load_truth_layer()
    if not layer.prohibited_wording:
        return

    already_flagged = {
        i.paragraph for i in issues
        if i.paragraph is not None and i.category in (
            IssueCategory.INFRASTRUCTURE_STATUS, IssueCategory.PROHIBITED_LANGUAGE,
        )
    }

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    for phrase in layer.prohibited_wording:
        pattern = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
        for idx, para in enumerate(paragraphs, 1):
            if idx in already_flagged or not pattern.search(para):
                continue
            issue_counter[0] += 1
            issues.append(AuditIssue(
                issue_id=f"CG-TRUTH-{issue_counter[0]:03d}",
                category=IssueCategory.PROHIBITED_LANGUAGE,
                severity=Severity.HIGH,
                owner=Owner.ROI,
                summary=f"Registry-prohibited wording: '{phrase}'",
                paragraph=idx,
                claim=para[:200],
                reason="Listed under prohibited_wording in the County Group truth layer",
                recommended_action=f"Remove or rephrase '{phrase}'",
                acceptance_test=f"No '{phrase}' wording remains",
                editorial_rule="TRUTH_LAYER_PROHIBITED",
            ))
            already_flagged.add(idx)


# Cities a project could be wrongly placed in. Checked only against the city
# the registry records for a project the content actually names.
_NCR_CITIES = ["Noida", "Greater Noida", "Gurugram", "Gurgaon", "Ghaziabad", "Faridabad", "Delhi"]

# A city name followed by any of these is part of a larger proper noun — a
# road, an airport, or the region — and says nothing about where a project is.
# "Delhi NCR", "Greater Noida Expressway" and "Noida International Airport"
# must never be read as claims that a project sits in Delhi or Greater Noida.
_CITY_COMPOUND_SUFFIX = (
    r"(?!\s*[-–]?\s*(?:NCR|Expressway|Express\s*way|Airport|Metro|Flyway|"
    r"Authority|Link\s+Road|Development|Region|International))"
)

# Only these may sit between the project name and the location assertion.
# Anything else — notably a colon followed by a keyword list — usually means
# the preposition belongs to a different phrase ("flats in Ghaziabad"), not
# to the project.
_PROJECT_APPOSITIVE = (
    r"(?:\s+(?:project|development|residences?|apartments?|complex|society|"
    r"towers?|by\s+County\s+Group))?"
)

# The city must be asserted as the project's location, not merely appear near
# it. "Clove County on the Greater Noida Expressway" is not a location claim;
# "Clove County in Greater Noida" is.
_LOCATION_ASSERTION = (
    r"(?:\s*,\s*|\s+(?:in|at|near\s+by|within)\s+|"
    r"\s+(?:is\s+|are\s+)?(?:located|situated|positioned|based)\s+(?:in|at)\s+)"
)

# Which RERA authority governs which state. Citing the wrong one is a
# compliance error, not a typo — the buyer cannot verify the registration.
_RERA_AUTHORITY_BY_STATE = {
    "uttar pradesh": "UP-RERA",
    "haryana": "HARERA",
}


def _near(text: str, anchor: str, target: str, window: int = 220):
    """Find `target` within `window` characters of `anchor`, in either order.

    Sentence-bounded matching is unreliable here because Indian real estate
    copy is full of abbreviations ("sq. ft.", "Pvt. Ltd.") that a period-based
    boundary treats as a sentence end.
    """
    a_re = re.compile(re.escape(anchor), re.IGNORECASE)
    t_re = re.compile(r"\b" + re.escape(target) + r"\b", re.IGNORECASE)

    for a in a_re.finditer(text):
        lo = max(0, a.start() - window)
        hi = min(len(text), a.end() + window)
        t = t_re.search(text, lo, hi)
        if t:
            span_lo, span_hi = min(a.start(), t.start()), max(a.end(), t.end())
            return text[span_lo:span_hi]
    return None


def _check_projects(text: str, issues: list[AuditIssue], issue_counter: list[int],
                    layer):
    """Verify claims made about a named project against the registry.

    Only runs for projects the content actually names, so a blog about Clove
    County is never judged against Center Court's facts.
    """
    for project in layer.projects:
        if not re.search(r"\b" + re.escape(project.name) + r"\b", text, re.IGNORECASE):
            continue

        # Wrong city for a named project.
        if project.city:
            for city in _NCR_CITIES:
                if city.lower() == project.city.lower():
                    continue
                # "Gurgaon" and "Gurugram" are the same place.
                if {city.lower(), project.city.lower()} == {"gurgaon", "gurugram"}:
                    continue
                # Require an explicit "<project> in <city>" style assertion.
                assertion = re.compile(
                    re.escape(project.name)
                    + _PROJECT_APPOSITIVE
                    + _LOCATION_ASSERTION
                    + r"(?:the\s+)?"
                    + re.escape(city)
                    + r"\b"
                    + _CITY_COMPOUND_SUFFIX,
                    re.IGNORECASE,
                )
                found = assertion.search(text)
                match = found.group(0) if found else None
                if match:
                    issue_counter[0] += 1
                    issues.append(AuditIssue(
                        issue_id=f"CG-PROJECT-{issue_counter[0]:03d}",
                        category=IssueCategory.FACTUAL_ERROR,
                        severity=Severity.CRITICAL,
                        owner=Owner.ROI,
                        summary=f"{project.name} placed in {city}; registry says {project.city}",
                        claim=match[:200],
                        evidence_source=project.project_page,
                        verified_status=f"{project.name} is in {project.city}"
                                        + (f", {project.state}" if project.state else ""),
                        recommended_action=f"Correct the location to {project.city}",
                        acceptance_test=f"{project.name} is described as being in {project.city}",
                    ))
                    break

        # Wrong RERA authority for the project's state.
        expected = project.rera_authority or _RERA_AUTHORITY_BY_STATE.get(
            (project.state or "").lower()
        )
        if expected:
            wrong = [a for a in ("UP-RERA", "UPRERA", "HARERA")
                     if a.replace("-", "").lower() != expected.replace("-", "").lower()]
            for authority in wrong:
                match = _near(text, project.name, authority, window=320)
                if match:
                    issue_counter[0] += 1
                    issues.append(AuditIssue(
                        issue_id=f"CG-PROJECT-{issue_counter[0]:03d}",
                        category=IssueCategory.RERA_COMPLIANCE,
                        severity=Severity.CRITICAL,
                        owner=Owner.ROI,
                        summary=f"{project.name} cited under {authority}; it is registered with {expected}",
                        claim=match[:200],
                        verified_status=f"{project.name} is registered with {expected}",
                        recommended_action=f"Cite {expected} and link its portal",
                        acceptance_test=f"Only {expected} is cited for {project.name}",
                        google_rule="CONTENT-RERA-003",
                    ))
                    break

        # Super area presented without carpet area, for a project we have
        # both figures for. RERA makes carpet area the disclosable number.
        supers = project.super_areas()
        if supers and not re.search(r"(?i)carpet\s+area", text):
            for value in supers:
                if re.search(rf"\b{value}\b", text):
                    issue_counter[0] += 1
                    issues.append(AuditIssue(
                        issue_id=f"CG-PROJECT-{issue_counter[0]:03d}",
                        category=IssueCategory.RERA_COMPLIANCE,
                        severity=Severity.HIGH,
                        owner=Owner.ROI,
                        summary=f"{project.name} super area {value} sq ft quoted with no carpet area",
                        claim=f"{value} sq ft",
                        verified_status=f"Registry carpet areas: {project.carpet_areas()}",
                        recommended_action="State the carpet area alongside, and label which is which",
                        acceptance_test="Carpet area is stated and labelled wherever super area appears",
                        google_rule="CONTENT-RERA-002",
                    ))
                    break

        # Project-specific bans declared in the project YAML.
        for rule in project.prohibited:
            issue_counter[0] += 1
            issues.append(AuditIssue(
                issue_id=f"CG-PROJECT-{issue_counter[0]:03d}",
                category=IssueCategory.MISSING_EVIDENCE,
                severity=Severity.INFO,
                owner=Owner.ROI,
                summary=f"Reviewer note for {project.name}: {rule}",
                recommended_action="Confirm the content does not do this",
                acceptance_test=rule,
                editorial_rule="PROJECT_SPECIFIC_RULE",
            ))
            break  # one reminder per project, not one per rule


def _check_links(text: str, issues: list[AuditIssue], issue_counter: list[int],
                 layer):
    """Check the links in a post: are they present, and do they resolve to
    URLs the registry knows about?

    A link to a County page that is not in the registry is usually a typo or
    a dead campaign URL — the kind of thing that quietly leaks link equity.
    """
    md_links = re.findall(r"\[([^\]]*)\]\((https?://[^)\s]+)\)", text)
    bare = re.findall(r"(?<![(\[])\bhttps?://[^\s)\]]+", text)
    urls = [u for _, u in md_links] + bare

    if not urls:
        return  # absence of links is already reported elsewhere

    known = set(layer.known_urls) | {
        _normalise_url(p.project_page) for p in layer.projects if p.project_page
    }
    already_unverified = set(layer.unverified_urls)

    internal = [u for u in urls if "countygroup.in" in u or "cleocounty.com" in u]
    external = [u for u in urls if u not in internal]

    seen: set[str] = set()
    for url in internal:
        stem = _normalise_url(url)
        if not known or stem in known or stem in seen:
            continue
        # Blog-to-blog links are ordinary internal linking and are not
        # expected to appear in the project URL registry.
        path = stem.partition("/")[2]
        if path.startswith("blog/"):
            continue
        seen.add(stem)
        # The audit is offline, so it cannot tell a dead URL from one simply
        # missing from the registry. Report it as needing verification.
        note = ("already listed as unverified in site_urls.yaml"
                if stem in already_unverified else "not listed in site_urls.yaml")
        issue_counter[0] += 1
        issues.append(AuditIssue(
            issue_id=f"CG-LINK-{issue_counter[0]:03d}",
            category=IssueCategory.INTERNAL_LINKS,
            severity=Severity.LOW,
            owner=Owner.INTERNAL,
            summary=f"Internal URL needs verification: {stem}",
            claim=url,
            reason=note,
            recommended_action="Run `agent links` to check it resolves, then add it to "
                               "county_context/site_urls.yaml or correct the link",
            acceptance_test="Every internal link resolves and is listed in site_urls.yaml",
        ))

    # Anchor text quality: generic anchors waste the internal link.
    for anchor, url in md_links:
        if "countygroup.in" not in url:
            continue
        if anchor.strip().lower() in {"here", "click here", "read more", "this", "link", "know more"}:
            issue_counter[0] += 1
            issues.append(AuditIssue(
                issue_id=f"CG-LINK-{issue_counter[0]:03d}",
                category=IssueCategory.INTERNAL_LINKS,
                severity=Severity.MEDIUM,
                owner=Owner.ROI,
                summary=f"Generic anchor text '{anchor.strip()}' on an internal link",
                claim=f"[{anchor}]({url})",
                recommended_action="Use descriptive anchor text naming the destination",
                acceptance_test="No internal link uses generic anchor text",
                google_rule="CONTENT-LINK-001",
            ))

    if not external:
        issue_counter[0] += 1
        issues.append(AuditIssue(
            issue_id=f"CG-LINK-{issue_counter[0]:03d}",
            category=IssueCategory.EXTERNAL_LINKS,
            severity=Severity.MEDIUM,
            owner=Owner.ROI,
            summary="No external authority links — every link points back to County Group",
            recommended_action="Cite 2-3 external sources (UP-RERA, HARERA, ANAROCK, PIB, official news)",
            acceptance_test="At least 2 external authority links present",
        ))


def _run_gates(analysis: ContentAnalysis):
    """Run publication gates and determine publishability."""
    critical_issues = [i for i in analysis.issues if i.severity == Severity.CRITICAL]
    high_issues = [i for i in analysis.issues if i.severity == Severity.HIGH]

    # Gate 1: Factual Accuracy
    factual_fails = [i for i in analysis.issues if i.category in (
        IssueCategory.FACTUAL_ERROR, IssueCategory.STALE_CLAIM,
        IssueCategory.INFRASTRUCTURE_STATUS,
    )]
    analysis.gates.append(GateResult(
        gate_name="Factual Accuracy",
        gate_number=1,
        status=GateStatus.FAIL if factual_fails else GateStatus.PASS,
        details=f"{len(factual_fails)} factual issues" if factual_fails else "No factual issues",
        issues=factual_fails,
    ))

    # Gate 2: RERA & Legal Compliance
    compliance_fails = [i for i in analysis.issues if i.category in (
        IssueCategory.RERA_COMPLIANCE, IssueCategory.PROHIBITED_LANGUAGE,
    )]
    analysis.gates.append(GateResult(
        gate_name="RERA & Legal Compliance",
        gate_number=2,
        status=GateStatus.FAIL if compliance_fails else GateStatus.PASS,
        details=f"{len(compliance_fails)} compliance issues" if compliance_fails else "Compliant",
        issues=compliance_fails,
    ))

    # Gate 3: Technical SEO
    seo_fails = [i for i in analysis.issues if i.category in (
        IssueCategory.HEADING_STRUCTURE, IssueCategory.META_TITLE,
        IssueCategory.META_DESCRIPTION, IssueCategory.CANONICAL,
    ) and i.severity in (Severity.CRITICAL, Severity.HIGH)]
    analysis.gates.append(GateResult(
        gate_name="Technical SEO Eligibility",
        gate_number=3,
        status=GateStatus.FAIL if seo_fails else GateStatus.PASS,
        details=f"{len(seo_fails)} SEO issues" if seo_fails else "SEO basics pass",
        issues=seo_fails,
    ))

    # Gate 4: Deployment Integrity
    deploy_fails = [i for i in analysis.issues if i.category in (
        IssueCategory.SCHEMA_MISSING, IssueCategory.SCHEMA_INVALID,
        IssueCategory.DEPLOYMENT,
    )]
    analysis.gates.append(GateResult(
        gate_name="Deployment Integrity",
        gate_number=4,
        status=GateStatus.FAIL if deploy_fails else GateStatus.WARNING,
        details=f"{len(deploy_fails)} deployment issues" if deploy_fails else "Check post-deployment",
        issues=deploy_fails,
    ))

    # Publishability
    any_gate_fail = any(g.status == GateStatus.FAIL for g in analysis.gates)
    analysis.publishable = not any_gate_fail and not critical_issues


def audit_text(text: str, file_path: str = "unknown") -> ContentAnalysis:
    """Audit blog content from raw text. Returns structured analysis with issues."""
    analysis = ContentAnalysis(file_path=file_path)

    # Basic stats
    words = text.split()
    analysis.word_count = len(words)
    analysis.paragraph_count = len([p for p in text.split("\n\n") if p.strip()])

    issue_counter = [0]

    # Extract and check metadata
    analysis.metadata = _extract_metadata_from_text(text)
    _check_metadata(analysis.metadata, analysis.issues, issue_counter)

    # Paragraph-level content checks
    _check_paragraphs(text, analysis.issues, issue_counter)

    # Registry-driven checks (county_context/)
    _check_truth_layer(text, analysis.issues, issue_counter)
    _layer = load_truth_layer()
    _check_projects(text, analysis.issues, issue_counter, _layer)
    _check_links(text, analysis.issues, issue_counter, _layer)

    # Run publication gates
    _run_gates(analysis)

    # Score (simplified — the full scoring is in analyze_blog.py)
    critical = len([i for i in analysis.issues if i.severity == Severity.CRITICAL])
    high = len([i for i in analysis.issues if i.severity == Severity.HIGH])
    medium = len([i for i in analysis.issues if i.severity == Severity.MEDIUM])
    analysis.score = max(0, 100 - (critical * 15) - (high * 8) - (medium * 3))

    return analysis


def audit_file(file_path: str) -> ContentAnalysis:
    """Audit a blog file (plain text, markdown, or DOCX)."""
    path = Path(file_path)

    if path.suffix.lower() == ".docx":
        text = _read_docx(path)
    else:
        text = path.read_text(encoding="utf-8", errors="replace")

    return audit_text(text, file_path=str(path))


def _read_docx(path: Path) -> str:
    """Extract text from a DOCX file."""
    try:
        from docx import Document
    except ImportError:
        # Fallback: extract text using zipfile (basic but works without python-docx)
        return _read_docx_basic(path)

    doc = Document(str(path))
    lines = []
    for para in doc.paragraphs:
        style = para.style.name if para.style else ""
        text = para.text.strip()
        if not text:
            lines.append("")
            continue

        # Convert Word heading styles to markdown
        if "Heading 1" in style:
            lines.append(f"# {text}")
        elif "Heading 2" in style:
            lines.append(f"## {text}")
        elif "Heading 3" in style:
            lines.append(f"### {text}")
        elif "Heading 4" in style:
            lines.append(f"#### {text}")
        else:
            lines.append(text)

    return "\n\n".join(lines)


def _read_docx_basic(path: Path) -> str:
    """Basic DOCX reader using only stdlib (zipfile + xml)."""
    import zipfile
    import xml.etree.ElementTree as ET

    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path) as z:
        with z.open("word/document.xml") as f:
            tree = ET.parse(f)

    paragraphs = []
    for para in tree.findall(".//w:p", ns):
        texts = [t.text for t in para.findall(".//w:t", ns) if t.text]
        if texts:
            paragraphs.append("".join(texts))

    return "\n\n".join(paragraphs)
