# Blog Audit Report

**File:** blogs/roi-incoming/clove-county-masterplan-page.md
**Score:** 75/100
**Publishable:** No
**Word Count:** 652
**Paragraphs:** 20
**Total Issues:** 7

## Publication Gates

| Gate | Status | Details |
|------|--------|---------|
| 1. Factual Accuracy | PASS | No factual issues |
| 2. RERA & Legal Compliance | FAIL | 1 compliance issues |
| 3. Technical SEO Eligibility | PASS | SEO basics pass |
| 4. Deployment Integrity | WARN | Check post-deployment |

## HIGH Issues (2)

### CG-CONTENT-002: Area figures (5 mentions) not labeled as carpet area

- **Owner:** ROI
- **Category:** rera_compliance
- **Action:** Specify whether figures are carpet area (RERA) or super built-up. RERA mandates carpet area disclosure.
- **Acceptance test:** All area figures explicitly labeled as carpet area or super built-up
- **Google rule:** CONTENT-RERA-002

### CG-CONTENT-004: Thin content: only 652 words (minimum 800 for ranking potential)

- **Owner:** ROI
- **Category:** ai_readiness
- **Action:** Expand content to at least 1200-1500 words with substantive sections
- **Acceptance test:** Word count >= 1200
- **Google rule:** CONTENT-THIN-001

## MEDIUM Issues (3)

### CG-META-001: Meta description too short (101 chars)

- **Owner:** ROI
- **Category:** meta_description
- **Found:** "Clove County masterplan. 5 acres, 226 residences, 3 blocks, 8 towers, sports, gardens, Ce La Vi club."
- **Action:** Expand to 120-160 characters for optimal SERP display
- **Acceptance test:** Description is 120-160 characters

### CG-CONTENT-003: No images found in content

- **Owner:** ROI
- **Category:** image_seo
- **Action:** Add 1 hero image and 2-4 supporting visuals with descriptive alt text
- **Acceptance test:** Hero image + 2 supporting images with specific alt text

### CG-LINK-007: No external authority links — every link points back to County Group

- **Owner:** ROI
- **Category:** external_links
- **Action:** Cite 2-3 external sources (UP-RERA, HARERA, ANAROCK, PIB, official news)
- **Acceptance test:** At least 2 external authority links present

## LOW Issues (1)

### CG-LINK-006: Internal URL needs verification: countygroup.in/clovecounty/masterplan

- **Owner:** INTERNAL
- **Category:** internal_links
- **Found:** "https://www.countygroup.in/clovecounty/masterplan"
- **Reason:** not listed in site_urls.yaml
- **Action:** Run `agent links` to check it resolves, then add it to county_context/site_urls.yaml or correct the link
- **Acceptance test:** Every internal link resolves and is listed in site_urls.yaml

## INFO Issues (1)

### CG-PROJECT-005: Reviewer note for Clove County: Quoting super area as the flat size without naming carpet area

- **Owner:** ROI
- **Category:** missing_evidence
- **Action:** Confirm the content does not do this
- **Acceptance test:** Quoting super area as the flat size without naming carpet area
- **Editorial rule:** PROJECT_SPECIFIC_RULE

## Issues by Owner

| Owner | Critical | High | Medium | Low | Total |
|-------|----------|------|--------|-----|-------|
| ROI | 0 | 2 | 3 | 0 | 6 |
| INTERNAL | 0 | 0 | 0 | 1 | 1 |
