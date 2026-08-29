# Blog Audit Report

**File:** blogs/roi-incoming/clove-county-nearby-places.md
**Score:** 83/100
**Publishable:** Yes
**Word Count:** 269
**Paragraphs:** 19
**Total Issues:** 6

## Publication Gates

| Gate | Status | Details |
|------|--------|---------|
| 1. Factual Accuracy | PASS | No factual issues |
| 2. RERA & Legal Compliance | PASS | Compliant |
| 3. Technical SEO Eligibility | PASS | SEO basics pass |
| 4. Deployment Integrity | WARN | Check post-deployment |

## HIGH Issues (1)

### CG-CONTENT-003: Thin content: only 269 words (minimum 800 for ranking potential)

- **Owner:** ROI
- **Category:** ai_readiness
- **Action:** Expand content to at least 1200-1500 words with substantive sections
- **Acceptance test:** Word count >= 1200
- **Google rule:** CONTENT-THIN-001

## MEDIUM Issues (3)

### CG-META-001: Meta description too short (113 chars)

- **Owner:** ROI
- **Category:** meta_description
- **Found:** "Explore schools, hospitals, business hubs, shopping and sports facilities near Clove County in Sector 151, Noida."
- **Action:** Expand to 120-160 characters for optimal SERP display
- **Acceptance test:** Description is 120-160 characters

### CG-CONTENT-002: No images found in content

- **Owner:** ROI
- **Category:** image_seo
- **Action:** Add 1 hero image and 2-4 supporting visuals with descriptive alt text
- **Acceptance test:** Hero image + 2 supporting images with specific alt text

### CG-LINK-006: No external authority links — every link points back to County Group

- **Owner:** ROI
- **Category:** external_links
- **Action:** Cite 2-3 external sources (UP-RERA, HARERA, ANAROCK, PIB, official news)
- **Acceptance test:** At least 2 external authority links present

## LOW Issues (1)

### CG-LINK-005: Internal URL needs verification: countygroup.in/clovecounty/nearby-places

- **Owner:** INTERNAL
- **Category:** internal_links
- **Found:** "https://www.countygroup.in/clovecounty/nearby-places"
- **Reason:** not listed in site_urls.yaml
- **Action:** Run `agent links` to check it resolves, then add it to county_context/site_urls.yaml or correct the link
- **Acceptance test:** Every internal link resolves and is listed in site_urls.yaml

## INFO Issues (1)

### CG-PROJECT-004: Reviewer note for Clove County: Quoting super area as the flat size without naming carpet area

- **Owner:** ROI
- **Category:** missing_evidence
- **Action:** Confirm the content does not do this
- **Acceptance test:** Quoting super area as the flat size without naming carpet area
- **Editorial rule:** PROJECT_SPECIFIC_RULE

## Issues by Owner

| Owner | Critical | High | Medium | Low | Total |
|-------|----------|------|--------|-----|-------|
| ROI | 0 | 1 | 3 | 0 | 5 |
| INTERNAL | 0 | 0 | 0 | 1 | 1 |
