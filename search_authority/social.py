"""Social post performance analysis.

Social data is shaped differently from advertising data: one row per post
rather than per campaign, no spend, and the meaningful measure is engagement
against reach rather than cost against conversions.

A single export usually covers several months, so periods are split by date
from one file rather than requiring two.

Reach is the denominator throughout. Raw likes reward a post that happened to
be pushed to more people; engagement rate measures whether the people who saw
it responded, which is the thing a content decision can act on.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median
from typing import Optional

ENGAGEMENT_FIELDS = ("likes", "comments", "shares", "saves")

COLUMNS: dict[str, tuple[str, ...]] = {
    "date": ("date posted", "date published", "date", "published"),
    "project": ("project name", "project", "brand", "account"),
    "url": ("url", "link", "permalink"),
    "type": ("type", "format", "media type", "post type"),
    "views": ("views", "plays", "impressions"),
    "reach": ("reach", "accounts reached"),
    "likes": ("likes", "reactions"),
    "shares": ("shares", "reposts"),
    "follows": ("follows", "new followers"),
    "comments": ("comments",),
    "saves": ("saves", "bookmarks"),
}

# Below this many posts a group's averages are noise, not signal.
MIN_GROUP = 3


def _column(headers: list[str], field: str) -> Optional[str]:
    lowered = {h.strip().lower(): h for h in headers}
    for alias in COLUMNS[field]:
        if alias in lowered:
            return lowered[alias]
    for alias in COLUMNS[field]:
        for low, original in lowered.items():
            if alias in low:
                return original
    return None


def _number(value) -> float:
    if value is None:
        return 0.0
    text = str(value).strip().replace(",", "").replace("%", "")
    if text in {"", "-", "--", "n/a", "N/A"}:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _parse_date(value) -> Optional[date]:
    text = str(value or "").strip()
    if not text:
        return None
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
                    "%d-%m-%Y", "%d %b %Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:len(pattern) + 6], pattern).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def load_posts(path: str | Path) -> tuple[list[dict], dict]:
    """Read a social export into normalised post records."""
    file = Path(path)
    if not file.exists():
        raise FileNotFoundError(f"No such export: {path}")

    with open(file, newline="", encoding="utf-8-sig") as handle:
        raw = list(csv.DictReader(handle))
    if not raw:
        return [], {"error": "empty file"}

    headers = list(raw[0].keys())
    mapping = {f: _column(headers, f) for f in COLUMNS}
    if not mapping["reach"] and not mapping["views"]:
        return [], {"error": "no reach or views column found", "headers": headers}

    posts = []
    for record in raw:
        reach = _number(record.get(mapping["reach"])) if mapping["reach"] else 0.0
        views = _number(record.get(mapping["views"])) if mapping["views"] else 0.0
        engagement = sum(
            _number(record.get(mapping[f])) for f in ENGAGEMENT_FIELDS if mapping[f]
        )
        denominator = reach or views
        posts.append({
            "date": _parse_date(record.get(mapping["date"])) if mapping["date"] else None,
            "project": (record.get(mapping["project"]) or "Unattributed").strip()
                       if mapping["project"] else "Unattributed",
            "type": (record.get(mapping["type"]) or "Unknown").strip()
                    if mapping["type"] else "Unknown",
            "url": (record.get(mapping["url"]) or "").strip() if mapping["url"] else "",
            "reach": reach,
            "views": views,
            "engagement": engagement,
            "follows": _number(record.get(mapping["follows"])) if mapping["follows"] else 0.0,
            "engagement_rate": round(engagement / denominator * 100, 2) if denominator else 0.0,
        })

    return posts, {"columns_used": mapping, "posts": len(posts)}


def _summarise(posts: list[dict]) -> dict:
    if not posts:
        return {"posts": 0}
    reach = sum(p["reach"] for p in posts)
    engagement = sum(p["engagement"] for p in posts)
    return {
        "posts": len(posts),
        "reach": round(reach),
        "engagement": round(engagement),
        "follows": round(sum(p["follows"] for p in posts)),
        # Rate over the pooled totals, not an average of per-post rates: the
        # latter lets a tiny post with a freak rate dominate.
        "engagement_rate": round(engagement / reach * 100, 2) if reach else 0.0,
        "median_reach": round(median(p["reach"] for p in posts)),
    }


def _group(posts: list[dict], key: str) -> dict:
    grouped = defaultdict(list)
    for post in posts:
        grouped[post[key]].append(post)
    return {name: _summarise(items) for name, items in sorted(grouped.items())}


def analyse(posts: list[dict], split_days: int = 28,
            today: Optional[date] = None) -> dict:
    """Compare the most recent window against the one before it."""
    dated = [p for p in posts if p["date"]]
    if not dated:
        return {"error": "no parseable dates; cannot split into periods"}

    latest = today or max(p["date"] for p in dated)
    cutoff = latest - timedelta(days=split_days)
    earlier_cutoff = cutoff - timedelta(days=split_days)

    current = [p for p in dated if p["date"] > cutoff]
    previous = [p for p in dated if earlier_cutoff < p["date"] <= cutoff]

    return {
        "window_days": split_days,
        "current_period": {"from": cutoff.isoformat(), "to": latest.isoformat(),
                           **_summarise(current)},
        "previous_period": {"from": earlier_cutoff.isoformat(), "to": cutoff.isoformat(),
                            **_summarise(previous)},
        "by_project": _group(posts, "project"),
        "by_type": _group(posts, "type"),
        "top_posts": sorted(posts, key=lambda p: -p["engagement_rate"])[:5],
        "weakest_posts": [
            p for p in sorted(posts, key=lambda p: p["engagement_rate"])[:5]
            if p["reach"] > 0
        ],
    }


def explain(analysis: dict) -> list[dict]:
    """Findings a content decision can act on."""
    if "error" in analysis:
        return [{"severity": "high", "headline": "Could not analyse",
                 "why": analysis["error"], "action": "Check the date column."}]

    findings: list[dict] = []
    current, previous = analysis["current_period"], analysis["previous_period"]

    if previous.get("posts") and current.get("posts"):
        for label, key in (("Engagement rate", "engagement_rate"),
                           ("Reach", "reach"), ("Posts published", "posts")):
            before, after = previous.get(key, 0), current.get(key, 0)
            if not before:
                continue
            change = round((after - before) / before * 100, 1)
            if abs(change) < 15:
                continue
            findings.append({
                "severity": "high" if change < 0 and key == "engagement_rate" else "info",
                "headline": f"{label} {'up' if change > 0 else 'down'} {abs(change)}% "
                            f"({before} to {after})",
                "why": f"Comparing the last {analysis['window_days']} days "
                       f"against the {analysis['window_days']} before.",
                "action": ("Review what changed in format or subject."
                           if change < 0 else "Identify what worked and repeat it."),
            })

    # Format comparison: which post types actually earn engagement.
    types = {k: v for k, v in analysis["by_type"].items() if v["posts"] >= MIN_GROUP}
    if len(types) > 1:
        ranked = sorted(types.items(), key=lambda kv: -kv[1]["engagement_rate"])
        best, worst = ranked[0], ranked[-1]
        if best[1]["engagement_rate"] > worst[1]["engagement_rate"] * 1.3:
            findings.append({
                "severity": "info",
                "headline": f"{best[0]} posts engage {best[1]['engagement_rate']}% "
                            f"against {worst[0]} at {worst[1]['engagement_rate']}%",
                "why": f"{best[1]['posts']} {best[0]} posts versus "
                       f"{worst[1]['posts']} {worst[0]}, measured against reach.",
                "action": f"Shift the mix toward {best[0]} and test why {worst[0]} lags.",
            })

    # Projects publishing without earning attention.
    projects = {k: v for k, v in analysis["by_project"].items() if v["posts"] >= MIN_GROUP}
    if len(projects) > 1:
        rates = [v["engagement_rate"] for v in projects.values()]
        typical = median(rates)
        for name, data in sorted(projects.items(), key=lambda kv: kv[1]["engagement_rate"]):
            if typical and data["engagement_rate"] < typical * 0.6:
                findings.append({
                    "severity": "high",
                    "headline": f"{name} engages at {data['engagement_rate']}% "
                                f"against a {round(typical, 2)}% median",
                    "why": f"{data['posts']} posts reaching {data['reach']:,} accounts "
                           f"produced {data['engagement']:,} interactions.",
                    "action": "Reach is being bought or earned but not converted into "
                              "interest. Review the creative and the caption hook.",
                })
                break

    if not findings:
        findings.append({
            "severity": "info",
            "headline": "No material change in social performance",
            "why": "Every tracked measure moved less than 15%.",
            "action": "No action needed.",
        })
    return findings


def social_report(path: str | Path, split_days: int = 28) -> dict:
    """The whole flow: one export in, analysis out."""
    posts, meta = load_posts(path)
    if not posts:
        return {"error": meta.get("error", "no posts parsed"), "meta": meta}
    analysis = analyse(posts, split_days=split_days)
    return {
        "columns_used": meta.get("columns_used"),
        "posts_analysed": len(posts),
        **analysis,
        "findings": explain(analysis),
    }
