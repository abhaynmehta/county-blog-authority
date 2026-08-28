# Blog Audit Report

**File:** blogs/roi-incoming/flats-greater-noida-west-conveniences.md
**Score:** 85/100
**Publishable:** Yes
**Word Count:** 2138
**Paragraphs:** 54
**Total Issues:** 8

## Publication Gates

| Gate | Status | Details |
|------|--------|---------|
| 1. Factual Accuracy | PASS | No factual issues |
| 2. RERA & Legal Compliance | PASS | Compliant |
| 3. Technical SEO Eligibility | PASS | SEO basics pass |
| 4. Deployment Integrity | WARN | Check post-deployment |

## MEDIUM Issues (5)

### CG-META-001: Meta title too long (66 chars, may truncate)

- **Owner:** ROI
- **Category:** meta_title
- **Found:** "Why Buy a Flat in Greater Noida West? Explore the Key Conveniences"
- **Action:** Shorten title to 60 characters or fewer
- **Acceptance test:** Title is 30-60 characters

### CG-META-002: Meta description too long (170 chars)

- **Owner:** ROI
- **Category:** meta_description
- **Found:** "Thinking of buying flats in Greater Noida West? Explore schools, healthcare, shopping, connectivity, business hubs and recreational facilities nearby. Click to know more!"
- **Action:** Shorten to 120-160 characters
- **Acceptance test:** Description is 120-160 characters

### CG-META-003: Clickbait CTA in meta description — spam signal per Google

- **Owner:** ROI
- **Category:** meta_description
- **Found:** "Thinking of buying flats in Greater Noida West? Explore schools, healthcare, shopping, connectivity, business hubs and recreational facilities nearby. Click to know more!"
- **Action:** Remove clickbait CTA. Use a factual description of the content.
- **Acceptance test:** No 'click to', 'don't miss', 'hurry' etc. in meta
- **Google rule:** SPAM-CLICKBAIT-001

### CG-CONTENT-004: Keyword stuffing: 'greater noida' appears 40 times

- **Owner:** ROI
- **Category:** spam_signal
- **Action:** Reduce repetition. Use synonyms and natural phrasing.
- **Acceptance test:** No phrase repeated more than 7 times in one article
- **Google rule:** SPAM-KEYWORD-001

### CG-CONTENT-005: No images found in content

- **Owner:** ROI
- **Category:** image_seo
- **Action:** Add 1 hero image and 2-4 supporting visuals with descriptive alt text
- **Acceptance test:** Hero image + 2 supporting images with specific alt text

## LOW Issues (3)

### CG-LINK-006: Internal URL needs verification: countygroup.in/flats-in-greater-noida

- **Owner:** INTERNAL
- **Category:** internal_links
- **Found:** "https://www.countygroup.in/flats-in-greater-noida"
- **Reason:** already listed as unverified in site_urls.yaml
- **Action:** Run `agent links` to check it resolves, then add it to county_context/site_urls.yaml or correct the link
- **Acceptance test:** Every internal link resolves and is listed in site_urls.yaml

### CG-LINK-007: Internal URL needs verification: countygroup.in/Residential

- **Owner:** INTERNAL
- **Category:** internal_links
- **Found:** "https://www.countygroup.in/Residential"
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
| ROI | 0 | 0 | 5 | 0 | 5 |
| INTERNAL | 0 | 0 | 0 | 3 | 3 |
