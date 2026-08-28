# Blog Audit Report

**File:** blogs/roi-incoming/flats-in-gurgaon-writer-doc.md
**Score:** 54/100
**Publishable:** No
**Word Count:** 1949
**Paragraphs:** 58
**Total Issues:** 7

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

## MEDIUM Issues (2)

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

## Issues by Owner

| Owner | Critical | High | Medium | Low | Total |
|-------|----------|------|--------|-----|-------|
| ROI | 0 | 5 | 2 | 0 | 7 |
