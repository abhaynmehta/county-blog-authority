"""Tests for the agent commands.

These were the untested half of the system. The decay parser in particular
had never seen a real Search Console export, so its column handling is
covered here against the shapes GSC actually produces.
"""

import csv
import json
from pathlib import Path

import pytest

from search_authority import agent


@pytest.fixture(autouse=True)
def logs_in_tmp(tmp_path, monkeypatch):
    """Keep every test's log writes inside tmp_path."""
    monkeypatch.setattr(agent, "AGENT_LOG", tmp_path / "agent-logs")
    return tmp_path


def write_csv(path: Path, headers: list[str], rows: list[list]):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)
    return path


# --- Column detection ---

def test_finds_gsc_comparison_columns():
    """Search Console names columns after the chosen range."""
    headers = [
        "Top pages",
        "Clicks Last 28 days", "Clicks Previous 28 days",
        "Impressions Last 28 days", "Impressions Previous 28 days",
    ]
    current, previous = agent._find_comparison_columns(headers)
    assert current == "Impressions Last 28 days"
    assert previous == "Impressions Previous 28 days"


def test_finds_columns_for_a_three_month_range():
    headers = ["Top pages", "Impressions Last 3 months", "Impressions Previous 3 months"]
    current, previous = agent._find_comparison_columns(headers)
    assert (current, previous) == (
        "Impressions Last 3 months", "Impressions Previous 3 months",
    )


def test_finds_plain_lowercase_columns():
    headers = ["page", "impressions", "prev_impressions"]
    current, previous = agent._find_comparison_columns(headers)
    assert (current, previous) == ("impressions", "prev_impressions")


def test_page_column_matches_any_common_name():
    for header in ["Top pages", "page", "URL", "Landing Page"]:
        assert agent._find_column([header, "Impressions"], ["top pages", "page", "url", "landing page"])


# --- Decay detection ---

def test_detects_a_page_past_the_decay_threshold(tmp_path):
    path = write_csv(
        tmp_path / "gsc.csv",
        ["Top pages", "Impressions Last 28 days", "Impressions Previous 28 days"],
        [["https://x.in/a", 50, 100],    # -50%, decaying
         ["https://x.in/b", 95, 100]],   # -5%, fine
    )
    result = agent.check_content_decay(str(path))
    assert result["decaying"] == 1
    assert result["pages"][0]["page"] == "https://x.in/a"
    assert result["pages"][0]["change_pct"] == -50.0


def test_exactly_twenty_percent_counts_as_decay(tmp_path):
    path = write_csv(
        tmp_path / "gsc.csv",
        ["Top pages", "Impressions Last 28 days", "Impressions Previous 28 days"],
        [["https://x.in/a", 80, 100]],
    )
    assert agent.check_content_decay(str(path))["decaying"] == 1


def test_growth_is_never_reported_as_decay(tmp_path):
    path = write_csv(
        tmp_path / "gsc.csv",
        ["Top pages", "Impressions Last 28 days", "Impressions Previous 28 days"],
        [["https://x.in/a", 200, 100]],
    )
    assert agent.check_content_decay(str(path))["decaying"] == 0


def test_new_pages_with_no_history_are_skipped(tmp_path):
    """A page with zero previous impressions has not decayed; it is new."""
    path = write_csv(
        tmp_path / "gsc.csv",
        ["Top pages", "Impressions Last 28 days", "Impressions Previous 28 days"],
        [["https://x.in/new", 10, 0]],
    )
    assert agent.check_content_decay(str(path))["decaying"] == 0


def test_thousands_separators_are_parsed(tmp_path):
    """GSC exports numbers as "1,234"."""
    path = write_csv(
        tmp_path / "gsc.csv",
        ["Top pages", "Impressions Last 28 days", "Impressions Previous 28 days"],
        [["https://x.in/a", "1,000", "5,000"]],
    )
    result = agent.check_content_decay(str(path))
    assert result["decaying"] == 1
    assert result["pages"][0]["change_pct"] == -80.0


def test_decaying_pages_are_ordered_worst_first(tmp_path):
    path = write_csv(
        tmp_path / "gsc.csv",
        ["Top pages", "Impressions Last 28 days", "Impressions Previous 28 days"],
        [["https://x.in/mild", 70, 100], ["https://x.in/severe", 10, 100]],
    )
    pages = agent.check_content_decay(str(path))["pages"]
    assert [p["page"] for p in pages] == ["https://x.in/severe", "https://x.in/mild"]


def test_unparseable_rows_are_counted_not_crashed_on(tmp_path):
    path = write_csv(
        tmp_path / "gsc.csv",
        ["Top pages", "Impressions Last 28 days", "Impressions Previous 28 days"],
        [["https://x.in/a", "n/a", "100"], ["https://x.in/b", 10, 100]],
    )
    result = agent.check_content_decay(str(path))
    assert result["skipped_unparseable"] == 1
    assert result["decaying"] == 1


# --- Error handling ---

def test_missing_file_reports_an_error(tmp_path):
    assert "error" in agent.check_content_decay(str(tmp_path / "nope.csv"))


def test_export_without_comparison_columns_explains_what_to_do(tmp_path):
    """The commonest mistake: exporting without enabling date comparison."""
    path = write_csv(
        tmp_path / "gsc.csv", ["Top pages", "Clicks", "Impressions"],
        [["https://x.in/a", 5, 100]],
    )
    result = agent.check_content_decay(str(path))
    assert "error" in result
    assert "comparison" in result["error"].lower()
    assert result["headers_seen"]


def test_export_without_a_page_column_reports_the_headers(tmp_path):
    path = write_csv(
        tmp_path / "gsc.csv",
        ["Query", "Impressions Last 28 days", "Impressions Previous 28 days"],
        [["flats noida", 10, 100]],
    )
    result = agent.check_content_decay(str(path))
    assert "No page column" in result["error"]


# --- Health report ---

def test_health_report_counts_and_averages(monkeypatch):
    monkeypatch.setattr(agent, "load_inventory", lambda: {
        "roi_google_docs": [
            {"title": "A", "score": 90, "publishable": True, "status": "audited"},
            {"title": "B", "score": 70, "publishable": False, "status": "audited"},
        ]
    })
    report = agent.generate_health_report()
    assert report["total_docs"] == 2
    assert report["avg_score"] == 80.0
    assert report["publishable"] == 1
    assert report["publishable_pct"] == 50.0


def test_health_report_ignores_entries_never_audited(monkeypatch):
    monkeypatch.setattr(agent, "load_inventory", lambda: {
        "roi_google_docs": [
            {"title": "A", "score": 90, "publishable": True, "status": "audited"},
            {"title": "B", "status": "pending"},  # no score yet
        ]
    })
    assert agent.generate_health_report()["total_docs"] == 1


def test_health_report_on_empty_inventory_reports_an_error(monkeypatch):
    monkeypatch.setattr(agent, "load_inventory", lambda: {})
    assert "error" in agent.generate_health_report()


# --- Watch ---

def test_watch_on_a_missing_directory_reports_an_error():
    assert "error" in agent.watch_and_audit(directory="no/such/dir")


def test_watch_ignores_files_already_in_the_inventory(tmp_path, monkeypatch):
    blogs = tmp_path / "incoming"
    blogs.mkdir()
    existing = blogs / "already-done.md"
    existing.write_text("# Done\n\nBody.\n", encoding="utf-8")

    monkeypatch.setattr(agent, "load_inventory", lambda: {
        "roi_google_docs": [{"local_file": str(existing), "status": "audited"}]
    })
    result = agent.watch_and_audit(directory=str(blogs))
    assert result["new_files"] == 0


# --- Link checking ---

def test_link_check_flags_a_404(monkeypatch):
    import urllib.error

    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result = agent.check_links(urls=["https://www.countygroup.in/gone"])
    assert result["broken"] == 1
    assert result["results"][0]["status"] == 404


def test_link_check_records_a_redirect(monkeypatch):
    class FakeResponse:
        status = 200
        def geturl(self): return "https://www.cleocounty.com/mobile/"
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: FakeResponse())
    result = agent.check_links(urls=["https://www.cleocounty.com/"])
    assert result["redirected"] == 1
    assert result["results"][0]["redirected_to"].endswith("/mobile/")


def test_link_check_survives_a_network_failure(monkeypatch):
    def boom(*a, **k):
        raise OSError("dns failure")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    result = agent.check_links(urls=["https://www.countygroup.in/"])
    assert result["broken"] == 1
    assert "dns failure" in result["results"][0]["error"]
