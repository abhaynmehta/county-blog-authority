"""Tests for the Truth Layer registry loader and its wiring into the auditor."""

from datetime import date
from pathlib import Path

import pytest

from search_authority.truth_layer import (
    Claim, load_truth_layer, registry_report,
)
from search_authority.content_auditor import audit_text


@pytest.fixture
def registry(tmp_path: Path) -> Path:
    """A minimal two-file registry with one fresh and one stale claim."""
    claims = tmp_path / "claims"
    claims.mkdir(parents=True)
    (claims / "infrastructure.yaml").write_text(
        "claim_category: infrastructure\n"
        "claims:\n"
        "  - claim_id: T_001\n"
        "    claim: Airport is operational\n"
        "    status: operational\n"
        "    source: https://example.org/a\n"
        "    last_verified: 2026-08-01\n"
        "    refresh_days: 30\n"
        "  - claim_id: T_002\n"
        "    claim: Metro phase 2\n"
        "    status: null\n"
        "    source: null\n"
        "    last_verified: null\n"
        "    refresh_days: 30\n"
        "prohibited_wording:\n"
        '  - "upcoming airport" # it is operational\n'
        '  - "guaranteed connectivity improvement"\n',
        encoding="utf-8",
    )
    (claims / "amenities.yaml").write_text(
        "claim_category: amenities\n"
        "claims:\n"
        "  - claim_id: T_003\n"
        "    claim: Clubhouse is delivered\n"
        "    status: delivered\n"
        "    source: https://example.org/c\n"
        "    last_verified: 2026-08-25\n"
        "    refresh_days: 90\n",
        encoding="utf-8",
    )
    return tmp_path


# --- Loading ---

def test_loads_claims_from_every_file(registry):
    layer = load_truth_layer(registry)
    assert {c.claim_id for c in layer.claims} == {"T_001", "T_002", "T_003"}


def test_category_comes_from_the_file(registry):
    layer = load_truth_layer(registry)
    assert layer.by_id("T_003").category == "amenities"


def test_prohibited_wording_strips_yaml_comments(registry):
    layer = load_truth_layer(registry)
    assert "upcoming airport" in layer.prohibited_wording
    assert not any("#" in p for p in layer.prohibited_wording)


def test_missing_directory_yields_empty_layer_not_an_error(tmp_path):
    layer = load_truth_layer(tmp_path / "does-not-exist")
    assert layer.is_empty


def test_malformed_yaml_is_skipped_not_raised(tmp_path):
    claims = tmp_path / "claims"
    claims.mkdir(parents=True)
    (claims / "broken.yaml").write_text("claims: [unclosed\n", encoding="utf-8")
    assert load_truth_layer(tmp_path).is_empty


# --- Staleness ---

def test_claim_past_its_ttl_is_stale(registry):
    layer = load_truth_layer(registry)
    # verified 2026-08-01, TTL 30 days -> stale from 2026-09-01
    assert layer.by_id("T_001").is_stale(date(2026, 9, 5))


def test_claim_within_its_ttl_is_not_stale(registry):
    layer = load_truth_layer(registry)
    assert not layer.by_id("T_001").is_stale(date(2026, 8, 20))


def test_never_verified_claim_is_incomplete_rather_than_stale(registry):
    """A claim nobody ever checked is a different problem from an expired one."""
    claim = load_truth_layer(registry).by_id("T_002")
    assert not claim.is_stale(date(2027, 1, 1))
    assert claim.is_incomplete()


def test_days_overdue_counts_from_ttl_expiry(registry):
    claim = load_truth_layer(registry).by_id("T_001")
    assert claim.days_overdue(date(2026, 9, 5)) == 5


def test_days_overdue_is_zero_when_fresh(registry):
    claim = load_truth_layer(registry).by_id("T_001")
    assert claim.days_overdue(date(2026, 8, 10)) == 0


def test_missing_fields_names_each_gap(registry):
    claim = load_truth_layer(registry).by_id("T_002")
    assert set(claim.missing_fields()) == {"status", "source", "last_verified"}


def test_complete_claim_reports_no_gaps(registry):
    assert load_truth_layer(registry).by_id("T_001").missing_fields() == []


# --- Report ---

def test_registry_report_separates_stale_from_incomplete(registry):
    report = registry_report(registry, today=date(2026, 9, 5))
    assert report["total_claims"] == 3
    assert [c["claim_id"] for c in report["stale"]] == ["T_001"]
    assert [c["claim_id"] for c in report["incomplete"]] == ["T_002"]


def test_registry_report_orders_stale_by_most_overdue(tmp_path):
    claims = tmp_path / "claims"
    claims.mkdir(parents=True)
    (claims / "c.yaml").write_text(
        "claim_category: c\nclaims:\n"
        "  - {claim_id: A, claim: a, status: s, source: u,"
        " last_verified: 2026-08-01, refresh_days: 30}\n"
        "  - {claim_id: B, claim: b, status: s, source: u,"
        " last_verified: 2026-06-01, refresh_days: 30}\n",
        encoding="utf-8",
    )
    report = registry_report(tmp_path, today=date(2026, 9, 5))
    assert [c["claim_id"] for c in report["stale"]] == ["B", "A"]


# --- Auditor wiring ---

def test_auditor_flags_registry_prohibited_wording(monkeypatch, registry):
    """The point of the registry: editing YAML changes what audits enforce."""
    import search_authority.content_auditor as ca
    monkeypatch.setattr(ca, "load_truth_layer", lambda *a: load_truth_layer(registry))

    text = "# Title\n\nWe offer guaranteed connectivity improvement to buyers.\n"
    result = audit_text(text)

    assert any(i.editorial_rule == "TRUTH_LAYER_PROHIBITED" for i in result.issues)


def test_registry_wording_is_not_double_reported_with_builtin_patterns(monkeypatch, registry):
    """'upcoming airport' is caught by a built-in pattern; it must not fire twice."""
    import search_authority.content_auditor as ca
    monkeypatch.setattr(ca, "load_truth_layer", lambda *a: load_truth_layer(registry))

    text = "# Title\n\nThe upcoming airport will help the area.\n"
    result = audit_text(text)

    flagged = [i for i in result.issues if i.paragraph == 2]
    truth_hits = [i for i in flagged if i.editorial_rule == "TRUTH_LAYER_PROHIBITED"]
    assert truth_hits == [], "built-in pattern already covers this paragraph"


def test_audit_still_works_when_registry_is_absent(monkeypatch, tmp_path):
    """No county_context/ must degrade to built-in rules, not crash."""
    import search_authority.content_auditor as ca
    monkeypatch.setattr(ca, "load_truth_layer", lambda *a: load_truth_layer(tmp_path))

    result = audit_text("# Title\n\nA normal paragraph about flats.\n")
    assert isinstance(result.score, int)
