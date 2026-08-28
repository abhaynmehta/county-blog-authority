# Blog Audit Report

**File:** blogs/roi-incoming/flats-in-noida-jewar-airport.md
**Score:** 34/100
**Publishable:** No
**Word Count:** 1950
**Paragraphs:** 45
**Total Issues:** 14

## Publication Gates

| Gate | Status | Details |
|------|--------|---------|
| 1. Factual Accuracy | FAIL | 3 factual issues |
| 2. RERA & Legal Compliance | FAIL | 1 compliance issues |
| 3. Technical SEO Eligibility | PASS | SEO basics pass |
| 4. Deployment Integrity | WARN | Check post-deployment |

## CRITICAL Issues (3)

### CG-CONTENT-004: Airport described as future — Noida International Airport opened June 2026

- **Owner:** ROI
- **Category:** infrastructure_status
- **Paragraph:** 6
- **Found:** "Jewar Airport is expected to become one of the biggest milestones in Noida's growth story, with its impact extending far beyond air travel. As the city enters its next phase of development, the airpor"
- **Evidence:** https://www.niairport.in/en/company/news/2026/2026-06-15
- **Correct status:** Noida International Airport: commercial ops began 15 June 2026
- **Action:** Update to reflect operational status with source link
- **Acceptance test:** Airport described as operational with official source

### CG-CONTENT-005: Airport described as future — Noida International Airport opened June 2026

- **Owner:** ROI
- **Category:** infrastructure_status
- **Paragraph:** 30
- **Found:** "Major infrastructure projects like airports strengthen an area's long-term growth potential by improving connectivity and attracting businesses and investment. While property appreciation depends on s"
- **Evidence:** https://www.niairport.in/en/company/news/2026/2026-06-15
- **Correct status:** Noida International Airport: commercial ops began 15 June 2026
- **Action:** Update to reflect operational status with source link
- **Acceptance test:** Airport described as operational with official source

### CG-CONTENT-006: Airport described as future — Noida International Airport opened June 2026

- **Owner:** ROI
- **Category:** infrastructure_status
- **Paragraph:** 42
- **Found:** "Meta Description: Discover how Jewar Airport is set to drive demand for luxury flats in Noida through improved connectivity, infrastructure growth, and expanding residential opportunities. Click to kn"
- **Evidence:** https://www.niairport.in/en/company/news/2026/2026-06-15
- **Correct status:** Noida International Airport: commercial ops began 15 June 2026
- **Action:** Update to reflect operational status with source link
- **Acceptance test:** Airport described as operational with official source

## MEDIUM Issues (7)

### CG-META-001: Meta title too long (73 chars, may truncate)

- **Owner:** ROI
- **Category:** meta_title
- **Found:** "How Jewar Airport Is Driving Luxury Flats in Noida | Blog by County Group"
- **Action:** Shorten title to 60 characters or fewer
- **Acceptance test:** Title is 30-60 characters

### CG-META-002: Meta description too long (190 chars)

- **Owner:** ROI
- **Category:** meta_description
- **Found:** "Discover how Jewar Airport is set to drive demand for luxury flats in Noida through improved connectivity, infrastructure growth, and expanding residential opportunities. Click to know more!"
- **Action:** Shorten to 120-160 characters
- **Acceptance test:** Description is 120-160 characters

### CG-META-003: Clickbait CTA in meta description — spam signal per Google

- **Owner:** ROI
- **Category:** meta_description
- **Found:** "Discover how Jewar Airport is set to drive demand for luxury flats in Noida through improved connectivity, infrastructure growth, and expanding residential opportunities. Click to know more!"
- **Action:** Remove clickbait CTA. Use a factual description of the content.
- **Acceptance test:** No 'click to', 'don't miss', 'hurry' etc. in meta
- **Google rule:** SPAM-CLICKBAIT-001

### CG-CONTENT-007: Implied appreciation: Implies price appreciation without evidence

- **Owner:** ROI
- **Category:** unsupported_claim
- **Paragraph:** 38
- **Found:** "The right choice depends on your priorities. Ready-to-move flats offer immediate possession and greater certainty, while under-construction homes often offer greater pricing flexibility and future app"
- **Action:** Remove forward-looking price claim or add 'past performance does not indicate future results'
- **Acceptance test:** No implied price appreciation without disclaimer
- **Editorial rule:** EDITORIAL_INVESTMENT_001

### CG-CONTENT-008: Keyword stuffing: 'luxury flats' appears 9 times

- **Owner:** ROI
- **Category:** prohibited_language
- **Action:** Reduce repetition. Use synonyms and natural phrasing.
- **Acceptance test:** No phrase repeated more than 7 times in one article
- **Google rule:** SPAM-KEYWORD-001

### CG-CONTENT-009: No images found in content

- **Owner:** ROI
- **Category:** image_seo
- **Action:** Add 1 hero image and 2-4 supporting visuals with descriptive alt text
- **Acceptance test:** Hero image + 2 supporting images with specific alt text

### CG-LINK-014: No external authority links — every link points back to County Group

- **Owner:** ROI
- **Category:** external_links
- **Action:** Cite 2-3 external sources (UP-RERA, HARERA, ANAROCK, PIB, official news)
- **Acceptance test:** At least 2 external authority links present

## LOW Issues (3)

### CG-LINK-011: Internal URL needs verification: countygroup.in/flats-in-noida

- **Owner:** INTERNAL
- **Category:** internal_links
- **Found:** "https://www.countygroup.in/flats-in-noida"
- **Reason:** already listed as unverified in site_urls.yaml
- **Action:** Run `agent links` to check it resolves, then add it to county_context/site_urls.yaml or correct the link
- **Acceptance test:** Every internal link resolves and is listed in site_urls.yaml

### CG-LINK-012: Internal URL needs verification: countygroup.in/Residential

- **Owner:** INTERNAL
- **Category:** internal_links
- **Found:** "https://www.countygroup.in/Residential"
- **Reason:** already listed as unverified in site_urls.yaml
- **Action:** Run `agent links` to check it resolves, then add it to county_context/site_urls.yaml or correct the link
- **Acceptance test:** Every internal link resolves and is listed in site_urls.yaml

### CG-LINK-013: Internal URL needs verification: countygroup.in/contact.php

- **Owner:** INTERNAL
- **Category:** internal_links
- **Found:** "https://www.countygroup.in/contact.php"
- **Reason:** already listed as unverified in site_urls.yaml
- **Action:** Run `agent links` to check it resolves, then add it to county_context/site_urls.yaml or correct the link
- **Acceptance test:** Every internal link resolves and is listed in site_urls.yaml

## INFO Issues (1)

### CG-PROJECT-010: Reviewer note for Clove County: Publishing a Clove County carpet or super area figure; none is registered yet

- **Owner:** ROI
- **Category:** missing_evidence
- **Action:** Confirm the content does not do this
- **Acceptance test:** Publishing a Clove County carpet or super area figure; none is registered yet
- **Editorial rule:** PROJECT_SPECIFIC_RULE

## Issues by Owner

| Owner | Critical | High | Medium | Low | Total |
|-------|----------|------|--------|-----|-------|
| ROI | 3 | 0 | 7 | 0 | 11 |
| INTERNAL | 0 | 0 | 0 | 3 | 3 |
