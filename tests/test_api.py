"""Tests for the HTTP API.

The API must stay a thin transport over the engine. These check the contract
the dashboard depends on, and that the API never reaches a different verdict
than the CLI would on the same text.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from search_authority.content_auditor import audit_text

client = TestClient(app)


BAD = ("# Center Court\n\n"
       "The Center Court in Noida offers homes.\n"
       "Registered under UP-RERA, with assured returns.\n")

GOOD = ("# The Center Court\n\n"
        "Meta Title: The Center Court Sector 88-A Gurugram Homes\n"
        "Meta Description: A guide to The Center Court in Sector 88-A Gurugram, "
        "with carpet areas, HARERA registration details and verified sources.\n\n"
        "The Center Court is in Sector 88-A, Gurugram, Haryana, registered with "
        "HARERA. Carpet area is 888 sq ft for Type A.\n")


# ── Health ────────────────────────────────────────────────────────────────

def test_health_reports_ok_and_loads_the_registry():
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["projects_loaded"] >= 1


def test_health_surfaces_registry_load_errors():
    """A registry file that stops parsing must be visible, not silent."""
    assert client.get("/health").json()["registry_errors"] == []


# ── Audit ─────────────────────────────────────────────────────────────────

def test_audit_returns_a_score_and_gates():
    body = client.post("/audit", json={"content": GOOD, "slug": "cc"}).json()
    assert 0 <= body["score"] <= 100
    assert {g["gate"] for g in body["gates"]}


def test_audit_matches_the_engine_exactly():
    """The API must never disagree with the CLI on the same text."""
    api_score = client.post("/audit", json={"content": BAD}).json()["score"]
    assert api_score == audit_text(BAD).score


def test_audit_flags_the_wrong_city_as_critical():
    issues = client.post("/audit", json={"content": BAD}).json()["issues"]
    criticals = [i for i in issues if i["severity"] == "critical"]
    assert any("Gurugram" in i["summary"] for i in criticals)


def test_audit_returns_quoted_text_for_locatable_issues():
    issues = client.post("/audit", json={"content": BAD}).json()["issues"]
    assert any(i.get("quoted_text") for i in issues)


def test_audit_includes_an_acceptance_test_on_every_issue():
    """An issue without a done-when line is not actionable."""
    issues = client.post("/audit", json={"content": BAD}).json()["issues"]
    assert issues and all(i["acceptance_test"] for i in issues)


def test_audit_assigns_an_owner_to_every_issue():
    issues = client.post("/audit", json={"content": BAD}).json()["issues"]
    assert all(i["owner"] in {"ROI", "AGO", "BOTH", "INTERNAL"} for i in issues)


def test_audit_counts_match_the_issue_list():
    body = client.post("/audit", json={"content": BAD}).json()
    assert sum(body["counts"].values()) == len(body["issues"])


def test_empty_content_is_rejected():
    assert client.post("/audit", json={"content": "   "}).status_code == 422


def test_missing_content_field_is_rejected():
    assert client.post("/audit", json={"slug": "x"}).status_code == 422


def test_oversized_content_is_rejected():
    huge = "word " * 60_000
    assert client.post("/audit", json={"content": huge}).status_code == 413


def test_audit_is_deterministic_across_calls():
    a = client.post("/audit", json={"content": BAD}).json()["score"]
    b = client.post("/audit", json={"content": BAD}).json()["score"]
    assert a == b


# ── Schema ────────────────────────────────────────────────────────────────

PASSING = (
    "# The Center Court\n\n"
    "Meta Title: The Center Court Sector 88-A Gurugram Homes Guide\n"
    "Meta Description: A guide to The Center Court in Sector 88-A Gurugram, "
    "covering carpet areas, HARERA registration and how to verify it.\n\n"
    "The Center Court is in Sector 88-A, Gurugram, Haryana, registered with "
    "HARERA under registration number RC/REP/HARERA/GGM/46 of "
    "2017/7(3)/45/2024/04. Carpet area is 888 sq ft for Type A.\n\n"
    "![Tower elevation](center-court.jpg)\n\n"
    "See the [HARERA portal](https://www.haryanarera.gov.in/) and the "
    "[project page](https://www.countygroup.in/centercourt/).\n\n"
    + ("Substantive sentence about the development. " * 200)
)


def test_schema_uses_the_supplied_publication_date():
    """A rerun must never rewrite publication history."""
    import json
    body = client.post("/schema", json={
        "content": PASSING, "slug": "cc", "date_published": "2026-06-01",
    }).json()
    assert json.loads(body["jsonld"])["@graph"][0]["datePublished"] == "2026-06-01"


def test_schema_requires_a_publication_date():
    response = client.post("/schema", json={"content": PASSING, "slug": "cc"})
    assert response.status_code == 422


def test_schema_is_refused_for_content_that_failed_a_gate():
    """Structured data must describe a page fit to publish."""
    response = client.post("/schema", json={
        "content": BAD, "slug": "cc", "date_published": "2026-06-01",
    })
    assert response.status_code == 409
    assert response.json()["detail"]["failed_gates"]


def test_schema_honours_a_supplied_canonical_url():
    body = client.post("/schema", json={
        "content": PASSING, "slug": "cc", "date_published": "2026-06-01",
        "canonical_url": "https://www.countygroup.in/blog/custom/",
    }).json()
    assert body["canonical_url"] == "https://www.countygroup.in/blog/custom/"


# ── Registry ──────────────────────────────────────────────────────────────

def test_projects_endpoint_exposes_verified_figures():
    projects = client.get("/projects").json()["projects"]
    names = {p["name"] for p in projects}
    assert "The Center Court" in names
    cc = next(p for p in projects if p["name"] == "The Center Court")
    assert cc["city"] == "Gurugram"
    assert cc["rera_authority"] == "HARERA"


def test_projects_endpoint_includes_prohibited_wording():
    assert client.get("/projects").json()["prohibited_wording"]


def test_registry_health_separates_stale_from_incomplete():
    body = client.get("/registry/health").json()
    assert "stale_count" in body and "incomplete_count" in body


# ── Corpus ────────────────────────────────────────────────────────────────

def test_corpus_endpoint_returns_documents_and_summary():
    body = client.get("/corpus").json()
    assert body["summary"]["total"] > 0
    assert isinstance(body["documents"], list)


def test_cannibalization_endpoint_returns_collisions_with_rebuttals():
    body = client.get("/cannibalization").json()
    assert "collisions" in body
    if body["details"]:
        assert body["details"][0]["not_fixed_by"]
