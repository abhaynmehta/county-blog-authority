# Blog Audit Report

**File:** blogs/roi-incoming/flats-in-gurgaon-sector-88.md
**Score:** 11/100
**Publishable:** No
**Word Count:** 2333
**Paragraphs:** 54
**Total Issues:** 20

## Publication Gates

| Gate | Status | Details |
|------|--------|---------|
| 1. Factual Accuracy | PASS | No factual issues |
| 2. RERA & Legal Compliance | FAIL | 6 compliance issues |
| 3. Technical SEO Eligibility | PASS | SEO basics pass |
| 4. Deployment Integrity | WARN | Check post-deployment |

## CRITICAL Issues (2)

### CG-CONTENT-004: Prohibited language: 'superlative claim ('best') without evidence'

- **Owner:** ROI
- **Category:** prohibited_language
- **Paragraph:** 1
- **Found:** "**Keywords:** flats in gurgaon, premium flats in Gurgaon, property to buy in gurgaon, best flats in gurgaon, best property in gurgaon, builders and developers in Delhi NCR, 3 BHK flat in gurgaon, best"
- **Reason:** Violates RERA compliance / editorial policy
- **Action:** Remove or rephrase the 'superlative claim ('best') without evidence' claim
- **Acceptance test:** No 'superlative claim ('best') without evidence' language remains
- **Editorial rule:** BRAND_PROHIBITED_001

### CG-CONTENT-005: Prohibited language: 'superlative claim ('best') without evidence'

- **Owner:** ROI
- **Category:** prohibited_language
- **Paragraph:** 18
- **Found:** "The proposed metro extension along the Dwarka Expressway corridor is expected to add a significant public transport layer to this micro-market, which would further reduce commute times and support pro"
- **Reason:** Violates RERA compliance / editorial policy
- **Action:** Remove or rephrase the 'superlative claim ('best') without evidence' claim
- **Acceptance test:** No 'superlative claim ('best') without evidence' language remains
- **Editorial rule:** BRAND_PROHIBITED_001

## HIGH Issues (4)

### CG-CONTENT-009: 4 travel time claim(s) without source attribution

- **Owner:** ROI
- **Category:** unsupported_claim
- **Action:** Add source (e.g., 'via Google Maps as of [date]') or remove specific time claims
- **Acceptance test:** Every travel time claim has inline source

### CG-CONTENT-010: RERA mentioned but no registration number provided

- **Owner:** ROI
- **Category:** rera_compliance
- **Action:** Add the actual RERA registration number with portal verification link
- **Acceptance test:** RERA registration number is visible and verifiable
- **Google rule:** CONTENT-RERA-001

### CG-CONTENT-011: Area figures (3 mentions) not labeled as carpet area

- **Owner:** ROI
- **Category:** rera_compliance
- **Action:** Specify whether figures are carpet area (RERA) or super built-up. RERA mandates carpet area disclosure.
- **Acceptance test:** All area figures explicitly labeled as carpet area or super built-up
- **Google rule:** CONTENT-RERA-002

### CG-TRUTH-014: Registry-prohibited wording: 'proposed metro'

- **Owner:** ROI
- **Category:** prohibited_language
- **Paragraph:** 16
- **Found:** "| Destination | Approximate Travel Time | Route |
| :-: | :-: | :-: |
| IGI Airport | 30 minutes / 35 minutes | Route 3 / Route 1 |
| Pataudi Road Junction | 10–12 minutes | Route 1 |
| Southern Perip"
- **Reason:** Listed under prohibited_wording in the County Group truth layer
- **Action:** Remove or rephrase 'proposed metro'
- **Acceptance test:** No 'proposed metro' wording remains
- **Editorial rule:** TRUTH_LAYER_PROHIBITED

## MEDIUM Issues (9)

### CG-META-001: Meta title too long (88 chars, may truncate)

- **Owner:** ROI
- **Category:** meta_title
- **Found:** "Why Sector 88A is One of the Best Places to Buy a Flat in Gurgaon | Blog by County Group"
- **Action:** Shorten title to 60 characters or fewer
- **Acceptance test:** Title is 30-60 characters

### CG-META-002: Meta description too long (171 chars)

- **Owner:** ROI
- **Category:** meta_description
- **Found:** "Planning to buy a flat in Gurgaon? Learn why Sector 88A stands out with excellent connectivity, premium residential projects, and strong future growth. Click to know more!"
- **Action:** Shorten to 120-160 characters
- **Acceptance test:** Description is 120-160 characters

### CG-META-003: Clickbait CTA in meta description — spam signal per Google

- **Owner:** ROI
- **Category:** meta_description
- **Found:** "Planning to buy a flat in Gurgaon? Learn why Sector 88A stands out with excellent connectivity, premium residential projects, and strong future growth. Click to know more!"
- **Action:** Remove clickbait CTA. Use a factual description of the content.
- **Acceptance test:** No 'click to', 'don't miss', 'hurry' etc. in meta
- **Google rule:** SPAM-CLICKBAIT-001

### CG-CONTENT-006: Implied appreciation: Implies price support without evidence

- **Owner:** ROI
- **Category:** unsupported_claim
- **Paragraph:** 18
- **Found:** "The proposed metro extension along the Dwarka Expressway corridor is expected to add a significant public transport layer to this micro-market, which would further reduce commute times and support pro"
- **Action:** Remove forward-looking price claim or add 'past performance does not indicate future results'
- **Acceptance test:** No implied price appreciation without disclaimer
- **Editorial rule:** EDITORIAL_INVESTMENT_001

### CG-CONTENT-007: Implied appreciation: Implies price appreciation without evidence

- **Owner:** ROI
- **Category:** unsupported_claim
- **Paragraph:** 25
- **Found:** "- **Planned development** sets it apart from older sectors that grew organically and now carry the weight of congestion, mixed land use and ageing infrastructure. Sector 88A was laid out with a clear "
- **Action:** Remove forward-looking price claim or add 'past performance does not indicate future results'
- **Acceptance test:** No implied price appreciation without disclaimer
- **Editorial rule:** EDITORIAL_INVESTMENT_001

### CG-CONTENT-008: Implied appreciation: Implies certain price appreciation

- **Owner:** ROI
- **Category:** unsupported_claim
- **Paragraph:** 25
- **Found:** "- **Planned development** sets it apart from older sectors that grew organically and now carry the weight of congestion, mixed land use and ageing infrastructure. Sector 88A was laid out with a clear "
- **Action:** Remove forward-looking price claim or add 'past performance does not indicate future results'
- **Acceptance test:** No implied price appreciation without disclaimer
- **Editorial rule:** EDITORIAL_INVESTMENT_001

### CG-CONTENT-012: Keyword stuffing: 'minutes | route' appears 11 times

- **Owner:** ROI
- **Category:** prohibited_language
- **Action:** Reduce repetition. Use synonyms and natural phrasing.
- **Acceptance test:** No phrase repeated more than 7 times in one article
- **Google rule:** SPAM-KEYWORD-001

### CG-CONTENT-013: No images found in content

- **Owner:** ROI
- **Category:** image_seo
- **Action:** Add 1 hero image and 2-4 supporting visuals with descriptive alt text
- **Acceptance test:** Hero image + 2 supporting images with specific alt text

### CG-LINK-020: Generic anchor text 'here' on an internal link

- **Owner:** ROI
- **Category:** internal_links
- **Found:** "[here](https://www.countygroup.in/centercourt/)"
- **Action:** Use descriptive anchor text naming the destination
- **Acceptance test:** No internal link uses generic anchor text
- **Google rule:** CONTENT-LINK-001

## LOW Issues (4)

### CG-LINK-016: Internal URL needs verification: countygroup.in/flats-in-gurugram

- **Owner:** INTERNAL
- **Category:** internal_links
- **Found:** "https://www.countygroup.in/flats-in-gurugram"
- **Reason:** already listed as unverified in site_urls.yaml
- **Action:** Run `agent links` to check it resolves, then add it to county_context/site_urls.yaml or correct the link
- **Acceptance test:** Every internal link resolves and is listed in site_urls.yaml

### CG-LINK-017: Internal URL needs verification: countygroup.in/Residential

- **Owner:** INTERNAL
- **Category:** internal_links
- **Found:** "https://www.countygroup.in/Residential"
- **Reason:** already listed as unverified in site_urls.yaml
- **Action:** Run `agent links` to check it resolves, then add it to county_context/site_urls.yaml or correct the link
- **Acceptance test:** Every internal link resolves and is listed in site_urls.yaml

### CG-LINK-018: Internal URL needs verification: countygroup.in/centercourt/location

- **Owner:** INTERNAL
- **Category:** internal_links
- **Found:** "https://www.countygroup.in/centercourt/location"
- **Reason:** not listed in site_urls.yaml
- **Action:** Run `agent links` to check it resolves, then add it to county_context/site_urls.yaml or correct the link
- **Acceptance test:** Every internal link resolves and is listed in site_urls.yaml

### CG-LINK-019: Internal URL needs verification: countygroup.in/centercourt/amenities

- **Owner:** INTERNAL
- **Category:** internal_links
- **Found:** "https://www.countygroup.in/centercourt/amenities"
- **Reason:** not listed in site_urls.yaml
- **Action:** Run `agent links` to check it resolves, then add it to county_context/site_urls.yaml or correct the link
- **Acceptance test:** Every internal link resolves and is listed in site_urls.yaml

## INFO Issues (1)

### CG-PROJECT-015: Reviewer note for The Center Court: Describing this project as being in Noida or Uttar Pradesh

- **Owner:** ROI
- **Category:** missing_evidence
- **Action:** Confirm the content does not do this
- **Acceptance test:** Describing this project as being in Noida or Uttar Pradesh
- **Editorial rule:** PROJECT_SPECIFIC_RULE

## Issues by Owner

| Owner | Critical | High | Medium | Low | Total |
|-------|----------|------|--------|-----|-------|
| ROI | 2 | 4 | 9 | 0 | 16 |
| INTERNAL | 0 | 0 | 0 | 4 | 4 |
