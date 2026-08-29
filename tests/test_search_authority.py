"""Tests for the County Group search_authority audit engine."""

import json
import sys
from pathlib import Path

# Add parent to path for import
sys.path.insert(0, str(Path(__file__).parent.parent))

from search_authority.content_auditor import audit_text
from search_authority.models import Severity, Owner, IssueCategory, GateStatus
from search_authority.report import (
    generate_markdown_report,
    generate_json_report,
    generate_csv_issues,
    generate_agency_handoff,
)
from search_authority.schema import (
    generate_blog_schema,
    generate_breadcrumb_schema,
    schemas_to_jsonld,
    validate_schema,
)
from search_authority.pipeline import run_pipeline


# --- Content Auditor Tests ---

def test_catches_guaranteed_appreciation():
    text = "This area has shown guaranteed appreciation of 15% annually."
    result = audit_text(text)
    cats = [i.category for i in result.issues]
    assert IssueCategory.PROHIBITED_LANGUAGE in cats


def test_catches_best_investment():
    text = "Noida is the best investment destination in NCR."
    result = audit_text(text)
    cats = [i.category for i in result.issues]
    assert IssueCategory.PROHIBITED_LANGUAGE in cats


def test_catches_risk_free():
    text = "Real estate in Noida is a risk-free investment for homebuyers."
    result = audit_text(text)
    cats = [i.category for i in result.issues]
    assert IssueCategory.PROHIBITED_LANGUAGE in cats


def test_catches_assured_returns():
    text = "Investors can expect assured returns of 8-10% per year."
    result = audit_text(text)
    cats = [i.category for i in result.issues]
    assert IssueCategory.PROHIBITED_LANGUAGE in cats


def test_catches_best_developer():
    text = "County Group is the best developer in Noida."
    result = audit_text(text)
    cats = [i.category for i in result.issues]
    assert IssueCategory.PROHIBITED_LANGUAGE in cats


def test_catches_world_class():
    text = "The project offers world-class amenities."
    result = audit_text(text)
    cats = [i.category for i in result.issues]
    assert IssueCategory.PROHIBITED_LANGUAGE in cats


def test_catches_upcoming_airport():
    text = "The upcoming Jewar Airport will boost property values."
    result = audit_text(text)
    cats = [i.category for i in result.issues]
    assert IssueCategory.INFRASTRUCTURE_STATUS in cats


def test_catches_upcoming_noida_international():
    text = "With the upcoming Noida International Airport nearby."
    result = audit_text(text)
    cats = [i.category for i in result.issues]
    assert IssueCategory.INFRASTRUCTURE_STATUS in cats


def test_catches_proposed_airport():
    text = "The proposed airport at Jewar will change the landscape."
    result = audit_text(text)
    cats = [i.category for i in result.issues]
    assert IssueCategory.INFRASTRUCTURE_STATUS in cats


def test_catches_percentage_claims():
    text = "Property values have seen 20% appreciation in the last year."
    result = audit_text(text)
    cats = [i.category for i in result.issues]
    assert IssueCategory.UNSUPPORTED_CLAIM in cats


def test_catches_missing_links():
    text = "Clove County is a great project in Sector 151 Noida."
    result = audit_text(text)
    cats = [i.category for i in result.issues]
    assert IssueCategory.INTERNAL_LINKS in cats


def test_catches_missing_images():
    text = "# My Blog\n\nSome content about real estate."
    result = audit_text(text)
    cats = [i.category for i in result.issues]
    assert IssueCategory.IMAGE_SEO in cats


def test_catches_missing_h1():
    text = "Just plain text without any headings."
    result = audit_text(text)
    cats = [i.category for i in result.issues]
    assert IssueCategory.HEADING_STRUCTURE in cats


def test_catches_multiple_h1():
    text = "# First H1\n\nContent\n\n# Second H1\n\nMore content"
    result = audit_text(text)
    issues = [i for i in result.issues if "Multiple H1" in i.summary]
    assert len(issues) == 1


def test_catches_heading_skip():
    text = "# Title\n\n## Section\n\n#### Subsection"
    result = audit_text(text)
    issues = [i for i in result.issues if "skipped" in i.summary]
    assert len(issues) == 1


def test_catches_long_meta_title():
    text = "Meta Title: This is a very long meta title that exceeds the recommended sixty character limit for search engines\n\nContent"
    result = audit_text(text)
    cats = [i.category for i in result.issues]
    assert IssueCategory.META_TITLE in cats


def test_catches_long_meta_description():
    text = "Meta Description: This is a very long meta description that exceeds the recommended one hundred and sixty character limit. It should be shortened to avoid truncation in search results. Google may generate its own snippet but recommends accurate descriptions.\n\nContent"
    result = audit_text(text)
    cats = [i.category for i in result.issues]
    assert IssueCategory.META_DESCRIPTION in cats


def test_clean_blog_has_fewer_issues():
    text = """Meta Title: Verify Developers on UP RERA Portal
Meta Description: Step-by-step guide to verify any real estate developer in Noida using the UP RERA portal.

# How to Verify a Real Estate Developer on UP RERA

This guide explains how homebuyers can independently verify any developer in Uttar Pradesh.

## Step 1: Visit the UP RERA Portal

Go to [UP RERA](https://www.up-rera.in) and search for the project.

## Step 2: Check Registration Details

Verify the registration number, promoter name, and completion date.

![UP RERA search page](up-rera-search.webp)
"""
    result = audit_text(text)
    assert result.score > 50
    prohibited = [i for i in result.issues if i.category == IssueCategory.PROHIBITED_LANGUAGE]
    assert len(prohibited) == 0


def test_all_prohibited_issues_assigned_to_roi():
    text = "This is the best investment with guaranteed appreciation and assured returns."
    result = audit_text(text)
    for issue in result.issues:
        if issue.category == IssueCategory.PROHIBITED_LANGUAGE:
            assert issue.owner == Owner.ROI


def test_infrastructure_issues_assigned_to_roi():
    text = "The upcoming airport will be great."
    result = audit_text(text)
    for issue in result.issues:
        if issue.category == IssueCategory.INFRASTRUCTURE_STATUS:
            assert issue.owner == Owner.ROI


def test_gates_fail_on_critical_issues():
    text = "This is a risk-free investment with guaranteed appreciation."
    result = audit_text(text)
    assert not result.publishable
    gate_statuses = {g.gate_name: g.status for g in result.gates}
    assert gate_statuses["RERA & Legal Compliance"] == GateStatus.FAIL


def test_gates_pass_on_clean_content():
    text = """Meta Title: Sector 150 Noida Guide
Meta Description: A complete guide to Sector 150 Noida for homebuyers.

# Sector 150 Noida: Complete Buyer's Guide

This guide covers everything buyers need to know about Sector 150.

## Location and Connectivity

Sector 150 is located along the [Noida Expressway](https://countygroup.in/sector-150).

## Infrastructure

The Noida International Airport began commercial operations in June 2026 ([source](https://www.niairport.in)).

![Sector 150 map](sector-150-map.webp)
"""
    result = audit_text(text)
    gate_statuses = {g.gate_name: g.status for g in result.gates}
    assert gate_statuses["Factual Accuracy"] == GateStatus.PASS
    assert gate_statuses["RERA & Legal Compliance"] == GateStatus.PASS


# --- Report Tests ---

def test_markdown_report_contains_owner_table():
    text = "This is the best investment with guaranteed appreciation."
    result = audit_text(text)
    report = generate_markdown_report(result)
    assert "Issues by Owner" in report
    assert "ROI" in report


def test_json_report_is_valid_json():
    text = "Some blog content about real estate."
    result = audit_text(text)
    report = generate_json_report(result)
    data = json.loads(report)
    assert "issues" in data
    assert "score" in data


def test_csv_report_has_headers():
    text = "Best developer in Noida with guaranteed appreciation."
    result = audit_text(text)
    csv_output = generate_csv_issues([result])
    lines = csv_output.strip().split("\n")
    assert "Issue ID" in lines[0]
    assert len(lines) > 1


def test_agency_handoff_filters_by_owner():
    text = "The best investment with guaranteed appreciation."
    result = audit_text(text)
    roi_report = generate_agency_handoff([result], Owner.ROI)
    assert "ROI Action Items" in roi_report

    ago_report = generate_agency_handoff([result], Owner.AGO)
    assert "AGO Action Items" in ago_report


# --- Schema Tests ---

def test_blog_schema_structure():
    schema = generate_blog_schema(
        headline="Test Blog",
        description="Test description",
        url="https://example.com/blog/test",
        date_published="2026-08-27",
    )
    assert schema["@type"] == "BlogPosting"
    assert schema["headline"] == "Test Blog"
    assert schema["datePublished"] == "2026-08-27"
    assert schema["author"]["@type"] == "Organization"


def test_breadcrumb_schema():
    schema = generate_breadcrumb_schema([
        {"name": "Home", "url": "https://example.com/"},
        {"name": "Blog", "url": "https://example.com/blog/"},
        {"name": "Test Post"},
    ])
    assert schema["@type"] == "BreadcrumbList"
    assert len(schema["itemListElement"]) == 3
    assert schema["itemListElement"][0]["position"] == 1


def test_schema_validation_catches_missing_headline():
    schema = {"@type": "BlogPosting", "datePublished": "2026-08-27"}
    warnings = validate_schema(schema, "some text")
    assert any("headline" in w.lower() for w in warnings)


def test_schema_validation_catches_missing_date():
    schema = {"@type": "BlogPosting", "headline": "Test"}
    warnings = validate_schema(schema, "test content")
    assert any("datePublished" in w for w in warnings)


def test_combined_jsonld_output():
    blog = generate_blog_schema(
        headline="Test", description="Test", url="https://x.com/blog",
        date_published="2026-08-27",
    )
    bc = generate_breadcrumb_schema([{"name": "Home", "url": "https://x.com/"}])
    output = schemas_to_jsonld(blog, bc)
    data = json.loads(output)
    assert "@graph" in data
    assert len(data["@graph"]) == 2


# --- Regression Tests (from the 8 revised blogs) ---

def test_regression_catches_all_key_issues_in_bad_blog():
    """The system must catch all the issues found in the manual audit of Blog 8 (Luxury Living 2026)."""
    text = """Meta Title: Luxury Living in Noida: Why 2026 Is the Year for Premium Residential Investments in Noida NCR Delhi
Meta Description: Discover why 2026 is the best year for investing in luxury apartments in Noida. Explore premium residential projects, Sector 150, and upcoming infrastructure developments that make Noida the top choice for property investment in NCR.

# Luxury Living in Noida: Why 2026 Is the Year for Premium Residential Investments

Noida has emerged as the best investment destination in NCR with guaranteed appreciation and risk-free returns.

## Why Invest in Noida

The upcoming Jewar Airport and world-class infrastructure make this the best investment opportunity.

#### Price Trends

Property prices have shown 20% appreciation year-on-year with assured returns of 8-10%.

## Conclusion

County Group is the best developer in Noida. Don't miss this opportunity.
"""
    result = audit_text(text)

    # Must NOT be publishable
    assert not result.publishable

    # Must catch these specific issues:
    categories = [i.category for i in result.issues]
    assert IssueCategory.PROHIBITED_LANGUAGE in categories  # "best investment", "guaranteed", etc.
    assert IssueCategory.INFRASTRUCTURE_STATUS in categories  # "upcoming" airport
    assert IssueCategory.UNSUPPORTED_CLAIM in categories  # percentage claims
    assert IssueCategory.META_TITLE in categories  # too long
    assert IssueCategory.META_DESCRIPTION in categories  # too long
    assert IssueCategory.HEADING_STRUCTURE in categories  # H2→H4 skip
    assert IssueCategory.INTERNAL_LINKS in categories  # no links
    assert IssueCategory.IMAGE_SEO in categories  # no images

    # Must have critical severity issues
    critical = [i for i in result.issues if i.severity == Severity.CRITICAL]
    assert len(critical) >= 5

    # All issues must have an owner
    for issue in result.issues:
        assert issue.owner is not None


# --- Pipeline Tests ---

def test_pipeline_clean_blog(tmp_path):
    text = """Meta Title: RERA Verification Guide for Noida
Meta Description: How to verify developers on the UP RERA portal.

# How to Verify a Developer on UP RERA

Step-by-step guide for homebuyers.

## Step 1: Visit the Portal

Go to [UP RERA](https://www.up-rera.in).

## Step 2: Search

Enter the project or promoter name.

![RERA portal](rera.webp)
"""
    result = run_pipeline(
        text=text,
        slug="rera-guide",
        output_dir=str(tmp_path),
    )
    assert result["publishable"] is True
    assert result["score"] > 50
    assert result["critical_count"] == 0
    # No schema without a real publication date: the pipeline must never
    # invent one, so a caller that omits it gets diagnostics only.
    assert "schema" not in result["output_files"]
    assert result["schema_skipped_reason"] == "no date_published supplied"

    # Supplying the real date produces schema carrying that date, not today's.
    dated = run_pipeline(
        text=text,
        slug="rera-guide-dated",
        output_dir=str(tmp_path),
        date_published="2026-06-01",
    )
    schema = json.loads(Path(dated["output_files"]["schema"]).read_text())
    assert "@graph" in schema
    assert schema["@graph"][0]["datePublished"] == "2026-06-01"


def test_pipeline_bad_blog_not_publishable(tmp_path):
    text = "The best investment with guaranteed appreciation and upcoming airport."
    result = run_pipeline(
        text=text,
        slug="bad",
        output_dir=str(tmp_path),
    )
    assert result["publishable"] is False
    assert result["critical_count"] >= 2
    assert result["gates"]["RERA & Legal Compliance"] == "FAIL"
    assert Path(result["output_files"]["roi_handoff"]).exists()


def test_pipeline_from_file(tmp_path):
    blog_file = tmp_path / "test.md"
    blog_file.write_text("""Meta Title: Test Blog Post
Meta Description: A test blog post for pipeline testing.

# Test Blog Post

Some content here with a [link](https://example.com).

## Section Two

More content.

![test image](test.webp)
""")
    out_dir = tmp_path / "output"
    result = run_pipeline(
        input_path=str(blog_file),
        output_dir=str(out_dir),
    )
    assert "slug" in result
    assert Path(result["output_files"]["audit_report_md"]).exists()
    assert Path(result["output_files"]["ago_handoff"]).exists()
