"""Week-over-week performance analysis across ad and search platforms.

Takes two exports — last period and this one — normalises whatever column
names the platform used, and explains what moved and why.

The "why" is arithmetic, not opinion. Leads are impressions x CTR x CVR, so
a drop in leads decomposes into exactly which of those three fell. That is
the difference between "leads are down 30%" and "leads are down 30% because
CTR fell while impressions and conversion rate held, so the creative stopped
working" — the second is something a person can act on.

Lead quality is joined separately when supplied, because spend efficiency
measured against raw leads is misleading: buying more cheap unqualified
leads looks like success on CPL and is not.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

# Column aliases per platform. Meta, Google Ads, GA4 and Search Console all
# name the same quantity differently, and each changes its export headers
# between versions, so matching is by substring rather than exact name.
ALIASES: dict[str, tuple[str, ...]] = {
    "campaign": ("campaign name", "campaign", "ad set name", "ad group",
                 "top pages", "page", "landing page", "query", "source / medium"),
    "impressions": ("impressions", "impression", "impr.", "reach"),
    "clicks": ("clicks", "link clicks", "sessions"),
    # "Spent" is what the County weekly sheet uses; it does not contain
    # "spend", so substring matching alone would miss it.
    "spend": ("amount spent", "spent", "spend", "cost", "amount"),
    "leads": ("leads", "conversions", "results", "conversion", "form submissions"),
    # Names what the conversion column actually counts. Reach, page likes and
    # post engagements are not comparable quantities, so summing a column that
    # mixes them produces a meaningless total.
    "conversion_metric": ("conversion metric", "result type", "metric"),
    "platform": ("platform", "channel", "source"),
}

# Derived metrics: (name, numerator, denominator, multiplier).
# Kept declarative so a new ratio is one line, not a new branch.
DERIVED: tuple[tuple[str, str, str, float], ...] = (
    ("ctr", "clicks", "impressions", 100.0),
    ("cpc", "spend", "clicks", 1.0),
    ("cvr", "leads", "clicks", 100.0),
    ("cpl", "spend", "leads", 1.0),
    ("cpm", "spend", "impressions", 1000.0),
)

# Metrics where a rise is bad news.
LOWER_IS_BETTER = {"cpc", "cpl", "cpm"}

MATERIAL_CHANGE = 0.10   # ignore movement under 10% as noise
BIG_CHANGE = 0.25


@dataclass
class Row:
    """One campaign, page, or query in a period."""
    name: str
    metrics: dict[str, float] = field(default_factory=dict)
    platform: Optional[str] = None

    def derive(self) -> None:
        for key, num, den, mult in DERIVED:
            n, d = self.metrics.get(num), self.metrics.get(den)
            if n is not None and d:
                self.metrics[key] = round(n / d * mult, 2)


def _number(value: str) -> Optional[float]:
    """Parse a spreadsheet cell. Handles '1,234', '₹1,234.50', '12%', '--'."""
    if value is None:
        return None
    text = str(value).strip().replace(",", "").replace("₹", "").replace("%", "")
    text = text.replace("Rs.", "").replace("Rs", "").strip()
    if text in {"", "-", "--", "n/a", "N/A", "—"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _match_column(headers: Iterable[str], field_name: str) -> Optional[str]:
    lowered = {h.strip().lower(): h for h in headers}
    for alias in ALIASES[field_name]:
        if alias in lowered:
            return lowered[alias]
    for alias in ALIASES[field_name]:
        for low, original in lowered.items():
            if alias in low:
                return original
    return None


def _find_header_row(rows: list[list[str]], limit: int = 10) -> Optional[int]:
    """Index of the row that looks like column headers.

    Matches the first row containing a campaign/page-like column name, so a
    title or date banner above the table does not become the header.
    """
    for index, row in enumerate(rows[:limit]):
        cells = [c.strip().lower() for c in row if c and c.strip()]
        if len(cells) < 2:
            continue
        if any(any(alias in cell for alias in ALIASES["campaign"]) for cell in cells):
            return index
    return None


def load_rows(path: str | Path) -> tuple[list[Row], dict]:
    """Read an export into normalised rows.

    Returns (rows, mapping) so the caller can show which columns were used —
    silent mis-mapping is the failure mode that produces confident nonsense.
    """
    file = Path(path)
    if not file.exists():
        raise FileNotFoundError(f"No such export: {path}")

    with open(file, newline="", encoding="utf-8-sig") as handle:
        rows_raw = list(csv.reader(handle))
    if not rows_raw:
        return [], {"error": "empty file"}

    # Exported sheets often open with a title row ("County Group 17 Aug - 23
    # Aug 2026") before the real headers, so the first line is not reliably
    # the header. Take the first row that names a campaign-like column.
    header_index = _find_header_row(rows_raw)
    if header_index is None:
        return [], {"error": "no header row found",
                    "first_rows": [r[:4] for r in rows_raw[:4]]}

    headers = [h.strip() for h in rows_raw[header_index]]
    raw = [
        {headers[i]: (row[i] if i < len(row) else "") for i in range(len(headers))}
        for row in rows_raw[header_index + 1:]
    ]
    if not raw:
        return [], {"error": "header row found but no data rows"}
    mapping = {f: _match_column(headers, f) for f in ALIASES}
    if not mapping["campaign"]:
        return [], {"error": "no campaign/page column found", "headers": headers}

    rows: list[Row] = []
    metrics_seen: set[str] = set()
    platform = None
    for record in raw:
        # Grouped sheets fill the platform cell only on the first row of a
        # block, leaving the rest blank; carry it down.
        if mapping.get("platform"):
            cell = (record.get(mapping["platform"]) or "").strip()
            if cell:
                platform = cell

        name = (record.get(mapping["campaign"]) or "").strip()
        lowered = name.lower()
        # Totals appear mid-sheet as well as at the end.
        if not name or lowered.startswith(("total", "grand total", "—", "-")) \
                or "total (" in lowered:
            continue

        if mapping.get("conversion_metric"):
            metric = (record.get(mapping["conversion_metric"]) or "").strip()
            if metric and metric != "-":
                metrics_seen.add(metric)

        row = Row(name=name)
        if platform:
            row.platform = platform
        for field_name in ("impressions", "clicks", "spend", "leads"):
            column = mapping[field_name]
            if column:
                value = _number(record.get(column))
                if value is not None:
                    row.metrics[field_name] = value
        row.derive()
        rows.append(row)

    meta = {"columns_used": mapping, "rows": len(rows),
            "header_row": header_index + 1}
    if len(metrics_seen) > 1:
        # Reach, page likes and post engagements are different quantities.
        # Adding them would produce a confident, meaningless total.
        meta["mixed_conversion_metrics"] = sorted(metrics_seen)
    return rows, meta


def load_leads(path: str | Path) -> dict:
    """Read a lead-quality export: one row per lead, with a status.

    Statuses are matched loosely because CRM exports vary: anything
    containing "qualif" counts unless it also contains "dis".
    """
    file = Path(path)
    if not file.exists():
        raise FileNotFoundError(f"No such lead export: {path}")

    with open(file, newline="", encoding="utf-8-sig") as handle:
        raw = list(csv.DictReader(handle))
    if not raw:
        return {"total": 0}

    headers = list(raw[0].keys())
    status_col = next(
        (h for h in headers if any(k in h.strip().lower()
                                   for k in ("status", "stage", "disposition", "quality"))),
        None,
    )
    campaign_col = _match_column(headers, "campaign")

    buckets = {"qualified": 0, "booked": 0, "disqualified": 0, "pending": 0, "other": 0}
    per_campaign: dict[str, dict] = {}

    for record in raw:
        status = str(record.get(status_col, "") if status_col else "").strip().lower()
        if "book" in status:
            bucket = "booked"
        elif "dis" in status:
            bucket = "disqualified"
        elif "qualif" in status:
            bucket = "qualified"
        elif status in {"", "pending", "new", "open", "follow up", "follow-up"}:
            bucket = "pending"
        else:
            bucket = "other"
        buckets[bucket] += 1

        if campaign_col:
            campaign = (record.get(campaign_col) or "unattributed").strip()
            entry = per_campaign.setdefault(
                campaign, {"total": 0, "qualified": 0, "booked": 0, "disqualified": 0}
            )
            entry["total"] += 1
            if bucket in entry:
                entry[bucket] += 1

    total = len(raw)
    # Booked leads are qualified by definition, so count them in the rate.
    good = buckets["qualified"] + buckets["booked"]
    return {
        "total": total,
        "status_column": status_col,
        **buckets,
        "qualified_rate": round(good / total * 100, 1) if total else 0.0,
        "per_campaign": per_campaign,
    }


def _change(previous: Optional[float], current: Optional[float]) -> Optional[float]:
    if previous is None or current is None or previous == 0:
        return None
    return (current - previous) / previous


def compare(previous: list[Row], current: list[Row]) -> dict:
    """Match rows by name and compute per-metric change."""
    before = {r.name: r for r in previous}
    after = {r.name: r for r in current}

    rows = []
    for name in sorted(set(before) | set(after)):
        a, b = before.get(name), after.get(name)
        entry = {
            "name": name,
            "status": "new" if not a else "stopped" if not b else "active",
            "previous": a.metrics if a else {},
            "current": b.metrics if b else {},
            "change": {},
        }
        if a and b:
            for metric in set(a.metrics) | set(b.metrics):
                delta = _change(a.metrics.get(metric), b.metrics.get(metric))
                if delta is not None:
                    entry["change"][metric] = round(delta * 100, 1)
        rows.append(entry)

    totals = {}
    for metric in ("impressions", "clicks", "spend", "leads"):
        p = sum(r.metrics.get(metric, 0) for r in previous)
        c = sum(r.metrics.get(metric, 0) for r in current)
        if p or c:
            totals[metric] = {
                "previous": round(p, 2), "current": round(c, 2),
                "change_pct": round(_change(p, c) * 100, 1) if _change(p, c) is not None else None,
            }

    combined = Row(name="TOTAL", metrics={
        k: v["current"] for k, v in totals.items()
    })
    combined.derive()
    prior = Row(name="TOTAL_PREV", metrics={k: v["previous"] for k, v in totals.items()})
    prior.derive()
    for key, _, _, _ in DERIVED:
        if key in combined.metrics and key in prior.metrics:
            totals[key] = {
                "previous": prior.metrics[key], "current": combined.metrics[key],
                "change_pct": round(_change(prior.metrics[key], combined.metrics[key]) * 100, 1)
                if _change(prior.metrics[key], combined.metrics[key]) is not None else None,
            }

    return {"totals": totals, "rows": rows}


def explain(comparison: dict, leads: Optional[dict] = None,
            meta: Optional[dict] = None) -> list[dict]:
    """Turn the numbers into findings a person can act on.

    Each finding states what moved, the arithmetic reason it moved, and what
    to do. Nothing here is a guess: every claim decomposes a ratio whose
    inputs are both in the data.
    """
    totals = comparison["totals"]
    findings: list[dict] = []

    # Warn before anything else if the conversion column mixes quantities.
    # A sheet counting reach on one row and page likes on another produces a
    # total that looks authoritative and means nothing.
    mixed = (meta or {}).get("mixed_conversion_metrics")
    if mixed:
        findings.append({
            "severity": "high",
            "headline": "The conversion column mixes different metrics: "
                        + ", ".join(mixed),
            "why": "These are not comparable quantities, so any total or "
                   "cost-per-conversion across them is meaningless.",
            "action": "Split branding rows from lead-generation rows and "
                      "compare each against its own metric.",
        })

    def pct(metric: str) -> Optional[float]:
        return (totals.get(metric) or {}).get("change_pct")

    spend, lead_change = pct("spend"), pct("leads")
    impressions, ctr, cvr, cpl = pct("impressions"), pct("ctr"), pct("cvr"), pct("cpl")

    # Efficiency: spend and leads moving apart is the headline.
    if spend is not None and lead_change is not None:
        if spend > 10 and lead_change < 0:
            findings.append({
                "severity": "critical",
                "headline": f"Spend rose {spend}% while leads fell {abs(lead_change)}%",
                "why": _decompose(ctr, cvr, impressions),
                "action": "Pause the worst-performing campaigns before adding budget.",
            })
        elif lead_change > 10 and spend is not None and spend < lead_change - 10:
            findings.append({
                "severity": "good",
                "headline": f"Leads rose {lead_change}% on {spend}% more spend",
                "why": "Efficiency improved: output grew faster than cost.",
                "action": "Identify which campaigns drove it and shift budget toward them.",
            })

    if cpl is not None and abs(cpl) >= BIG_CHANGE * 100:
        direction = "rose" if cpl > 0 else "fell"
        findings.append({
            "severity": "high" if cpl > 0 else "good",
            "headline": f"Cost per lead {direction} {abs(cpl)}%",
            "why": _decompose(ctr, cvr, impressions),
            "action": ("Check landing pages and creative before raising budgets."
                       if cpl > 0 else "Document what changed so it can be repeated."),
        })

    # Per-campaign movers, worst first.
    movers = [
        r for r in comparison["rows"]
        if r["status"] == "active" and abs(r["change"].get("leads", 0)) >= BIG_CHANGE * 100
    ]
    for row in sorted(movers, key=lambda r: r["change"].get("leads", 0))[:5]:
        delta = row["change"]["leads"]
        findings.append({
            "severity": "high" if delta < 0 else "good",
            "headline": f"{row['name']}: leads {'down' if delta < 0 else 'up'} {abs(delta)}%",
            "why": _decompose(row["change"].get("ctr"), row["change"].get("cvr"),
                              row["change"].get("impressions")),
            "action": ("Review this campaign's creative and targeting."
                       if delta < 0 else "Consider increasing budget here."),
        })

    for row in comparison["rows"]:
        if row["status"] == "stopped":
            findings.append({
                "severity": "medium",
                "headline": f"{row['name']} stopped running",
                "why": "Present last period, absent this one.",
                "action": "Confirm this was intentional.",
            })

    # Lead quality changes the reading of everything above.
    if leads and leads.get("total"):
        rate = leads["qualified_rate"]
        findings.append({
            "severity": "high" if rate < 30 else "info",
            "headline": f"{rate}% of {leads['total']} leads were qualified or booked",
            "why": (f"{leads['qualified']} qualified, {leads['booked']} booked, "
                    f"{leads['disqualified']} disqualified, {leads['pending']} pending."),
            "action": ("Volume is not the problem if most leads are disqualified — "
                       "tighten targeting rather than raising budget."
                       if rate < 30 else
                       "Judge campaigns on qualified leads, not raw lead count."),
        })

        worst = sorted(
            ((name, d) for name, d in leads["per_campaign"].items() if d["total"] >= 5),
            key=lambda kv: (kv[1]["qualified"] + kv[1]["booked"]) / kv[1]["total"],
        )[:3]
        for name, data in worst:
            good = data["qualified"] + data["booked"]
            share = round(good / data["total"] * 100, 1)
            if share < 25:
                findings.append({
                    "severity": "high",
                    "headline": f"{name}: only {share}% of {data['total']} leads qualified",
                    "why": f"{data['disqualified']} of {data['total']} were disqualified.",
                    "action": "This campaign is buying volume, not buyers. Review its targeting.",
                })

    if not findings:
        findings.append({
            "severity": "info",
            "headline": "No material change week over week",
            "why": f"Every tracked metric moved less than {int(MATERIAL_CHANGE * 100)}%.",
            "action": "No action needed.",
        })
    return findings


def _decompose(ctr: Optional[float], cvr: Optional[float],
               impressions: Optional[float]) -> str:
    """Name which input actually moved. Leads = impressions x CTR x CVR."""
    parts = []
    if impressions is not None and abs(impressions) >= MATERIAL_CHANGE * 100:
        parts.append(f"impressions {'up' if impressions > 0 else 'down'} {abs(impressions)}%")
    if ctr is not None and abs(ctr) >= MATERIAL_CHANGE * 100:
        parts.append(f"click-through {'up' if ctr > 0 else 'down'} {abs(ctr)}% "
                     f"({'creative or targeting' if ctr < 0 else 'creative resonating'})")
    if cvr is not None and abs(cvr) >= MATERIAL_CHANGE * 100:
        parts.append(f"conversion rate {'up' if cvr > 0 else 'down'} {abs(cvr)}% "
                     f"({'landing page or offer' if cvr < 0 else 'landing page working'})")
    if not parts:
        return "No single input moved materially; the change is spread across them."
    if len(parts) == 1:
        return f"Driven by {parts[0]}."
    return "Driven by " + ", ".join(parts[:-1]) + f", and {parts[-1]}."


def weekly_report(previous_path: str | Path, current_path: str | Path,
                  leads_path: Optional[str | Path] = None) -> dict:
    """The whole flow: two exports in, analysis out."""
    previous, prev_meta = load_rows(previous_path)
    current, curr_meta = load_rows(current_path)
    if not previous and not current:
        return {"error": "neither export could be read",
                "previous": prev_meta, "current": curr_meta}

    leads = load_leads(leads_path) if leads_path else None
    comparison = compare(previous, current)

    return {
        "columns_used": curr_meta.get("columns_used"),
        "rows_compared": len(comparison["rows"]),
        "totals": comparison["totals"],
        "leads": leads,
        "findings": explain(comparison, leads, curr_meta),
        "campaigns": comparison["rows"],
        "warnings": {
            k: v for k, v in curr_meta.items()
            if k in ("mixed_conversion_metrics", "header_row")
        },
    }
