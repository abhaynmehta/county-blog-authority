# Blog Audit Report

**File:** blogs/roi-incoming/clove-county-location-map.md
**Score:** 72/100
**Publishable:** Yes
**Word Count:** 253
**Paragraphs:** 12
**Total Issues:** 8

## Publication Gates

| Gate | Status | Details |
|------|--------|---------|
| 1. Factual Accuracy | PASS | No factual issues |
| 2. RERA & Legal Compliance | PASS | Compliant |
| 3. Technical SEO Eligibility | PASS | SEO basics pass |
| 4. Deployment Integrity | WARN | Check post-deployment |

## HIGH Issues (2)

### CG-CONTENT-002: 1 travel time claim(s) without source attribution

- **Owner:** ROI
- **Category:** unsupported_claim
- **Action:** Add source (e.g., 'via Google Maps as of [date]') or remove specific time claims
- **Acceptance test:** Every travel time claim has inline source

### CG-CONTENT-005: Thin content: only 253 words (minimum 800 for ranking potential)

- **Owner:** ROI
- **Category:** ai_readiness
- **Action:** Expand content to at least 1200-1500 words with substantive sections
- **Acceptance test:** Word count >= 1200
- **Google rule:** CONTENT-THIN-001

## MEDIUM Issues (4)

### CG-META-001: Meta description too short (102 chars)

- **Owner:** ROI
- **Category:** meta_description
- **Found:** "Find Clove County in Sector 151, Noida. Access via Noida-Greater Noida Expressway and Aqua Line Metro."
- **Action:** Expand to 120-160 characters for optimal SERP display
- **Acceptance test:** Description is 120-160 characters

### CG-CONTENT-003: Keyword stuffing: 'clove county' appears 8 times

- **Owner:** ROI
- **Category:** spam_signal
- **Action:** Reduce repetition. Use synonyms and natural phrasing.
- **Acceptance test:** No phrase repeated more than 7 times in one article
- **Google rule:** SPAM-KEYWORD-001

### CG-CONTENT-004: No images found in content

- **Owner:** ROI
- **Category:** image_seo
- **Action:** Add 1 hero image and 2-4 supporting visuals with descriptive alt text
- **Acceptance test:** Hero image + 2 supporting images with specific alt text

### CG-LINK-008: No external authority links — every link points back to County Group

- **Owner:** ROI
- **Category:** external_links
- **Action:** Cite 2-3 external sources (UP-RERA, HARERA, ANAROCK, PIB, official news)
- **Acceptance test:** At least 2 external authority links present

## LOW Issues (1)

### CG-LINK-007: Internal URL needs verification: countygroup.in/clovecounty/location-map

- **Owner:** INTERNAL
- **Category:** internal_links
- **Found:** "https://www.countygroup.in/clovecounty/location-map"
- **Reason:** not listed in site_urls.yaml
- **Action:** Run `agent links` to check it resolves, then add it to county_context/site_urls.yaml or correct the link
- **Acceptance test:** Every internal link resolves and is listed in site_urls.yaml

## INFO Issues (1)

### CG-PROJECT-006: Reviewer note for Clove County: Publishing a Clove County carpet or super area figure; none is registered yet

- **Owner:** ROI
- **Category:** missing_evidence
- **Action:** Confirm the content does not do this
- **Acceptance test:** Publishing a Clove County carpet or super area figure; none is registered yet
- **Editorial rule:** PROJECT_SPECIFIC_RULE

## Issues by Owner

| Owner | Critical | High | Medium | Low | Total |
|-------|----------|------|--------|-----|-------|
| ROI | 0 | 2 | 4 | 0 | 7 |
| INTERNAL | 0 | 0 | 0 | 1 | 1 |
