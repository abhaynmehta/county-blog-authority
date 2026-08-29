"""Tests for social post analysis.

Social data behaves unlike advertising data: no spend, one row per post, and
engagement measured against reach rather than cost against conversions. The
denominator choice is the thing most worth pinning down — raw like counts
reward a post that was simply pushed to more people.
"""

import csv
from datetime import date
from pathlib import Path

import pytest

from search_authority.social import (
    analyse, explain, load_posts, social_report, _number, _parse_date, _summarise,
)

HEADERS = [
    "sr.no", "Date Posted / Published", "Project Name", "URL", "Type",
    "Description", "Views", "Reach", "Likes", "Shares", "Follows",
    "Comments", "Saves",
]


def post_row(n, when, project, kind, reach, likes=0, shares=0, comments=0, saves=0):
    return [n, when, project, f"https://x/{n}", kind, "caption",
            0, reach, likes, shares, 0, comments, saves]


def write(path: Path, rows) -> Path:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADERS)
        writer.writerows(rows)
    return path


# ── Parsing ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("value,expected", [
    ("1234", 1234.0), ("1,234", 1234.0), ("", 0.0), ("-", 0.0), (None, 0.0),
    ("not a number", 0.0),
])
def test_cells_parse(value, expected):
    assert _number(value) == expected


@pytest.mark.parametrize("value,expected", [
    ("2026-06-17 02:47:00", date(2026, 6, 17)),
    ("2026-06-17", date(2026, 6, 17)),
    ("17/06/2026", date(2026, 6, 17)),
    ("", None),
    ("nonsense", None),
])
def test_dates_parse(value, expected):
    assert _parse_date(value) == expected


def test_columns_are_detected_from_the_real_export_shape(tmp_path):
    path = write(tmp_path / "s.csv", [post_row(1, "2026-06-17", "Clove", "Image", 1000)])
    _, meta = load_posts(path)
    assert meta["columns_used"]["reach"] == "Reach"
    assert meta["columns_used"]["project"] == "Project Name"


def test_engagement_sums_the_interaction_columns(tmp_path):
    path = write(tmp_path / "s.csv",
                 [post_row(1, "2026-06-17", "Clove", "Image", 1000,
                           likes=50, shares=10, comments=5, saves=5)])
    posts, _ = load_posts(path)
    assert posts[0]["engagement"] == 70
    assert posts[0]["engagement_rate"] == 7.0


def test_a_post_with_no_reach_does_not_divide_by_zero(tmp_path):
    path = write(tmp_path / "s.csv",
                 [post_row(1, "2026-06-17", "Clove", "Image", 0, likes=5)])
    assert load_posts(path)[0][0]["engagement_rate"] == 0.0


def test_views_are_used_when_reach_is_absent(tmp_path):
    """Some exports report views instead of reach."""
    path = tmp_path / "v.csv"
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Date", "Project Name", "Type", "Views", "Likes"])
        writer.writerow(["2026-06-17", "Clove", "Reel", 500, 50])
    posts, _ = load_posts(path)
    assert posts[0]["engagement_rate"] == 10.0


def test_an_export_without_reach_or_views_reports_why(tmp_path):
    path = tmp_path / "bad.csv"
    with open(path, "w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows([["Date", "Caption"], ["2026-06-17", "hi"]])
    posts, meta = load_posts(path)
    assert posts == [] and "no reach or views" in meta["error"]


def test_a_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_posts(tmp_path / "absent.csv")


# ── Aggregation ───────────────────────────────────────────────────────────

def test_engagement_rate_pools_totals_rather_than_averaging_rates():
    """Averaging per-post rates lets one tiny post with a freak rate dominate.
    Pooling weights each post by the audience it actually reached."""
    posts = [
        {"reach": 10, "engagement": 5, "engagement_rate": 50.0, "follows": 0},
        {"reach": 10_000, "engagement": 100, "engagement_rate": 1.0, "follows": 0},
    ]
    # Naive mean would be 25.5%; pooled is 105/10010.
    assert _summarise(posts)["engagement_rate"] == 1.05


def test_summary_of_no_posts_is_safe():
    assert _summarise([])["posts"] == 0


# ── Period splitting ──────────────────────────────────────────────────────

def test_periods_split_by_date_from_a_single_export(tmp_path):
    rows = [post_row(1, "2026-07-20", "Clove", "Image", 1000, likes=100),
            post_row(2, "2026-06-10", "Clove", "Image", 1000, likes=10)]
    posts, _ = load_posts(write(tmp_path / "s.csv", rows))
    result = analyse(posts, split_days=28, today=date(2026, 7, 25))
    assert result["current_period"]["posts"] == 1
    assert result["previous_period"]["posts"] == 1


def test_undated_posts_do_not_break_the_split(tmp_path):
    rows = [post_row(1, "2026-07-20", "Clove", "Image", 1000),
            post_row(2, "", "Clove", "Image", 500)]
    posts, _ = load_posts(write(tmp_path / "s.csv", rows))
    assert "error" not in analyse(posts, today=date(2026, 7, 25))


def test_an_export_with_no_dates_reports_why(tmp_path):
    posts, _ = load_posts(write(tmp_path / "s.csv",
                                [post_row(1, "", "Clove", "Image", 100)]))
    assert "error" in analyse(posts)


# ── Findings ──────────────────────────────────────────────────────────────

def test_a_fall_in_engagement_rate_is_flagged_high():
    analysis = {
        "window_days": 28,
        "current_period": {"posts": 5, "engagement_rate": 2.0, "reach": 1000},
        "previous_period": {"posts": 5, "engagement_rate": 10.0, "reach": 1000},
        "by_type": {}, "by_project": {},
    }
    findings = explain(analysis)
    assert any(f["severity"] == "high" and "Engagement rate down" in f["headline"]
               for f in findings)


def test_format_comparison_needs_enough_posts_to_be_meaningful():
    """Two posts of a format is not evidence about that format."""
    analysis = {
        "window_days": 28,
        "current_period": {"posts": 0}, "previous_period": {"posts": 0},
        "by_type": {"Carousel": {"posts": 2, "engagement_rate": 20.0, "reach": 100,
                                 "engagement": 20},
                    "Reel": {"posts": 2, "engagement_rate": 2.0, "reach": 100,
                             "engagement": 2}},
        "by_project": {},
    }
    assert not any("engage" in f["headline"] for f in explain(analysis))


def test_format_comparison_fires_with_a_large_enough_sample():
    analysis = {
        "window_days": 28,
        "current_period": {"posts": 0}, "previous_period": {"posts": 0},
        "by_type": {"Carousel": {"posts": 5, "engagement_rate": 20.0, "reach": 100,
                                 "engagement": 20},
                    "Reel": {"posts": 8, "engagement_rate": 2.0, "reach": 100,
                             "engagement": 2}},
        "by_project": {},
    }
    assert any("Carousel" in f["headline"] for f in explain(analysis))


def test_a_quiet_period_produces_one_no_change_finding():
    analysis = {
        "window_days": 28,
        "current_period": {"posts": 5, "engagement_rate": 5.0, "reach": 1000},
        "previous_period": {"posts": 5, "engagement_rate": 5.1, "reach": 1010},
        "by_type": {}, "by_project": {},
    }
    findings = explain(analysis)
    assert len(findings) == 1 and findings[0]["severity"] == "info"


# ── End to end ────────────────────────────────────────────────────────────

def test_social_report_runs_end_to_end(tmp_path):
    rows = [post_row(i, "2026-07-20", "Clove", "Image", 1000, likes=100)
            for i in range(4)]
    rows += [post_row(i + 10, "2026-06-10", "Clove", "Image", 1000, likes=10)
             for i in range(4)]
    report = social_report(write(tmp_path / "s.csv", rows), split_days=28)
    assert report["posts_analysed"] == 8
    assert report["findings"]


def test_multiline_captions_do_not_split_a_post_into_several(tmp_path):
    """Real exports carry captions containing newlines inside quotes; a naive
    line-based reader would report one post as many."""
    path = tmp_path / "s.csv"
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADERS)
        writer.writerow([1, "2026-06-17", "Clove", "https://x/1", "Image",
                         "line one\nline two\nline three", 0, 1000, 50, 0, 0, 0, 0])
    posts, _ = load_posts(path)
    assert len(posts) == 1
