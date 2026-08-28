# Blog Audit Report

**File:** blogs/roi-incoming/flats-in-gurgaon-writer-doc.md
**Score:** 51/100
**Publishable:** No
**Word Count:** 1949
**Paragraphs:** 58
**Total Issues:** 11

## Publication Gates

| Gate | Status | Details |
|------|--------|---------|
| 1. Factual Accuracy | PASS | No factual issues |
| 2. RERA & Legal Compliance | FAIL | 3 compliance issues |
| 3. Technical SEO Eligibility | FAIL | 2 SEO issues |
| 4. Deployment Integrity | WARN | Check post-deployment |

## HIGH Issues (5)

### CG-META-001: No meta title found

- **Owner:** ROI
- **Category:** meta_title
- **Action:** Add a unique meta title, 30-60 characters
- **Acceptance test:** Meta title present and 30-60 characters

### CG-META-002: No meta description found

- **Owner:** ROI
- **Category:** meta_description
- **Action:** Add a unique meta description, 120-160 characters
- **Acceptance test:** Meta description present and 120-160 characters

### CG-CONTENT-003: 3 travel time claim(s) without source attribution

- **Owner:** ROI
- **Category:** unsupported_claim
- **Action:** Add source (e.g., 'via Google Maps as of [date]') or remove specific time claims
- **Acceptance test:** Every travel time claim has inline source

### CG-CONTENT-004: RERA mentioned but no registration number provided

- **Owner:** ROI
- **Category:** rera_compliance
- **Action:** Add the actual RERA registration number with portal verification link
- **Acceptance test:** RERA registration number is visible and verifiable
- **Google rule:** CONTENT-RERA-001

### CG-CONTENT-005: Area figures (8 mentions) not labeled as carpet area

- **Owner:** ROI
- **Category:** rera_compliance
- **Action:** Specify whether figures are carpet area (RERA) or super built-up. RERA mandates carpet area disclosure.
- **Acceptance test:** All area figures explicitly labeled as carpet area or super built-up
- **Google rule:** CONTENT-RERA-002

## MEDIUM Issues (3)

### CG-CONTENT-006: Keyword stuffing: 'center court' appears 26 times

- **Owner:** ROI
- **Category:** prohibited_language
- **Action:** Reduce repetition. Use synonyms and natural phrasing.
- **Acceptance test:** No phrase repeated more than 7 times in one article
- **Google rule:** SPAM-KEYWORD-001

### CG-CONTENT-007: No images found in content

- **Owner:** ROI
- **Category:** image_seo
- **Action:** Add 1 hero image and 2-4 supporting visuals with descriptive alt text
- **Acceptance test:** Hero image + 2 supporting images with specific alt text

### CG-LINK-011: No external authority links — every link points back to County Group

- **Owner:** ROI
- **Category:** external_links
- **Action:** Cite 2-3 external sources (UP-RERA, HARERA, ANAROCK, PIB, official news)
- **Acceptance test:** At least 2 external authority links present

## LOW Issues (2)

### CG-LINK-009: Internal URL needs verification: countygroup.in/flats-in-gurugram

- **Owner:** INTERNAL
- **Category:** internal_links
- **Found:** "https://www.countygroup.in/flats-in-gurugram"
- **Reason:** already listed as unverified in site_urls.yaml
- **Action:** Run `agent links` to check it resolves, then add it to county_context/site_urls.yaml or correct the link
- **Acceptance test:** Every internal link resolves and is listed in site_urls.yaml

### CG-LINK-010: Internal URL needs verification: countygroup.in/contact.php

- **Owner:** INTERNAL
- **Category:** internal_links
- **Found:** "https://www.countygroup.in/contact.php"
- **Reason:** already listed as unverified in site_urls.yaml
- **Action:** Run `agent links` to check it resolves, then add it to county_context/site_urls.yaml or correct the link
- **Acceptance test:** Every internal link resolves and is listed in site_urls.yaml

## INFO Issues (1)

### CG-PROJECT-008: Reviewer note for The Center Court: Describing this project as being in Noida or Uttar Pradesh

- **Owner:** ROI
- **Category:** missing_evidence
- **Action:** Confirm the content does not do this
- **Acceptance test:** Describing this project as being in Noida or Uttar Pradesh
- **Editorial rule:** PROJECT_SPECIFIC_RULE

## Issues by Owner

| Owner | Critical | High | Medium | Low | Total |
|-------|----------|------|--------|-----|-------|
| ROI | 0 | 5 | 3 | 0 | 9 |
| INTERNAL | 0 | 0 | 0 | 2 | 2 |
