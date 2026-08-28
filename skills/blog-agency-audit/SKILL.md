---
name: blog-agency-audit
description: >
  Audit agency-submitted blog content (DOCX, Google Docs, or pasted text) and produce
  actionable issue reports with owner assignment (ROI/AGO). Per-paragraph analysis
  with exact fixes, not just scores. Specialized for Indian real estate content
  with RERA compliance, infrastructure fact-checking, and County Group brand alignment.
license: MIT
compatibility: Requires Python 3.11+ and search_authority package
metadata:
  author: County Group
  version: "2.2.0"
user-invokable: true
argument-hint: "<file-or-directory> [--roi-report] [--ago-report] [--fixes] [--schema] [--meta]"
---

# Agency Blog Audit

Audit blogs submitted by ROI or AGO agencies. Produces per-paragraph, actionable
findings with owner assignment — not just quality scores.

## Commands

| Command | What it does |
|---------|-------------|
| `/blog agency-audit <file>` | Full audit of one blog file |
| `/blog agency-audit <directory>` | Batch audit all content files in directory |
| `/blog agency-audit --roi-report <path>` | ROI-specific action items only |
| `/blog agency-audit --ago-report <path>` | AGO-specific action items only |
| `/blog agency-audit --compare <docx> <url>` | Compare approved DOCX vs live deployment |

## Workflow

1. **Ingest**: Read DOCX, markdown, HTML, or pasted text
2. **Parse**: Extract metadata, headings, paragraphs, links, images
3. **Audit**: Run content through the search_authority audit engine:
   - RERA & legal compliance check
   - Prohibited language detection
   - Infrastructure status verification (airport, metro, expressway)
   - Unsupported claim detection (percentages, prices, distances)
   - Heading hierarchy validation
   - Meta title/description length and quality
   - Internal/external link presence
   - Image SEO check
   - Brand voice alignment
4. **Classify**: Assign each issue to an owner (ROI or AGO) per EDITORIAL_POLICY.md
5. **Report**: Generate actionable report with:
   - Per-issue: ID, severity, owner, paragraph, claim, fix, acceptance test
   - Publication gate summary (PASS/FAIL for each gate)
   - Owner summary table
   - Optional: ROI-only or AGO-only filtered report

## Running the Audit

### Via CLI (for batch processing, CI, scripts)
```bash
cd ~/Desktop/county-blog-authority
python3 -m search_authority content-audit ./blogs/ --output ./audit-reports/ --fixes --csv
python3 -m search_authority roi-report ./blogs/ --output ./reports/
python3 -m search_authority ago-report ./blogs/ --output ./reports/
```

### Via Claude Code skill
```
/blog agency-audit path/to/blog.docx
/blog agency-audit path/to/blogs/ --roi-report
```

## Context Loading

Before auditing, load:
1. `BRAND.md` — prohibited language, approved terminology, USPs
2. `VOICE.md` — tone and style expectations
3. `EDITORIAL_POLICY.md` — publication gates, owner assignment rules, refresh policy
4. `county_context/claims/` — delivery, amenities, infrastructure claims registry
5. `county_context/sources/registry.yaml` — source tier hierarchy

## Issue Severity Levels

| Severity | Meaning | Publication impact |
|----------|---------|-------------------|
| CRITICAL | Cannot publish | Blocks all gates |
| HIGH | Must fix before publish | Blocks relevant gate |
| MEDIUM | Should fix | Warning, does not block |
| LOW | Nice to have | Advisory |
| INFO | Informational | No action needed |

## Owner Assignment

| Issue type | Owner |
|---|---|
| Content errors (facts, claims, structure, links in content) | ROI |
| Meta title/description quality | ROI |
| Grammar/editorial | ROI |
| Schema not implemented on live site | AGO |
| Title/meta not deployed correctly | AGO |
| Alt text not applied in CMS | AGO |
| Page speed, mobile, canonical | AGO |

## Output Formats

- **Markdown report** — human-readable, shareable with agencies
- **JSON** — machine-readable for dashboard/automation
- **CSV** — all issues across files for spreadsheet analysis
- **Agency handoff** — filtered report for ROI or AGO specifically

## Anti-Patterns

| Anti-pattern | Why |
|---|---|
| Score without actionable fixes | Agencies need exact instructions, not numbers |
| Generic recommendations | "Improve SEO" is useless. Say "Change H4 to H3 in paragraph 11" |
| Skip RERA compliance | Legal risk for the developer |
| Accept "upcoming airport" | Noida International Airport is operational since June 2026 |
| Allow superlatives without evidence | "Best developer" needs RERA-verified delivery data |
