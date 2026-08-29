"""Agentic automation for the County Group Blog Authority System.

Watches for new blog docs, auto-audits them, monitors content decay,
tracks competitor activity, and verifies AI citations. Runs on free APIs:
- Anthropic API (Haiku) for AI analysis
- Google Search Console API for decay detection
- Google PageSpeed Insights API for Core Web Vitals
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import yaml

from .batch import load_inventory, save_inventory, ROI_OUTPUT
from .pipeline import run_pipeline
from .truth_layer import registry_report
from .dashboard import build as build_dashboard
from .history import summary as history_summary
from .hygiene import run as run_hygiene
from .reports import weekly_report
from .social import social_report

AGENT_LOG = Path("agent-logs")
CONFIG_PATH = Path("agent-config.yaml")
CONFIG_EXAMPLE_PATH = Path("agent-config.example.yaml")
URL_BASE = "https://www.countygroup.in/blog"


def _load_config() -> dict:
    for path in (CONFIG_PATH, CONFIG_EXAMPLE_PATH):
        if path.exists():
            return yaml.safe_load(path.read_text()) or {}
    return {}


def _log(action: str, data: dict):
    AGENT_LOG.mkdir(parents=True, exist_ok=True)
    entry = {"timestamp": datetime.now().isoformat(), "action": action, **data}
    log_file = AGENT_LOG / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
    with open(log_file, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")
    print(f"[{entry['timestamp'][:19]}] {action}: {json.dumps(data, default=str)[:200]}")


# --- Task 1: Auto-audit new files ---

def watch_and_audit(directory: str = "blogs/roi-incoming", force: bool = False) -> dict:
    """Scan a directory for new/changed blog files and audit them.

    This is the core loop: ROI drops a file → agent audits → generates reports.
    """
    scan_dir = Path(directory)
    if not scan_dir.exists():
        return {"error": f"Directory {directory} does not exist"}

    inv = load_inventory()
    all_entries = (
        inv.get("already_processed", [])
        + inv.get("roi_google_docs", [])
    )
    known_files = {e.get("local_file") for e in all_entries if e.get("local_file")}

    results = []
    new_files = []

    for f in sorted(scan_dir.glob("*.md")):
        rel = str(f)
        if rel not in known_files:
            new_files.append(rel)

    if not new_files and not force:
        _log("watch_scan", {"new_files": 0, "directory": directory})
        return {"new_files": 0, "message": "No new files found"}

    for fpath in new_files:
        slug = Path(fpath).stem
        try:
            r = run_pipeline(
                input_path=fpath, slug=slug,
                output_dir=str(ROI_OUTPUT), url_base=URL_BASE,
            )
            entry = {
                "title": slug.replace("-", " ").title(),
                "local_file": fpath,
                "status": "audited",
                "score": r["score"],
                "issues": r["issue_count"],
                "critical": r["critical_count"],
                "publishable": r["publishable"],
                "added_by": "agent",
                "added_at": datetime.now().isoformat(),
            }
            inv.setdefault("roi_google_docs", []).append(entry)
            results.append({"file": fpath, "score": r["score"], "publishable": r["publishable"]})
            _log("auto_audit", {"file": fpath, "score": r["score"], "issues": r["issue_count"]})
        except Exception as e:
            results.append({"file": fpath, "error": str(e)})
            _log("auto_audit_error", {"file": fpath, "error": str(e)})

    save_inventory(inv)
    summary = {
        "new_files": len(new_files),
        "audited": len([r for r in results if "score" in r]),
        "errors": len([r for r in results if "error" in r]),
        "results": results,
    }
    _log("watch_complete", summary)
    return summary


# --- Task 2: Content decay detection ---

def _find_column(headers: list[str], candidates: list[str]) -> Optional[str]:
    """First header matching any candidate, compared case-insensitively."""
    lowered = {h.strip().lower(): h for h in headers}
    for want in candidates:
        if want in lowered:
            return lowered[want]
    for want in candidates:
        for low, original in lowered.items():
            if want in low:
                return original
    return None


def _find_comparison_columns(headers: list[str]) -> tuple[Optional[str], Optional[str]]:
    """Locate the current and previous impression columns.

    Search Console names these by the chosen range — "Impressions Last 28
    days" and "Impressions Previous 28 days" — so they cannot be hardcoded.
    Falls back to explicit impressions/prev_impressions columns.
    """
    impression_cols = [h for h in headers if "impression" in h.strip().lower()]

    current = previous = None
    for header in impression_cols:
        low = header.strip().lower()
        if "previous" in low or low.startswith("prev"):
            previous = header
        elif "last" in low or "current" in low:
            current = header

    if not current:
        plain = [h for h in impression_cols if h != previous]
        current = plain[0] if plain else None

    return current, previous


def check_content_decay(gsc_export_path: str) -> dict:
    """Detect blogs losing impressions using a Google Search Console CSV export.

    GSC export columns: page, clicks, impressions, ctr, position
    Compare last 28 days vs previous 28 days.

    Args:
        gsc_export_path: Path to a GSC performance CSV (exported manually or via API).
    """
    import csv

    path = Path(gsc_export_path)
    if not path.exists():
        return {"error": f"File not found: {gsc_export_path}"}

    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        return {"error": "Empty CSV file"}

    headers = list(rows[0].keys())
    page_col = _find_column(headers, ["top pages", "page", "url", "landing page"])
    current_col, previous_col = _find_comparison_columns(headers)

    if not page_col:
        return {"error": f"No page column found. Headers: {headers}"}
    if not (current_col and previous_col):
        return {
            "error": "No comparison columns found. Export from Search Console "
                     "with date comparison enabled (Last 28 days vs Previous "
                     "period), which produces 'Impressions Last 28 days' and "
                     "'Impressions Previous 28 days'.",
            "headers_seen": headers,
        }

    decaying, skipped = [], 0
    for row in rows:
        try:
            current = float(str(row.get(current_col, "") or 0).replace(",", ""))
            previous = float(str(row.get(previous_col, "") or 0).replace(",", ""))
        except ValueError:
            skipped += 1
            continue

        if previous <= 0:
            continue
        change = (current - previous) / previous
        if change <= -0.20:
            decaying.append({
                "page": row.get(page_col, ""),
                "impressions": current,
                "prev_impressions": previous,
                "change_pct": round(change * 100, 1),
            })

    result = {
        "total_pages": len(rows),
        "decaying": len(decaying),
        "skipped_unparseable": skipped,
        "decay_threshold": "-20%",
        "columns_used": {"page": page_col, "current": current_col, "previous": previous_col},
        "pages": sorted(decaying, key=lambda x: x["change_pct"]),
    }

    _log("content_decay", {"total": len(rows), "decaying": len(decaying)})

    if decaying:
        report_path = AGENT_LOG / f"decay-report-{datetime.now().strftime('%Y-%m-%d')}.json"
        report_path.write_text(json.dumps(result, indent=2))

    return result


# --- Task 3: Inventory health report ---

def generate_health_report() -> dict:
    """Generate a comprehensive health report from the current inventory."""
    inv = load_inventory()
    all_entries = []

    for section in ["already_processed", "roi_google_docs", "old_agency_local"]:
        for item in inv.get(section, []):
            score = item.get("score")
            if score is not None:
                all_entries.append({
                    "title": item.get("title", item.get("file", "unknown")),
                    "score": score,
                    "issues": item.get("issues", 0),
                    "critical": item.get("critical", 0),
                    "publishable": item.get("publishable", False),
                    "status": item.get("status", "unknown"),
                    "source": section,
                })

    if not all_entries:
        return {"error": "No audited entries found"}

    scores = [e["score"] for e in all_entries]
    publishable = [e for e in all_entries if e["publishable"]]
    critical_blogs = [e for e in all_entries if e["critical"] > 0]

    report = {
        "generated_at": datetime.now().isoformat(),
        "total_docs": len(all_entries),
        "audited": len([e for e in all_entries if e["status"] == "audited"]),
        "publishable": len(publishable),
        "publishable_pct": round(len(publishable) / len(all_entries) * 100, 1),
        "avg_score": round(sum(scores) / len(scores), 1),
        "min_score": min(scores),
        "max_score": max(scores),
        "median_score": sorted(scores)[len(scores) // 2],
        "critical_blogs": len(critical_blogs),
        "score_distribution": {
            "90_100": len([s for s in scores if s >= 90]),
            "80_89": len([s for s in scores if 80 <= s < 90]),
            "70_79": len([s for s in scores if 70 <= s < 80]),
            "60_69": len([s for s in scores if 60 <= s < 70]),
            "below_60": len([s for s in scores if s < 60]),
        },
        "top_5": sorted(all_entries, key=lambda x: x["score"], reverse=True)[:5],
        "bottom_5": sorted(all_entries, key=lambda x: x["score"])[:5],
    }

    report_path = AGENT_LOG / f"health-report-{datetime.now().strftime('%Y-%m-%d')}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, default=str))

    _log("health_report", {
        "total": report["total_docs"],
        "publishable": report["publishable"],
        "avg_score": report["avg_score"],
    })
    return report


# --- Task 4: AI citation check ---

def check_truth_layer() -> dict:
    """Report which registry facts are stale or too incomplete to enforce.

    Stale = past its refresh_days TTL, so nobody has re-verified it recently.
    Incomplete = missing status, source, or last_verified.
    """
    report = registry_report()
    _log("truth_layer", {
        "claims": report["total_claims"],
        "stale": report["stale_count"],
        "incomplete": report["incomplete_count"],
    })
    return report


def check_links(urls: Optional[list[str]] = None, timeout: int = 15) -> dict:
    """Check that County URLs actually resolve.

    The audit itself is offline and deterministic, so it can only say a URL is
    unlisted. This does the network half: fetches each URL and reports its
    status, following redirects so a 301 to the canonical page is visible.

    With no `urls`, checks everything in county_context/site_urls.yaml.
    """
    import urllib.error
    import urllib.request

    from .truth_layer import raw_site_urls

    if urls is None:
        urls = raw_site_urls()

    results = []
    for url in urls:
        entry = {"url": url}
        try:
            req = urllib.request.Request(
                url,
                method="GET",
                headers={"User-Agent": "CountyGroup-LinkCheck/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                entry["status"] = resp.status
                final = resp.geturl()
                entry["ok"] = 200 <= resp.status < 300
                if final.rstrip("/") != url.rstrip("/"):
                    entry["redirected_to"] = final
        except urllib.error.HTTPError as exc:
            entry.update({"status": exc.code, "ok": False})
        except Exception as exc:  # DNS, TLS, timeout
            entry.update({"status": None, "ok": False, "error": str(exc)[:120]})
        results.append(entry)

    broken = [r for r in results if not r.get("ok")]
    redirects = [r for r in results if r.get("redirected_to")]

    summary = {
        "checked": len(results),
        "ok": len(results) - len(broken),
        "broken": len(broken),
        "redirected": len(redirects),
        "results": results,
    }

    AGENT_LOG.mkdir(parents=True, exist_ok=True)
    (AGENT_LOG / f"link-check-{datetime.now().strftime('%Y-%m-%d')}.json").write_text(
        json.dumps(summary, indent=2)
    )
    _log("link_check", {"checked": len(results), "broken": len(broken)})
    return summary


def check_cannibalization() -> dict:
    """Find pages competing for the same search terms across the corpus."""
    from .cannibalization import analyse_corpus

    inv = load_inventory()
    entries = []
    for section in ("already_processed", "roi_google_docs", "old_agency_local"):
        entries.extend(inv.get(section) or [])

    report = analyse_corpus(entries)
    AGENT_LOG.mkdir(parents=True, exist_ok=True)
    (AGENT_LOG / f"cannibalization-{datetime.now().strftime('%Y-%m-%d')}.json").write_text(
        json.dumps(report, indent=2)
    )
    _log("cannibalization", {
        "pages": report["pages_analysed"],
        "collisions": report["collisions"],
        "high": report["by_severity"]["high"],
    })
    return report


def check_ai_citations(queries: list[str]) -> dict:
    """Log target queries for AI citation tracking.

    Run this quarterly. Manually check each query on ChatGPT, Perplexity,
    Google AI Overview — then record whether County Group was cited.

    Returns a tracking template for manual verification.
    """
    template = {
        "check_date": datetime.now().isoformat()[:10],
        "queries": [],
    }

    for q in queries:
        template["queries"].append({
            "query": q,
            "chatgpt_cited": None,
            "perplexity_cited": None,
            "google_ai_overview_cited": None,
            "notes": "",
        })

    path = AGENT_LOG / f"citation-check-{datetime.now().strftime('%Y-%m-%d')}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(template, indent=2))

    _log("citation_check_template", {"queries": len(queries)})
    return template


DEFAULT_CITATION_QUERIES = [
    "best luxury flats in Noida",
    "flats in Sector 151 Noida",
    "3 BHK Greater Noida West",
    "Noida Expressway apartments",
    "premium flats Gurugram Sector 88A",
    "County Group reviews",
    "Clove County Noida",
    "Coco County Greater Noida West",
    "Ivory County Noida Expressway",
    "Center Court Gurugram",
    "Jade County Sector 151",
    "Courtyard Noida",
    "RERA registered flats Noida",
    "luxury apartments near Noida airport",
    "County Group developer projects",
]


# --- Task 5: Refresh brief generator ---

def generate_refresh_brief(file_path: str) -> dict:
    """Generate a refresh brief for a blog that needs updating.

    Reads the audit report and creates a concise brief for ROI
    with exactly what needs to change.
    """
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    result = run_pipeline(input_path=file_path, output_dir=str(AGENT_LOG / "refresh"))

    brief = {
        "file": file_path,
        "current_score": result["score"],
        "publishable": result["publishable"],
        "gate_status": result["gates"],
        "total_issues": result["issue_count"],
        "critical_issues": result["critical_count"],
        "action_items": [],
    }

    report_path = AGENT_LOG / "refresh" / f"{Path(file_path).stem}-audit-report.json"
    if report_path.exists():
        report_data = json.loads(report_path.read_text())
        # Every actionable issue, worst first. Filtering to critical/high left
        # briefs empty for documents whose problems were all medium — which
        # read as "nothing to do" next to a non-zero issue count.
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        actionable = [
            i for i in report_data.get("issues", [])
            if i.get("severity") in order
        ]
        actionable.sort(key=lambda i: order.get(i.get("severity"), 9))

        for issue in actionable:
            brief["action_items"].append({
                "severity": issue["severity"],
                "summary": issue["summary"],
                "action": issue.get("recommended_action", ""),
                "test": issue.get("acceptance_test", ""),
                "owner": issue.get("owner", "ROI"),
                "quoted_text": (issue.get("claim") or "")[:160],
            })

        brief["blocking_gates"] = [
            name for name, status in result["gates"].items() if status == "FAIL"
        ]

    brief_path = AGENT_LOG / f"refresh-brief-{Path(file_path).stem}.json"
    brief_path.write_text(json.dumps(brief, indent=2))

    _log("refresh_brief", {"file": file_path, "score": result["score"], "actions": len(brief["action_items"])})
    return brief


# --- Task 6: Competitor content monitor ---

def log_competitor_content(competitor: str, url: str, title: str, topic: str) -> dict:
    """Log a competitor blog post for tracking.

    Run monthly. When checking competitor blogs, log new posts here
    to track their content velocity and topic coverage.
    """
    log_path = AGENT_LOG / "competitor-tracker.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "date": datetime.now().isoformat()[:10],
        "competitor": competitor,
        "url": url,
        "title": title,
        "topic": topic,
        "in_our_cluster": False,
        "responded": False,
    }

    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")

    _log("competitor_content", {"competitor": competitor, "title": title})
    return entry


def get_competitor_summary() -> dict:
    """Summarize tracked competitor content."""
    log_path = AGENT_LOG / "competitor-tracker.jsonl"
    if not log_path.exists():
        return {"total": 0, "competitors": {}}

    entries = []
    for line in log_path.read_text().strip().split("\n"):
        if line.strip():
            entries.append(json.loads(line))

    by_competitor = {}
    for e in entries:
        name = e["competitor"]
        by_competitor.setdefault(name, []).append(e)

    return {
        "total": len(entries),
        "competitors": {
            name: {"count": len(posts), "latest": posts[-1]["title"]}
            for name, posts in by_competitor.items()
        },
    }


# --- Task 7: PageSpeed check ---

def check_pagespeed(urls: list[str]) -> dict:
    """Check Core Web Vitals using the free Google PageSpeed Insights API.

    No API key needed for basic usage (limited rate).
    """
    try:
        import urllib.request
        import urllib.parse
    except ImportError:
        return {"error": "urllib not available"}

    results = []
    for url in urls:
        api_url = (
            "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?"
            + urllib.parse.urlencode({"url": url, "strategy": "mobile"})
        )
        try:
            with urllib.request.urlopen(api_url, timeout=30) as resp:
                data = json.loads(resp.read())

            lh = data.get("lighthouseResult", {})
            categories = lh.get("categories", {})
            perf_score = categories.get("performance", {}).get("score")

            audits = lh.get("audits", {})
            lcp = audits.get("largest-contentful-paint", {}).get("numericValue")
            cls = audits.get("cumulative-layout-shift", {}).get("numericValue")
            inp = audits.get("interaction-to-next-paint", {}).get("numericValue")

            results.append({
                "url": url,
                "performance_score": round(perf_score * 100) if perf_score else None,
                "lcp_ms": round(lcp) if lcp else None,
                "cls": round(cls, 3) if cls is not None else None,
                "inp_ms": round(inp) if inp else None,
            })
        except Exception as e:
            results.append({"url": url, "error": str(e)})

    summary = {
        "checked": len(urls),
        "results": results,
        "timestamp": datetime.now().isoformat(),
    }

    _log("pagespeed", {"checked": len(urls), "errors": len([r for r in results if "error" in r])})
    return summary


# --- CLI ---

def main():
    """CLI for the agent system."""
    import argparse

    parser = argparse.ArgumentParser(
        description="County Group Blog Authority Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  watch         Scan for new blog files and auto-audit them
  health        Generate inventory health report
  decay         Check content decay from GSC export
  citations     Generate AI citation tracking template
  refresh       Generate refresh brief for a specific blog
  pagespeed     Check Core Web Vitals for blog URLs
  competitors   Show competitor content summary
  truth         Report stale/incomplete claims in the truth layer
  links         Check that County URLs actually resolve
  cannibals     Find pages competing for the same search terms
  hygiene       Check live pages against the registry
  report        Weekly analysis: --prev A.csv --curr B.csv [--leads L.csv]
  social        Social post analysis: --file export.csv
  history       Repeat mistakes and score trends across all audits
  dashboard     Build the HTML dashboard from current audit data
        """,
    )
    parser.add_argument("command", choices=[
        "watch", "health", "decay", "citations", "refresh", "pagespeed",
        "competitors", "truth", "links", "cannibals", "dashboard", "hygiene",
        "report", "social", "history",
    ])
    parser.add_argument("--dir", default="blogs/roi-incoming", help="Directory to watch (for 'watch')")
    parser.add_argument("--file", help="File path (for 'refresh')")
    parser.add_argument("--gsc", help="GSC export CSV path (for 'decay')")
    parser.add_argument("--urls", nargs="+", help="URLs (for 'pagespeed')")
    parser.add_argument("--prev", help="Previous period export (for 'report')")
    parser.add_argument("--curr", help="Current period export (for 'report')")
    parser.add_argument("--leads", help="Lead status export (for 'report')")
    parser.add_argument("--force", action="store_true")

    args = parser.parse_args()

    if args.command == "watch":
        result = watch_and_audit(directory=args.dir, force=args.force)
    elif args.command == "health":
        result = generate_health_report()
    elif args.command == "decay":
        if not args.gsc:
            print("Error: --gsc required for decay check")
            sys.exit(1)
        result = check_content_decay(args.gsc)
    elif args.command == "citations":
        result = check_ai_citations(DEFAULT_CITATION_QUERIES)
    elif args.command == "refresh":
        if not args.file:
            print("Error: --file required for refresh brief")
            sys.exit(1)
        result = generate_refresh_brief(args.file)
    elif args.command == "pagespeed":
        if not args.urls:
            print("Error: --urls required for pagespeed check")
            sys.exit(1)
        result = check_pagespeed(args.urls)
    elif args.command == "competitors":
        result = get_competitor_summary()
    elif args.command == "truth":
        result = check_truth_layer()
    elif args.command == "links":
        result = check_links(urls=args.urls)
    elif args.command == "cannibals":
        result = check_cannibalization()
    elif args.command == "report":
        if not (args.prev and args.curr):
            print("Error: --prev and --curr are required for report")
            sys.exit(1)
        result = weekly_report(args.prev, args.curr, args.leads)
        _log("weekly_report", {"findings": len(result.get("findings", []))})
    elif args.command == "history":
        result = history_summary()
        _log("history", {"runs": result.get("runs", 0),
                         "regressions": len(result.get("regressions", []))})
    elif args.command == "social":
        if not args.file:
            print("Error: --file is required for social")
            sys.exit(1)
        result = social_report(args.file)
        _log("social_report", {"posts": result.get("posts_analysed", 0)})
    elif args.command == "hygiene":
        result = run_hygiene(urls=args.urls)
        _log("hygiene", {"pages": result["pages_checked"],
                         "findings": result["total_findings"]})
    elif args.command == "dashboard":
        result = build_dashboard()
        _log("dashboard", result)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
