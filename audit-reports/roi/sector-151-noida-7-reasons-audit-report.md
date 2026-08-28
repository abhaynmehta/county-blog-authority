# Blog Audit Report

**File:** blogs/roi-incoming/sector-151-noida-7-reasons.md
**Score:** 88/100
**Publishable:** Yes
**Word Count:** 2941
**Paragraphs:** 48
**Total Issues:** 8

## Publication Gates

| Gate | Status | Details |
|------|--------|---------|
| 1. Factual Accuracy | PASS | No factual issues |
| 2. RERA & Legal Compliance | PASS | Compliant |
| 3. Technical SEO Eligibility | PASS | SEO basics pass |
| 4. Deployment Integrity | WARN | Check post-deployment |

## MEDIUM Issues (4)

### CG-META-001: Meta description too long (186 chars)

- **Owner:** ROI
- **Category:** meta_description
- **Found:** "This blog explores 7 reasons to buy a flat in Sector 151, Noida, from excellent connectivity and green surroundings to premium housing and long-term growth potential. Click to know more!"
- **Action:** Shorten to 120-160 characters
- **Acceptance test:** Description is 120-160 characters

### CG-META-002: Clickbait CTA in meta description — spam signal per Google

- **Owner:** ROI
- **Category:** meta_description
- **Found:** "This blog explores 7 reasons to buy a flat in Sector 151, Noida, from excellent connectivity and green surroundings to premium housing and long-term growth potential. Click to know more!"
- **Action:** Remove clickbait CTA. Use a factual description of the content.
- **Acceptance test:** No 'click to', 'don't miss', 'hurry' etc. in meta
- **Google rule:** SPAM-CLICKBAIT-001

### CG-CONTENT-003: Keyword stuffing: 'premium residential' appears 12 times

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

## LOW Issues (3)

### CG-LINK-006: Internal URL needs verification: countygroup.in/flats-in-noida

- **Owner:** INTERNAL
- **Category:** internal_links
- **Found:** "https://www.countygroup.in/flats-in-noida"
- **Reason:** already listed as unverified in site_urls.yaml
- **Action:** Run `agent links` to check it resolves, then add it to county_context/site_urls.yaml or correct the link
- **Acceptance test:** Every internal link resolves and is listed in site_urls.yaml

### CG-LINK-007: Internal URL needs verification: countygroup.in/clovecounty/amenities

- **Owner:** INTERNAL
- **Category:** internal_links
- **Found:** "https://www.countygroup.in/clovecounty/amenities"
- **Reason:** not listed in site_urls.yaml
- **Action:** Run `agent links` to check it resolves, then add it to county_context/site_urls.yaml or correct the link
- **Acceptance test:** Every internal link resolves and is listed in site_urls.yaml

### CG-LINK-008: Internal URL needs verification: countygroup.in/clovecounty/overview

- **Owner:** INTERNAL
- **Category:** internal_links
- **Found:** "https://www.countygroup.in/clovecounty/overview"
- **Reason:** not listed in site_urls.yaml
- **Action:** Run `agent links` to check it resolves, then add it to county_context/site_urls.yaml or correct the link
- **Acceptance test:** Every internal link resolves and is listed in site_urls.yaml

## INFO Issues (1)

### CG-PROJECT-005: Reviewer note for Clove County: Publishing a Clove County carpet or super area figure; none is registered yet

- **Owner:** ROI
- **Category:** missing_evidence
- **Action:** Confirm the content does not do this
- **Acceptance test:** Publishing a Clove County carpet or super area figure; none is registered yet
- **Editorial rule:** PROJECT_SPECIFIC_RULE

## Issues by Owner

| Owner | Critical | High | Medium | Low | Total |
|-------|----------|------|--------|-----|-------|
| ROI | 0 | 0 | 4 | 0 | 5 |
| INTERNAL | 0 | 0 | 0 | 3 | 3 |
