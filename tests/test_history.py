"""Tests for the audit ledger.

The ledger exists to answer one question an individual audit cannot: is the
same mistake coming back? So the tests centre on the distinction between a
problem never fixed and one fixed then reintroduced, which are different
conversations to have with an agency.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from search_authority.content_auditor import audit_text
from search_authority.history import (
    Entry, document_trend, load, owner_scorecard, recurring_mistakes,
    record, regressions, summary,
)


@pytest.fixture
def ledger(tmp_path) -> Path:
    return tmp_path / "ledger.jsonl"


def write_entry(ledger: Path, slug: str, day: int, categories: list[str],
                score: int = 70, publishable: bool = False,
                owners: list[str] | None = None) -> None:
    entry = Entry(
        slug=slug,
        audited_at=(datetime(2026, 6, 1) + timedelta(days=day)).isoformat(timespec="seconds"),
        score=score, publishable=publishable,
        issue_ids=[f"X-{i}" for i in range(len(categories))],
        categories=sorted(categories), owners=owners or ["ROI"], failed_gates=[],
    )
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry.as_dict()) + "\n")


# ── Recording ─────────────────────────────────────────────────────────────

def test_an_audit_is_appended_to_the_ledger(ledger):
    result = audit_text("# T\n\nThe best investment with guaranteed appreciation.\n")
    record(result, slug="a", ledger=ledger)
    entries = load(ledger)
    assert len(entries) == 1 and entries[0].slug == "a"


def test_the_ledger_is_append_only(ledger):
    """A record of what was true on a date must not be quietly revised."""
    result = audit_text("# T\n\nSome content here.\n")
    record(result, slug="a", ledger=ledger)
    record(result, slug="a", ledger=ledger)
    assert len(load(ledger)) == 2


def test_categories_rather_than_issue_ids_identify_a_mistake(ledger):
    """Issue ids are positional and shift when unrelated text is edited, so
    they cannot identify 'the same mistake' across runs."""
    result = audit_text("# T\n\nThe best investment in Noida.\n")
    entry = record(result, slug="a", ledger=ledger)
    assert "prohibited_language" in entry.categories


def test_a_corrupt_line_is_skipped_not_fatal(ledger):
    write_entry(ledger, "a", 0, ["rera_compliance"])
    with open(ledger, "a", encoding="utf-8") as handle:
        handle.write("this is not json\n")
    write_entry(ledger, "b", 1, ["rera_compliance"])
    assert len(load(ledger)) == 2


def test_an_absent_ledger_reads_as_empty(tmp_path):
    assert load(tmp_path / "nothing.jsonl") == []


# ── Trend ─────────────────────────────────────────────────────────────────

def test_a_document_that_improved_shows_a_positive_change(ledger):
    write_entry(ledger, "a", 0, ["rera_compliance"], score=40)
    write_entry(ledger, "a", 7, [], score=85)
    trend = document_trend(load(ledger))[0]
    assert trend["change"] == 45 and trend["runs"] == 2


def test_a_document_audited_once_has_no_trend(ledger):
    write_entry(ledger, "a", 0, ["rera_compliance"])
    assert document_trend(load(ledger)) == []


def test_trends_list_the_worst_decline_first(ledger):
    write_entry(ledger, "improved", 0, [], score=40)
    write_entry(ledger, "improved", 5, [], score=80)
    write_entry(ledger, "declined", 0, [], score=80)
    write_entry(ledger, "declined", 5, [], score=40)
    assert document_trend(load(ledger))[0]["slug"] == "declined"


# ── Recurring mistakes ────────────────────────────────────────────────────

def test_a_category_across_several_documents_is_recurring(ledger):
    for slug in ("a", "b", "c"):
        write_entry(ledger, slug, 0, ["rera_compliance"])
    recurring = recurring_mistakes(load(ledger))
    assert recurring[0]["category"] == "rera_compliance"
    assert recurring[0]["documents"] == 3


def test_one_document_audited_repeatedly_is_not_a_systemic_problem(ledger):
    """Counting occurrences rather than documents would make a single blog
    audited twenty times look like a pattern across the corpus."""
    for day in range(20):
        write_entry(ledger, "a", day, ["rera_compliance"])
    assert recurring_mistakes(load(ledger)) == []


def test_only_the_latest_run_of_each_document_counts(ledger):
    """A problem fixed last week should not still be reported as current."""
    write_entry(ledger, "a", 0, ["rera_compliance"])
    write_entry(ledger, "a", 7, [])
    write_entry(ledger, "b", 0, ["rera_compliance"])
    assert recurring_mistakes(load(ledger), min_documents=1)[0]["documents"] == 1


def test_the_share_is_of_documents_not_runs(ledger):
    write_entry(ledger, "a", 0, ["rera_compliance"])
    write_entry(ledger, "b", 0, [])
    assert recurring_mistakes(load(ledger), min_documents=1)[0]["share_pct"] == 50.0


# ── Regressions ───────────────────────────────────────────────────────────

def test_an_issue_fixed_then_returning_is_a_regression(ledger):
    write_entry(ledger, "a", 0, ["rera_compliance"])
    write_entry(ledger, "a", 7, [])
    write_entry(ledger, "a", 14, ["rera_compliance"])
    found = regressions(load(ledger))
    assert found and found[0]["category"] == "rera_compliance"


def test_an_issue_never_fixed_is_not_a_regression(ledger):
    """Never addressed and fixed-then-broken are different conversations."""
    for day in (0, 7, 14):
        write_entry(ledger, "a", day, ["rera_compliance"])
    assert regressions(load(ledger)) == []


def test_an_issue_fixed_and_left_fixed_is_not_a_regression(ledger):
    write_entry(ledger, "a", 0, ["rera_compliance"])
    write_entry(ledger, "a", 7, [])
    write_entry(ledger, "a", 14, [])
    assert regressions(load(ledger)) == []


def test_two_runs_are_too_few_to_show_a_regression(ledger):
    write_entry(ledger, "a", 0, ["rera_compliance"])
    write_entry(ledger, "a", 7, ["rera_compliance"])
    assert regressions(load(ledger)) == []


def test_a_regression_records_when_it_was_fixed_and_when_it_returned(ledger):
    write_entry(ledger, "a", 0, ["rera_compliance"])
    write_entry(ledger, "a", 10, [])
    write_entry(ledger, "a", 20, ["rera_compliance"])
    found = regressions(load(ledger))[0]
    assert found["fixed_on"] == "2026-06-11"
    assert found["returned_on"] == "2026-06-21"


# ── Owners ────────────────────────────────────────────────────────────────

def test_the_scorecard_counts_documents_per_owner(ledger):
    write_entry(ledger, "a", 0, ["rera_compliance"], owners=["ROI"])
    write_entry(ledger, "b", 0, ["schema_missing"], owners=["AGO"])
    write_entry(ledger, "c", 0, ["rera_compliance"], owners=["ROI"])
    assert owner_scorecard(load(ledger))["by_owner"] == {"ROI": 2, "AGO": 1}


# ── Summary ───────────────────────────────────────────────────────────────

def test_an_empty_ledger_summarises_without_failing(tmp_path):
    result = summary(tmp_path / "none.jsonl")
    assert result["runs"] == 0 and "message" in result


def test_the_summary_separates_improved_from_declined(ledger):
    write_entry(ledger, "up", 0, [], score=40)
    write_entry(ledger, "up", 5, [], score=80)
    write_entry(ledger, "down", 0, [], score=80)
    write_entry(ledger, "down", 5, [], score=40)
    result = summary(ledger)
    assert [d["slug"] for d in result["improved"]] == ["up"]
    assert [d["slug"] for d in result["declined"]] == ["down"]


def test_the_summary_reports_the_current_average_not_the_historical_one(ledger):
    """Averaging every run would let old bad scores drag the number down long
    after the content was fixed."""
    write_entry(ledger, "a", 0, [], score=20)
    write_entry(ledger, "a", 5, [], score=90)
    assert summary(ledger)["average_score_now"] == 90.0
