"""Report generators for audit results.

Produces markdown, JSON, and CSV reports from ContentAnalysis objects.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Optional

from .models import ContentAnalysis, Severity, Owner, GateStatus


def generate_markdown_report(analysis: ContentAnalysis, include_fixes: bool = True) -> str:
    """Generate a professional markdown audit report."""
    lines = []
    lines.append(f"# Blog Audit Report")
    lines.append(f"")
    lines.append(f"**File:** {analysis.file_path}")
    lines.append(f"**Score:** {analysis.score}/100")
    lines.append(f"**Publishable:** {'Yes' if analysis.publishable else 'No'}")
    lines.append(f"**Word Count:** {analysis.word_count}")
    lines.append(f"**Paragraphs:** {analysis.paragraph_count}")
    lines.append(f"**Total Issues:** {len(analysis.issues)}")
    lines.append(f"")

    # Gate summary
    lines.append(f"## Publication Gates")
    lines.append(f"")
    lines.append(f"| Gate | Status | Details |")
    lines.append(f"|------|--------|---------|")
    for gate in analysis.gates:
        status_icon = "PASS" if gate.status == GateStatus.PASS else "FAIL" if gate.status == GateStatus.FAIL else "WARN"
        lines.append(f"| {gate.gate_number}. {gate.gate_name} | {status_icon} | {gate.details} |")
    lines.append(f"")

    # Issues by severity
    for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
        severity_issues = [i for i in analysis.issues if i.severity == severity]
        if not severity_issues:
            continue

        lines.append(f"## {severity.value.upper()} Issues ({len(severity_issues)})")
        lines.append(f"")

        for issue in severity_issues:
            lines.append(f"### {issue.issue_id}: {issue.summary}")
            lines.append(f"")
            lines.append(f"- **Owner:** {issue.owner.value}")
            lines.append(f"- **Category:** {issue.category.value}")
            if issue.paragraph:
                lines.append(f"- **Paragraph:** {issue.paragraph}")
            if issue.claim:
                lines.append(f"- **Found:** \"{issue.claim}\"")
            if issue.reason:
                lines.append(f"- **Reason:** {issue.reason}")
            if issue.evidence_source:
                lines.append(f"- **Evidence:** {issue.evidence_source}")
            if issue.verified_status:
                lines.append(f"- **Correct status:** {issue.verified_status}")

            if include_fixes:
                lines.append(f"- **Action:** {issue.recommended_action}")
                if issue.suggested_replacement:
                    lines.append(f"- **Suggested replacement:** \"{issue.suggested_replacement}\"")
                lines.append(f"- **Acceptance test:** {issue.acceptance_test}")

            if issue.google_rule:
                lines.append(f"- **Google rule:** {issue.google_rule}")
            elif issue.editorial_rule:
                lines.append(f"- **Editorial rule:** {issue.editorial_rule}")
            lines.append(f"")

    # Owner summary
    lines.append(f"## Issues by Owner")
    lines.append(f"")
    lines.append(f"| Owner | Critical | High | Medium | Low | Total |")
    lines.append(f"|-------|----------|------|--------|-----|-------|")
    for owner in Owner:
        owner_issues = [i for i in analysis.issues if i.owner == owner]
        if not owner_issues:
            continue
        counts = {s: len([i for i in owner_issues if i.severity == s]) for s in Severity}
        lines.append(
            f"| {owner.value} | {counts[Severity.CRITICAL]} | {counts[Severity.HIGH]} "
            f"| {counts[Severity.MEDIUM]} | {counts[Severity.LOW]} | {len(owner_issues)} |"
        )
    lines.append(f"")

    return "\n".join(lines)


def generate_json_report(analysis: ContentAnalysis) -> str:
    """Generate JSON audit report."""
    return analysis.to_json()


def generate_csv_issues(analyses: list[ContentAnalysis]) -> str:
    """Generate CSV of all issues across multiple files."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Issue ID", "File", "Severity", "Owner", "Category",
        "Paragraph", "Summary", "Claim", "Action", "Acceptance Test",
    ])

    for analysis in analyses:
        for issue in analysis.issues:
            writer.writerow([
                issue.issue_id,
                analysis.file_path,
                issue.severity.value,
                issue.owner.value,
                issue.category.value,
                issue.paragraph or "",
                issue.summary,
                (issue.claim or "")[:100],
                issue.recommended_action,
                issue.acceptance_test,
            ])

    return output.getvalue()


def _clean_quote(text: str, limit: int = 220) -> str:
    """Flatten quoted source text so it stays readable inside the report."""
    collapsed = " ".join(str(text).split())
    if len(collapsed) > limit:
        collapsed = collapsed[:limit].rstrip() + "…"
    return collapsed.replace("“", '"').replace("”", '"')


def generate_agency_handoff(analyses: list[ContentAnalysis], agency: Owner) -> str:
    """Generate a report filtered for a specific agency (ROI or AGO)."""
    lines = []
    lines.append(f"# {agency.value} Action Items")
    lines.append(f"")
    lines.append(f"The following issues require your attention.")
    lines.append(f"")

    total = 0
    for analysis in analyses:
        agency_issues = [i for i in analysis.issues
                         if i.owner == agency or i.owner == Owner.BOTH]
        if not agency_issues:
            continue

        lines.append(f"## {Path(analysis.file_path).name}")
        lines.append("")

        # Worst first, so the blocking problems are read before the nits.
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        agency_issues = sorted(
            agency_issues, key=lambda i: order.get(i.severity.value, 9)
        )

        for issue in agency_issues:
            total += 1
            lines.append(f"### {issue.issue_id} — {issue.severity.value.upper()}")
            lines.append("")
            lines.append(f"**{issue.summary}**")
            lines.append("")

            where = f"Paragraph {issue.paragraph}" if issue.paragraph else None
            if where:
                lines.append(f"- **Where:** {where}")
            if issue.claim:
                quoted = _clean_quote(issue.claim)
                lines.append(f"- **Text in question:** “{quoted}”")
            if issue.reason:
                lines.append(f"- **Why:** {issue.reason}")
            if issue.verified_status:
                lines.append(f"- **Verified fact:** {issue.verified_status}")
            if issue.evidence_source:
                lines.append(f"- **Source:** {issue.evidence_source}")
            lines.append(f"- **Fix:** {issue.recommended_action}")
            lines.append(f"- **Done when:** {issue.acceptance_test}")
            if issue.google_rule:
                lines.append(f"- **Rule:** {issue.google_rule}")
            lines.append("")

    lines.insert(2, f"**Total items: {total}**")
    lines.insert(3, f"")

    return "\n".join(lines)
