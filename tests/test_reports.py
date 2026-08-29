"""Tests for week-over-week performance analysis.

Two things matter here: the column detection must survive whatever the
platform calls its fields, and the analysis must decompose changes correctly
— a wrong "why" is worse than no "why", because it sends someone to fix the
wrong thing.
"""

import csv
from pathlib import Path

import pytest

from search_authority.reports import (
    Row, compare, explain, load_leads, load_rows, weekly_report, _decompose, _number,
)


def write(path: Path, headers: list[str], rows: list[list]) -> Path:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)
    return path


META = ["Campaign name", "Impressions", "Link clicks", "Amount spent (INR)", "Results"]
GOOGLE = ["Campaign", "Impr.", "Clicks", "Cost", "Conversions"]


# ── Cell parsing ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("cell,expected", [
    ("1234", 1234.0), ("1,234", 1234.0), ("₹1,234.50", 1234.5),
    ("Rs 5,000", 5000.0), ("12%", 12.0), ("", None), ("--", None),
    ("n/a", None), ("—", None), ("not a number", None), (None, None),
])
def test_spreadsheet_cells_are_parsed(cell, expected):
    assert _number(cell) == expected


# ── Column detection ──────────────────────────────────────────────────────

def test_meta_columns_are_detected(tmp_path):
    path = write(tmp_path / "m.csv", META, [["A", 1000, 50, "5,000", 5]])
    _, meta = load_rows(path)
    assert meta["columns_used"]["spend"] == "Amount spent (INR)"
    assert meta["columns_used"]["leads"] == "Results"


def test_google_columns_are_detected(tmp_path):
    path = write(tmp_path / "g.csv", GOOGLE, [["A", 1000, 50, "5,000", 5]])
    _, meta = load_rows(path)
    assert meta["columns_used"]["impressions"] == "Impr."
    assert meta["columns_used"]["leads"] == "Conversions"


def test_a_totals_row_is_not_treated_as_a_campaign(tmp_path):
    """Every platform export ends with one."""
    path = write(tmp_path / "t.csv", META,
                 [["A", 1000, 50, "5,000", 5], ["Total: all campaigns", 1000, 50, "5,000", 5]])
    rows, _ = load_rows(path)
    assert [r.name for r in rows] == ["A"]


def test_an_export_without_a_campaign_column_reports_why(tmp_path):
    path = write(tmp_path / "x.csv", ["Date", "Spend"], [["2026-08-01", 100]])
    rows, meta = load_rows(path)
    assert rows == [] and "no campaign" in meta["error"]


def test_a_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_rows(tmp_path / "absent.csv")


# ── Derived metrics ───────────────────────────────────────────────────────

def test_derived_metrics_are_computed():
    row = Row("A", {"impressions": 1000.0, "clicks": 50.0, "spend": 500.0, "leads": 5.0})
    row.derive()
    assert row.metrics["ctr"] == 5.0      # 50/1000
    assert row.metrics["cpc"] == 10.0     # 500/50
    assert row.metrics["cvr"] == 10.0     # 5/50
    assert row.metrics["cpl"] == 100.0    # 500/5


def test_division_by_zero_is_skipped_not_crashed_on():
    row = Row("A", {"spend": 500.0, "leads": 0.0, "clicks": 0.0})
    row.derive()
    assert "cpl" not in row.metrics and "cpc" not in row.metrics


# ── Comparison ────────────────────────────────────────────────────────────

def test_change_percentages_are_computed():
    previous = [Row("A", {"leads": 100.0})]
    current = [Row("A", {"leads": 150.0})]
    assert compare(previous, current)["rows"][0]["change"]["leads"] == 50.0


def test_a_new_campaign_is_labelled_new():
    result = compare([], [Row("B", {"leads": 10.0})])
    assert result["rows"][0]["status"] == "new"


def test_a_campaign_that_disappeared_is_labelled_stopped():
    result = compare([Row("A", {"leads": 10.0})], [])
    assert result["rows"][0]["status"] == "stopped"


def test_totals_recompute_ratios_rather_than_averaging_them():
    """Averaging per-campaign CPL would weight a tiny campaign equally."""
    previous = [Row("A", {"spend": 100.0, "leads": 10.0}),
                Row("B", {"spend": 900.0, "leads": 10.0})]
    current = [Row("A", {"spend": 100.0, "leads": 10.0}),
               Row("B", {"spend": 900.0, "leads": 10.0})]
    totals = compare(previous, current)["totals"]
    assert totals["cpl"]["current"] == 50.0   # 1000 spend / 20 leads


# ── Decomposition ─────────────────────────────────────────────────────────

def test_decompose_names_the_input_that_moved():
    assert "click-through down 40.0%" in _decompose(-40.0, 2.0, 1.0)


def test_decompose_ignores_movement_below_the_noise_floor():
    assert "No single input moved materially" in _decompose(3.0, -2.0, 1.0)


def test_decompose_distinguishes_creative_from_landing_page():
    """A CTR fall is creative; a CVR fall is the landing page. Naming the
    wrong one sends someone to fix the wrong thing."""
    assert "creative" in _decompose(-30.0, 0.0, 0.0)
    assert "landing page" in _decompose(0.0, -30.0, 0.0)


# ── Findings ──────────────────────────────────────────────────────────────

def test_spend_up_with_leads_down_is_critical():
    comparison = {"totals": {
        "spend": {"change_pct": 30.0}, "leads": {"change_pct": -20.0},
        "ctr": {"change_pct": -35.0},
    }, "rows": []}
    finding = explain(comparison)[0]
    assert finding["severity"] == "critical"
    assert "click-through" in finding["why"]


def test_improving_efficiency_is_reported_as_good():
    comparison = {"totals": {
        "spend": {"change_pct": 5.0}, "leads": {"change_pct": 40.0},
    }, "rows": []}
    assert explain(comparison)[0]["severity"] == "good"


def test_a_quiet_week_produces_one_no_change_finding():
    comparison = {"totals": {"spend": {"change_pct": 1.0},
                             "leads": {"change_pct": 2.0}}, "rows": []}
    findings = explain(comparison)
    assert len(findings) == 1 and findings[0]["severity"] == "info"


def test_a_stopped_campaign_is_surfaced():
    comparison = {"totals": {}, "rows": [
        {"name": "Old", "status": "stopped", "change": {}, "previous": {}, "current": {}}
    ]}
    assert any("stopped running" in f["headline"] for f in explain(comparison))


# ── Lead quality ──────────────────────────────────────────────────────────

def test_lead_statuses_are_bucketed(tmp_path):
    path = write(tmp_path / "l.csv", ["Lead ID", "Campaign name", "Status"], [
        [1, "A", "Qualified"], [2, "A", "Booked"], [3, "A", "Disqualified"],
        [4, "A", "Pending"], [5, "A", ""],
    ])
    leads = load_leads(path)
    assert (leads["qualified"], leads["booked"], leads["disqualified"], leads["pending"]) == (1, 1, 1, 2)


def test_booked_leads_count_toward_the_qualified_rate():
    """A booked lead is qualified by definition."""
    import tempfile
    path = Path(tempfile.mkdtemp()) / "l.csv"
    write(path, ["Lead ID", "Status"], [[1, "Booked"], [2, "Qualified"],
                                        [3, "Disqualified"], [4, "Disqualified"]])
    assert load_leads(path)["qualified_rate"] == 50.0


def test_disqualified_is_not_read_as_qualified(tmp_path):
    """'Disqualified' contains 'qualif'; order of checks matters."""
    path = write(tmp_path / "l.csv", ["Lead ID", "Status"], [[1, "Disqualified"]])
    leads = load_leads(path)
    assert leads["disqualified"] == 1 and leads["qualified"] == 0


def test_a_low_qualified_rate_is_flagged_high(tmp_path):
    path = write(tmp_path / "l.csv", ["Lead ID", "Status"],
                 [[i, "Disqualified"] for i in range(9)] + [[9, "Qualified"]])
    findings = explain({"totals": {}, "rows": []}, load_leads(path))
    assert any(f["severity"] == "high" and "qualified" in f["headline"] for f in findings)


def test_a_campaign_buying_unqualified_volume_is_named(tmp_path):
    path = write(tmp_path / "l.csv", ["Lead ID", "Campaign name", "Status"],
                 [[i, "Bad Campaign", "Disqualified"] for i in range(8)])
    findings = explain({"totals": {}, "rows": []}, load_leads(path))
    assert any("Bad Campaign" in f["headline"] for f in findings)


# ── End to end ────────────────────────────────────────────────────────────

def test_weekly_report_runs_end_to_end(tmp_path):
    previous = write(tmp_path / "p.csv", META, [["A", 100000, 2000, "150,000", 80]])
    current = write(tmp_path / "c.csv", META, [["A", 105000, 1200, "180,000", 50]])
    leads = write(tmp_path / "l.csv", ["Lead ID", "Campaign name", "Status"],
                  [[1, "A", "Disqualified"], [2, "A", "Qualified"]])

    report = weekly_report(previous, current, leads)

    assert report["totals"]["leads"]["change_pct"] == -37.5
    assert report["leads"]["total"] == 2
    assert any(f["severity"] == "critical" for f in report["findings"])


def test_weekly_report_works_without_lead_data(tmp_path):
    previous = write(tmp_path / "p.csv", META, [["A", 100, 10, "100", 1]])
    current = write(tmp_path / "c.csv", META, [["A", 200, 20, "200", 2]])
    report = weekly_report(previous, current)
    assert report["leads"] is None and report["findings"]
