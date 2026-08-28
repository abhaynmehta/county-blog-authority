# Indian Real Estate Entity Model

## Core Entities

Every blog must correctly identify and relate these entities:

### Developer / Promoter
- Legal promoter name (from RERA) vs marketing brand name
- These may differ — always verify from RERA portal
- Example: "M/s XYZ Developers Pvt Ltd" (RERA) vs "XYZ Group" (marketing)

### Project
- Name, phase, RERA registration, location (sector + city)
- Status: pre-launch | launched | under_construction | ready_to_move | completed
- Configurations: BHK types with carpet area (not super built-up)
- Possession: RERA committed date (not marketing estimate)

### Location Hierarchy
```
India → State → NCR → City → Zone/Micro-market → Sector → Project
```
- Noida ≠ Greater Noida ≠ Yamuna Expressway area
- Sector 150 Noida ≠ Sector 150 Greater Noida
- Gurgaon/Gurugram — use Gurugram in formal content

### Infrastructure
- Status MUST be: operational | under_construction | officially_approved | proposed
- Source: official authority website, not developer marketing
- Airport, metro, expressway, RRTS, employment hubs

### Pricing
- Always state basis: per sq ft carpet area
- ₹ in Cr/L format: ₹1.5 Cr, ₹85 L
- NEVER invent prices — source from current official data

## Search Intent Taxonomy

| Intent | Example queries | Page type |
|--------|----------------|-----------|
| Property discovery | "flats in Noida", "3 BHK Sector 150" | Project/listing page (commercial) |
| Developer research | "County Group reviews", "is County Group reliable" | Brand page (commercial) |
| Locality research | "Sector 150 Noida review", "best sectors in Noida" | Locality guide (informational) |
| Investment research | "Noida property investment 2026" | Investment guide (informational) |
| Homebuyer education | "RERA explained", "carpet area vs built-up" | Educational blog (informational) |
| Comparison | "Noida vs Gurgaon", "Sector 150 vs Greater Noida West" | Comparison article (informational) |
| Infrastructure | "Jewar airport impact on property" | Infrastructure blog (informational) |
| Legal/docs | "home loan process", "stamp duty Noida" | Guide (informational) |

## Cannibalization Rules

- Informational blogs must NOT target the same primary keyword as project/location pages
- If overlap exists: change the blog's angle or consolidate
- Each blog needs: one primary query, one audience + decision stage, one unique question it answers
- Track existing County URLs to avoid creating competing pages
