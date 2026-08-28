#!/usr/bin/env python3
"""searchctl — County Group Search Authority CLI.

Usage:
    searchctl content-audit <path> [--output DIR] [--fixes] [--json] [--csv]
    searchctl audit-file <file> [--output DIR] [--fixes]
    searchctl roi-report <path> [--output DIR]
    searchctl ago-report <path> [--output DIR]
    searchctl version
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .content_auditor import audit_file, audit_text
from .report import (
    generate_markdown_report,
    generate_json_report,
    generate_csv_issues,
    generate_agency_handoff,
)
from .models import Owner


def cmd_content_audit(args):
    """Audit one or more content files."""
    path = Path(args.path)
    output_dir = Path(args.output) if args.output else None

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    analyses = []

    if path.is_file():
        files = [path]
    elif path.is_dir():
        files = sorted(
            list(path.glob("*.docx")) +
            list(path.glob("*.md")) +
            list(path.glob("*.txt")) +
            list(path.glob("*.html"))
        )
    else:
        print(f"Error: {path} not found", file=sys.stderr)
        return 1

    if not files:
        print(f"No content files found in {path}", file=sys.stderr)
        return 1

    for f in files:
        print(f"Auditing: {f.name}...")
        analysis = audit_file(str(f))
        analyses.append(analysis)

        # Print summary
        status = "PUBLISHABLE" if analysis.publishable else "NOT PUBLISHABLE"
        print(f"  Score: {analysis.score}/100 | {status} | {len(analysis.issues)} issues")

        # Individual report
        if output_dir:
            report = generate_markdown_report(analysis, include_fixes=args.fixes)
            report_path = output_dir / f"{f.stem}-audit.md"
            report_path.write_text(report)
            print(f"  Report: {report_path}")

            if args.json:
                json_path = output_dir / f"{f.stem}-audit.json"
                json_path.write_text(generate_json_report(analysis))

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY: {len(analyses)} files audited")
    total_issues = sum(len(a.issues) for a in analyses)
    publishable = sum(1 for a in analyses if a.publishable)
    print(f"Total issues: {total_issues}")
    print(f"Publishable: {publishable}/{len(analyses)}")

    # CSV export
    if output_dir and args.csv:
        csv_path = output_dir / "all-issues.csv"
        csv_path.write_text(generate_csv_issues(analyses))
        print(f"CSV: {csv_path}")

    return 0


def cmd_audit_file(args):
    """Audit a single file and print the report."""
    path = Path(args.file)
    if not path.exists():
        print(f"Error: {path} not found", file=sys.stderr)
        return 1

    analysis = audit_file(str(path))
    report = generate_markdown_report(analysis, include_fixes=args.fixes)
    print(report)

    if args.output:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / f"{path.stem}-audit.md"
        report_path.write_text(report)
        json_path = output_dir / f"{path.stem}-audit.json"
        json_path.write_text(generate_json_report(analysis))
        print(f"\nReports saved to {output_dir}/")

    return 0


def cmd_roi_report(args):
    """Generate ROI-specific action items report."""
    return _agency_report(args, Owner.ROI)


def cmd_ago_report(args):
    """Generate AGO-specific action items report."""
    return _agency_report(args, Owner.AGO)


def _agency_report(args, agency: Owner):
    path = Path(args.path)
    output_dir = Path(args.output) if args.output else Path(".")

    if path.is_file():
        files = [path]
    elif path.is_dir():
        files = sorted(
            list(path.glob("*.docx")) + list(path.glob("*.md")) +
            list(path.glob("*.txt")) + list(path.glob("*.html"))
        )
    else:
        print(f"Error: {path} not found", file=sys.stderr)
        return 1

    analyses = [audit_file(str(f)) for f in files]
    report = generate_agency_handoff(analyses, agency)

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"{agency.value.lower()}-action-items.md"
    report_path.write_text(report)
    print(report)
    print(f"\nSaved to {report_path}")
    return 0


def cmd_pipeline(args):
    """Run the full pipeline: audit → schema → package."""
    from .pipeline import run_pipeline

    path = Path(args.path)
    if not path.exists():
        print(f"Error: {path} not found", file=sys.stderr)
        return 1

    slug = args.slug or path.stem
    result = run_pipeline(
        input_path=str(path),
        slug=slug,
        output_dir=args.output,
        url_base=args.url_base,
    )

    status = "PUBLISHABLE" if result["publishable"] else "NOT PUBLISHABLE"
    print(f"\nPipeline complete: {status}")
    print(f"Score: {result['score']}/100 | Issues: {result['issue_count']} ({result['critical_count']} critical)")
    print(f"\nGates:")
    for gate, val in result["gates"].items():
        print(f"  {gate}: {val}")
    print(f"\nOutput files:")
    for label, fpath in result["output_files"].items():
        print(f"  {label}: {fpath}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="searchctl",
        description="County Group Search Authority Engine",
    )
    subparsers = parser.add_subparsers(dest="command")

    # content-audit
    p_audit = subparsers.add_parser("content-audit", help="Audit content files")
    p_audit.add_argument("path", help="File or directory to audit")
    p_audit.add_argument("--output", "-o", help="Output directory for reports")
    p_audit.add_argument("--fixes", action="store_true", help="Include fix recommendations")
    p_audit.add_argument("--json", action="store_true", help="Also output JSON reports")
    p_audit.add_argument("--csv", action="store_true", help="Also output CSV of all issues")

    # audit-file
    p_file = subparsers.add_parser("audit-file", help="Audit a single file")
    p_file.add_argument("file", help="File to audit")
    p_file.add_argument("--output", "-o", help="Output directory")
    p_file.add_argument("--fixes", action="store_true", default=True, help="Include fixes")

    # roi-report
    p_roi = subparsers.add_parser("roi-report", help="Generate ROI action items")
    p_roi.add_argument("path", help="File or directory")
    p_roi.add_argument("--output", "-o", default=".", help="Output directory")

    # ago-report
    p_ago = subparsers.add_parser("ago-report", help="Generate AGO action items")
    p_ago.add_argument("path", help="File or directory")
    p_ago.add_argument("--output", "-o", default=".", help="Output directory")

    # pipeline
    p_pipe = subparsers.add_parser("pipeline", help="Run full audit → schema → package pipeline")
    p_pipe.add_argument("path", help="File to run through the pipeline")
    p_pipe.add_argument("--output", "-o", default="output", help="Output directory")
    p_pipe.add_argument("--slug", help="URL slug (default: derived from filename)")
    p_pipe.add_argument("--url-base", default="https://countygroup.in/blog", help="Base URL for schema")

    # version
    subparsers.add_parser("version", help="Show version")

    args = parser.parse_args()

    if args.command == "content-audit":
        return cmd_content_audit(args)
    elif args.command == "audit-file":
        return cmd_audit_file(args)
    elif args.command == "roi-report":
        return cmd_roi_report(args)
    elif args.command == "ago-report":
        return cmd_ago_report(args)
    elif args.command == "pipeline":
        return cmd_pipeline(args)
    elif args.command == "version":
        from . import __version__
        print(f"searchctl v{__version__}")
        return 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
