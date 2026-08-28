"""Batch processor: audit all local blog files from BLOG_INVENTORY.yaml."""

import json
import sys
from pathlib import Path

import yaml

from .pipeline import run_pipeline

INVENTORY_PATH = Path("blogs/BLOG_INVENTORY.yaml")
ROI_OUTPUT = Path("audit-reports/roi")
OLD_AGENCY_OUTPUT = Path("audit-reports/old-agency")
URL_BASE = "https://www.countygroup.in/blog"


def load_inventory(path: Path = INVENTORY_PATH) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def save_inventory(data: dict, path: Path = INVENTORY_PATH) -> None:
    path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _slug_from_path(p: Path) -> str:
    import re
    s = p.stem.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return s[:60].strip("-")


def process_batch(mode: str = "all", force: bool = False) -> dict:
    """Run pipeline on all local files.

    Args:
        mode: 'all', 'roi', or 'old-agency'
        force: re-audit already-audited files

    Returns:
        Summary dict with results per blog.
    """
    inv = load_inventory()
    results = []

    if mode in ("all", "roi"):
        for item in inv.get("already_processed", []):
            local = item.get("local_file")
            if not local or not Path(local).exists():
                continue
            if item.get("status") == "audited" and not force:
                results.append({"slug": Path(local).stem, "skipped": True, "score": item.get("score")})
                continue
            slug = Path(local).stem
            try:
                r = run_pipeline(input_path=local, slug=slug, output_dir=str(ROI_OUTPUT), url_base=URL_BASE)
                item["status"] = "audited"
                item["score"] = r["score"]
                item["issues"] = r["issue_count"]
                item["critical"] = r["critical_count"]
                item["publishable"] = r["publishable"]
                results.append(r)
                print(f"  [ROI] {slug}: {r['score']}/100 ({r['issue_count']} issues)")
            except Exception as e:
                results.append({"slug": slug, "error": str(e)})
                print(f"  [ROI] {slug}: ERROR — {e}")

        for item in inv.get("roi_google_docs", []):
            local = item.get("local_file")
            if not local or not Path(local).exists():
                continue
            if item.get("status") == "audited" and not force:
                results.append({"slug": Path(local).stem, "skipped": True, "score": item.get("score")})
                continue
            slug = Path(local).stem
            try:
                r = run_pipeline(input_path=local, slug=slug, output_dir=str(ROI_OUTPUT), url_base=URL_BASE)
                item["status"] = "audited"
                item["score"] = r["score"]
                item["issues"] = r["issue_count"]
                item["critical"] = r["critical_count"]
                item["publishable"] = r["publishable"]
                results.append(r)
                print(f"  [ROI-GD] {slug}: {r['score']}/100 ({r['issue_count']} issues)")
            except Exception as e:
                results.append({"slug": slug, "error": str(e)})
                print(f"  [ROI-GD] {slug}: ERROR — {e}")

    if mode in ("all", "old-agency"):
        for item in inv.get("old_agency_local", []):
            local = item.get("file")
            if not local or not Path(local).exists():
                continue
            if item.get("status") == "audited" and not force:
                results.append({"slug": _slug_from_path(Path(local)), "skipped": True, "score": item.get("score")})
                continue
            slug = _slug_from_path(Path(local))
            try:
                r = run_pipeline(input_path=local, slug=slug, output_dir=str(OLD_AGENCY_OUTPUT), url_base=URL_BASE)
                item["status"] = "audited"
                item["score"] = r["score"]
                item["issues"] = r["issue_count"]
                item["critical"] = r["critical_count"]
                item["publishable"] = r["publishable"]
                results.append(r)
                print(f"  [OLD] {slug}: {r['score']}/100 ({r['issue_count']} issues)")
            except Exception as e:
                results.append({"slug": slug, "error": str(e)})
                print(f"  [OLD] {slug}: ERROR — {e}")

    save_inventory(inv)

    summary = {
        "total": len(results),
        "audited": sum(1 for r in results if not r.get("skipped") and not r.get("error")),
        "skipped": sum(1 for r in results if r.get("skipped")),
        "errors": sum(1 for r in results if r.get("error")),
        "publishable": sum(1 for r in results if r.get("publishable")),
        "avg_score": round(
            sum(r.get("score", 0) for r in results if r.get("score") is not None)
            / max(1, sum(1 for r in results if r.get("score") is not None)),
            1,
        ),
        "results": results,
    }

    summary_path = Path("audit-reports") / "batch-summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"\nBatch complete: {summary['audited']} audited, {summary['skipped']} skipped, {summary['errors']} errors")
    print(f"Average score: {summary['avg_score']}/100 | Publishable: {summary['publishable']}/{summary['total']}")

    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Batch audit blogs from inventory")
    parser.add_argument("--mode", choices=["all", "roi", "old-agency"], default="all")
    parser.add_argument("--force", action="store_true", help="Re-audit already-audited files")
    args = parser.parse_args()
    process_batch(mode=args.mode, force=args.force)
