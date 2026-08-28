# Blog Audit Report

**File:** blogs/roi-incoming/flats-in-greater-noida.md
**Score:** 82/100
**Publishable:** No
**Word Count:** 2114
**Paragraphs:** 78
**Total Issues:** 9

## Publication Gates

| Gate | Status | Details |
|------|--------|---------|
| 1. Factual Accuracy | PASS | No factual issues |
| 2. RERA & Legal Compliance | FAIL | 1 compliance issues |
| 3. Technical SEO Eligibility | PASS | SEO basics pass |
| 4. Deployment Integrity | WARN | Check post-deployment |

## MEDIUM Issues (6)

### CG-META-001: Meta title too long (96 chars, may truncate)

- **Owner:** ROI
- **Category:** meta_title
- **Found:** "Curated Communities for Holistic Residential Living in Greater Noida West | Blog by County Group"
- **Action:** Shorten title to 60 characters or fewer
- **Acceptance test:** Title is 30-60 characters

### CG-META-002: Meta description too long (206 chars)

- **Owner:** ROI
- **Category:** meta_description
- **Found:** "Discover how County Group's curated communities in Greater Noida West combine wellness, recreation, green spaces, and premium amenities, and ready-to-move flats for a balanced lifestyle. Click to know more!"
- **Action:** Shorten to 120-160 characters
- **Acceptance test:** Description is 120-160 characters

### CG-META-003: Clickbait CTA in meta description — spam signal per Google

- **Owner:** ROI
- **Category:** meta_description
- **Found:** "Discover how County Group's curated communities in Greater Noida West combine wellness, recreation, green spaces, and premium amenities, and ready-to-move flats for a balanced lifestyle. Click to know more!"
- **Action:** Remove clickbait CTA. Use a factual description of the content.
- **Acceptance test:** No 'click to', 'don't miss', 'hurry' etc. in meta
- **Google rule:** SPAM-CLICKBAIT-001

### CG-CONTENT-004: Keyword stuffing: 'greater noida' appears 36 times

- **Owner:** ROI
- **Category:** prohibited_language
- **Action:** Reduce repetition. Use synonyms and natural phrasing.
- **Acceptance test:** No phrase repeated more than 7 times in one article
- **Google rule:** SPAM-KEYWORD-001

### CG-CONTENT-005: No images found in content

- **Owner:** ROI
- **Category:** image_seo
- **Action:** Add 1 hero image and 2-4 supporting visuals with descriptive alt text
- **Acceptance test:** Hero image + 2 supporting images with specific alt text

### CG-LINK-009: No external authority links — every link points back to County Group

- **Owner:** ROI
- **Category:** external_links
- **Action:** Cite 2-3 external sources (UP-RERA, HARERA, ANAROCK, PIB, official news)
- **Acceptance test:** At least 2 external authority links present

## LOW Issues (3)

### CG-LINK-006: Internal URL needs verification: countygroup.in/flats-in-greater-noida

- **Owner:** INTERNAL
- **Category:** internal_links
- **Found:** "https://www.countygroup.in/flats-in-greater-noida"
- **Reason:** already listed as unverified in site_urls.yaml
- **Action:** Run `agent links` to check it resolves, then add it to county_context/site_urls.yaml or correct the link
- **Acceptance test:** Every internal link resolves and is listed in site_urls.yaml

### CG-LINK-007: Internal URL needs verification: countygroup.in/Completed-Residential

- **Owner:** INTERNAL
- **Category:** internal_links
- **Found:** "https://www.countygroup.in/Completed-Residential"
- **Reason:** already listed as unverified in site_urls.yaml
- **Action:** Run `agent links` to check it resolves, then add it to county_context/site_urls.yaml or correct the link
- **Acceptance test:** Every internal link resolves and is listed in site_urls.yaml

### CG-LINK-008: Internal URL needs verification: countygroup.in/contact.php

- **Owner:** INTERNAL
- **Category:** internal_links
- **Found:** "https://www.countygroup.in/contact.php"
- **Reason:** already listed as unverified in site_urls.yaml
- **Action:** Run `agent links` to check it resolves, then add it to county_context/site_urls.yaml or correct the link
- **Acceptance test:** Every internal link resolves and is listed in site_urls.yaml

## Issues by Owner

| Owner | Critical | High | Medium | Low | Total |
|-------|----------|------|--------|-----|-------|
| ROI | 0 | 0 | 6 | 0 | 6 |
| INTERNAL | 0 | 0 | 0 | 3 | 3 |
