"""Tests for the dashboard generator.

The dashboard is a read-only view over audit output. What matters here is
that it collects the right data, embeds it safely, and produces a file that
stands alone with no server or network access.
"""

import json
import re
from pathlib import Path

import pytest
import yaml

from search_authority import dashboard


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A miniature project: one inventory, one blog, one audit report."""
    blogs = tmp_path / "blogs"
    blogs.mkdir()
    (blogs / "alpha.md").write_text(
        "# Luxury Flats in Noida Sector 151\n\n"
        "Meta Title: Luxury Flats in Noida Sector 151\n\nBody.\n",
        encoding="utf-8",
    )
    (blogs / "beta.md").write_text(
        "# Luxury Flats Noida Sector 151 Guide\n\n"
        "Meta Title: Luxury Flats Noida Sector 151 Guide\n\nBody.\n",
        encoding="utf-8",
    )

    inventory = tmp_path / "BLOG_INVENTORY.yaml"
    inventory.write_text(yaml.dump({
        "roi_google_docs": [
            {"title": "Alpha", "local_file": str(blogs / "alpha.md"),
             "score": 45, "issues": 3, "critical": 1, "publishable": False},
            {"title": "Beta", "local_file": str(blogs / "beta.md"),
             "score": 88, "issues": 1, "critical": 0, "publishable": True},
        ]
    }), encoding="utf-8")

    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "alpha-audit-report.json").write_text(json.dumps({
        "word_count": 500,
        "gates": [
            {"gate": "RERA & Legal Compliance", "status": "FAIL"},
            {"gate": "Factual Accuracy", "status": "PASS"},
        ],
        "issues": [
            {"issue_id": "X-1", "severity": "critical", "owner": "ROI",
             "summary": "Wrong city", "claim": "in Noida",
             "recommended_action": "Fix it", "acceptance_test": "Correct city"},
        ],
    }), encoding="utf-8")

    monkeypatch.setattr(dashboard, "REPORT_DIRS", [reports])
    return {"root": tmp_path, "inventory": inventory}


# --- Data collection ---

def test_collects_every_inventory_entry(project):
    data = dashboard.collect_data(project["inventory"])
    assert data["summary"]["total"] == 2


def test_summary_counts_publishable_and_average(project):
    s = dashboard.collect_data(project["inventory"])["summary"]
    assert s["publishable"] == 1
    assert s["avg_score"] == 66.5


def test_score_bands_are_bucketed(project):
    bands = dashboard.collect_data(project["inventory"])["summary"]["bands"]
    assert bands["80-89"] == 1
    assert bands["<60"] == 1


def test_gate_failures_are_tallied(project):
    data = dashboard.collect_data(project["inventory"])
    assert data["gate_failures"]["RERA & Legal Compliance"] == 1
    assert "Factual Accuracy" not in data["gate_failures"]


def test_issues_are_attached_to_their_document(project):
    docs = {d["slug"]: d for d in dashboard.collect_data(project["inventory"])["documents"]}
    assert docs["alpha"]["issue_list"][0]["summary"] == "Wrong city"
    assert docs["alpha"]["issue_list"][0]["claim"] == "in Noida"


def test_documents_without_a_report_still_appear(project):
    """Beta has inventory data but no audit report on disk."""
    docs = {d["slug"]: d for d in dashboard.collect_data(project["inventory"])["documents"]}
    assert docs["beta"]["score"] == 88
    assert docs["beta"]["issue_list"] == []


def test_owner_totals_are_counted(project):
    assert dashboard.collect_data(project["inventory"])["owner_totals"]["ROI"] == 1


def test_cannibalization_runs_over_the_same_corpus(project):
    data = dashboard.collect_data(project["inventory"])
    assert data["cannibalization"]["pages_analysed"] == 2
    assert data["cannibalization"]["collisions"] >= 1


def test_documents_are_ordered_worst_score_first(project):
    docs = dashboard.collect_data(project["inventory"])["documents"]
    assert docs[0]["slug"] == "alpha"


# --- Rendering ---

def test_build_writes_a_file(project, tmp_path):
    out = tmp_path / "out" / "index.html"
    result = dashboard.build(output=out, inventory_path=project["inventory"])
    assert out.is_file()
    assert result["documents"] == 2


def test_rendered_page_has_no_placeholder_left(project, tmp_path):
    out = tmp_path / "index.html"
    dashboard.build(output=out, inventory_path=project["inventory"])
    assert "/*DATA*/" not in out.read_text(encoding="utf-8")


def test_embedded_payload_is_valid_json(project, tmp_path):
    out = tmp_path / "index.html"
    dashboard.build(output=out, inventory_path=project["inventory"])
    html = out.read_text(encoding="utf-8")
    payload = re.search(
        r'<script id="payload" type="application/json">(.*?)</script>', html, re.S
    ).group(1)
    assert json.loads(payload)["summary"]["total"] == 2


def test_page_is_self_contained_with_no_external_requests(project, tmp_path):
    """It must open from a file path with no network, on any machine."""
    out = tmp_path / "index.html"
    dashboard.build(output=out, inventory_path=project["inventory"])
    html = out.read_text(encoding="utf-8")
    assert "<script src=" not in html
    assert 'rel="stylesheet"' not in html
    assert "http://" not in html.replace("http://www.w3.org", "")


def test_both_themes_are_defined(project, tmp_path):
    """A colour defined only under a dark media query renders unreadable
    for viewers whose OS is set to light."""
    out = tmp_path / "index.html"
    dashboard.build(output=out, inventory_path=project["inventory"])
    html = out.read_text(encoding="utf-8")
    base = re.search(r":root\{(.*?)\}", html, re.S).group(1)
    declared = set(re.findall(r"(--[\w-]+):", base))
    used = set(re.findall(r"var\((--[\w-]+)\)", html))
    assert not (used - declared), f"undefined in base :root: {used - declared}"


def test_html_is_escaped_in_the_payload(project, tmp_path, monkeypatch):
    """A document title containing markup must not break out of the script."""
    blogs = project["root"] / "blogs"
    (blogs / "evil.md").write_text("# Test\n\nBody.\n", encoding="utf-8")
    inv = project["root"] / "evil-inventory.yaml"
    inv.write_text(yaml.dump({"roi_google_docs": [{
        "title": "</script><img src=x onerror=alert(1)>",
        "local_file": str(blogs / "evil.md"),
        "score": 50, "publishable": False,
    }]}), encoding="utf-8")

    out = project["root"] / "evil.html"
    dashboard.build(output=out, inventory_path=inv)
    html = out.read_text(encoding="utf-8")

    payload = re.search(
        r'<script id="payload" type="application/json">(.*?)</script>', html, re.S
    ).group(1)
    # The closing tag must not survive verbatim inside the payload.
    assert "</script>" not in payload
    assert json.loads(payload)


def test_missing_inventory_raises_rather_than_writing_a_broken_page(tmp_path):
    with pytest.raises(OSError):
        dashboard.build(output=tmp_path / "x.html",
                        inventory_path=tmp_path / "absent.yaml")
