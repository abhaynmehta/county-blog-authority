# Blog Audit Report

**File:** blogs/roi-incoming/flats-in-noida-expressway.md
**Score:** 85/100
**Publishable:** Yes
**Word Count:** 1856
**Paragraphs:** 56
**Total Issues:** 9

## Publication Gates

| Gate | Status | Details |
|------|--------|---------|
| 1. Factual Accuracy | PASS | No factual issues |
| 2. RERA & Legal Compliance | PASS | Compliant |
| 3. Technical SEO Eligibility | PASS | SEO basics pass |
| 4. Deployment Integrity | WARN | Check post-deployment |

## MEDIUM Issues (5)

### CG-META-001: Meta title too long (94 chars, may truncate)

- **Owner:** ROI
- **Category:** meta_title
- **Found:** "Noida-Greater Noida Expressway: A Growing Destination for Luxury Flats in Noida | County Group"
- **Action:** Shorten title to 60 characters or fewer
- **Acceptance test:** Title is 30-60 characters

### CG-META-002: Meta description too long (190 chars)

- **Owner:** ROI
- **Category:** meta_description
- **Found:** "Explore why the Noida-Greater Noida Expressway is emerging as a prime residential corridor, offering luxury flats, better connectivity, green spaces, and a well-planned lifestyle. Read more!"
- **Action:** Shorten to 120-160 characters
- **Acceptance test:** Description is 120-160 characters

### CG-CONTENT-003: Keyword stuffing: 'noida-greater noida' appears 12 times

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

### CG-CONTENT-005: CTA spam: 2 generic 'read more/click here' CTAs in body text

- **Owner:** ROI
- **Category:** spam_signal
- **Action:** Replace with descriptive anchor text linking to specific content
- **Acceptance test:** No generic 'read more' or 'click here' CTAs in body
- **Google rule:** SPAM-CLICKBAIT-002

## LOW Issues (3)

### CG-LINK-007: Internal URL needs verification: countygroup.in/flats-in-noida

- **Owner:** INTERNAL
- **Category:** internal_links
- **Found:** "https://www.countygroup.in/flats-in-noida"
- **Reason:** already listed as unverified in site_urls.yaml
- **Action:** Run `agent links` to check it resolves, then add it to county_context/site_urls.yaml or correct the link
- **Acceptance test:** Every internal link resolves and is listed in site_urls.yaml

### CG-LINK-008: Internal URL needs verification: countygroup.in/clovecounty/overview

- **Owner:** INTERNAL
- **Category:** internal_links
- **Found:** "https://www.countygroup.in/clovecounty/overview"
- **Reason:** not listed in site_urls.yaml
- **Action:** Run `agent links` to check it resolves, then add it to county_context/site_urls.yaml or correct the link
- **Acceptance test:** Every internal link resolves and is listed in site_urls.yaml

### CG-LINK-009: Internal URL needs verification: countygroup.in/contact.php

- **Owner:** INTERNAL
- **Category:** internal_links
- **Found:** "https://www.countygroup.in/contact.php"
- **Reason:** already listed as unverified in site_urls.yaml
- **Action:** Run `agent links` to check it resolves, then add it to county_context/site_urls.yaml or correct the link
- **Acceptance test:** Every internal link resolves and is listed in site_urls.yaml

## INFO Issues (1)

### CG-PROJECT-006: Reviewer note for Clove County: Quoting super area as the flat size without naming carpet area

- **Owner:** ROI
- **Category:** missing_evidence
- **Action:** Confirm the content does not do this
- **Acceptance test:** Quoting super area as the flat size without naming carpet area
- **Editorial rule:** PROJECT_SPECIFIC_RULE

## Issues by Owner

| Owner | Critical | High | Medium | Low | Total |
|-------|----------|------|--------|-----|-------|
| ROI | 0 | 0 | 5 | 0 | 6 |
| INTERNAL | 0 | 0 | 0 | 3 | 3 |
