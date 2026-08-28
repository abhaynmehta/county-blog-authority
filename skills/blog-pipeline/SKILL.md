---
name: blog-pipeline
description: >
  End-to-end County Group blog pipeline: topic → research → brief → draft →
  fact-check → audit → schema → package. Chains existing sub-skills with
  truth-layer validation at each gate. Produces a publication-ready blog with
  audit report, JSON-LD schema, and agency handoff documents.
user-invokable: true
argument-hint: "<topic-or-file> [--audit-only] [--generate] [--full]"
license: MIT
metadata:
  author: County Group
  version: "0.1.0"
---

# County Group Blog Pipeline

End-to-end pipeline from topic (or submitted DOCX) to publication-ready package.

## Modes

| Mode | Command | What happens |
|------|---------|-------------|
| Audit Only | `/blog pipeline --audit-only <file>` | Audit existing content, no rewrite |
| Generate | `/blog pipeline --generate <topic>` | Generate new blog from scratch |
| Full | `/blog pipeline --full <file>` | Audit submitted blog, then rewrite with fixes |

## Pipeline Stages

### Stage 1: Context Load
Load truth layer before any content work:
1. Read `BRAND.md` — positioning, USPs, prohibited language
2. Read `VOICE.md` — tone, style, conventions
3. Read `EDITORIAL_POLICY.md` — gates, owner rules, refresh policy
4. Read relevant `county_context/projects/*.yaml` — project data
5. Read `county_context/claims/*.yaml` — permitted claims
6. Read `county_context/sources/registry.yaml` — source tiers

### Stage 2: Input Processing
- **If topic**: proceed to Stage 3 (research)
- **If file (DOCX/MD/HTML)**: parse content, extract metadata, proceed to Stage 4 (audit)

### Stage 3: Research & Brief (generate mode only)
1. Run `/blog brief` workflow:
   - WebSearch for top-ranking content on the topic
   - Identify primary + secondary keywords
   - Analyze SERP features (AI Overviews, PAA, featured snippets)
   - Select content template from `indian-real-estate/content-templates.md`
2. Load entity model from `indian-real-estate/entity-model.md`
3. Cross-reference all project claims against truth layer
4. Produce brief with:
   - Target keyword + secondaries
   - Content template + required sections
   - County Group data points to weave in (from YAML)
   - Internal link targets (from `internal_links.yaml`)
   - Facts that MUST be verified (airport status, RERA numbers)

### Stage 4: Draft / Audit
- **Generate mode**: Write draft using `/blog write` workflow with truth-layer constraints
- **Audit mode**: Run `search_authority.audit_text()` on the input content
- **Full mode**: Audit first, then rewrite flagged sections

### Stage 5: Fact-Check Gate
Run the audit engine on the draft:
```python
from search_authority.content_auditor import audit_text
result = audit_text(content)
```
Check all 6 publication gates:
1. Factual Accuracy — no stale infrastructure, no unsupported claims
2. RERA & Legal Compliance — no prohibited language, no false RERA claims
3. Technical SEO — proper headings, meta tags, links, images
4. Deployment Integrity — schema present, meta deployable
5. Content Quality — score ≥ 80
6. Brand Alignment — voice match, USPs present where relevant

If any PASS/FAIL gate fails → loop back to Stage 4 with specific fixes.

### Stage 6: Schema Generation
```python
from search_authority.schema import generate_blog_schema, generate_breadcrumb_schema, schemas_to_jsonld
```
Generate:
- BlogPosting JSON-LD (headline, description, datePublished, author as Organization)
- BreadcrumbList JSON-LD (Home > Blog > [Category] > [Post])
- Validate headline appears in visible text

### Stage 7: Package
Output the final package:
```
output/
  [slug].md                    # Publication-ready blog content
  [slug]-schema.json           # JSON-LD for AGO to deploy
  [slug]-audit-report.md       # Full audit report
  [slug]-audit-report.json     # Machine-readable audit
  [slug]-roi-handoff.md        # ROI-specific action items (if any remain)
  [slug]-ago-handoff.md        # AGO deployment checklist
```

## Truth Layer Integration

Every claim in the content is checked against the truth layer:
- Project facts → `county_context/projects/*.yaml`
- Delivery claims → `county_context/claims/delivery.yaml`
- Amenity claims → `county_context/claims/amenities.yaml`
- Infrastructure status → `county_context/claims/infrastructure.yaml`
- Source citations → `county_context/sources/registry.yaml`
- Geography references → `county_context/geography/ncr.yaml`

## AEO/GEO Baked In

Not a separate phase — baked into every stage:
- **Brief**: targets AI Overview surfaces, structures for extraction
- **Draft**: answer-first paragraphs, concise definitions, structured data
- **Schema**: JSON-LD for entity recognition
- **Audit**: checks citation-readiness (source attribution, structured answers)

## Running the Pipeline

### Via CLI
```bash
cd ~/Desktop/county-blog-authority
source .venv/bin/activate

# Audit a submitted blog
python3 -m search_authority content-audit blog.docx --fixes --json

# Generate ROI/AGO reports
python3 -m search_authority roi-report blog.docx
python3 -m search_authority ago-report blog.docx
```

### Via Claude Code
```
/blog pipeline --audit-only path/to/blog.docx
/blog pipeline --generate "Sector 150 Noida buyer guide"
/blog pipeline --full path/to/submitted-blog.docx
```
