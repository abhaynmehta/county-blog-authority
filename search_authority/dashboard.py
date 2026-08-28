"""Build a self-contained HTML dashboard from the audit output.

Produces one file with the data embedded, so it opens by double-clicking,
works offline, and can be attached to an email or dropped on any static host.
There is no server, no build step, and nothing to keep running.

The generated page is deliberately a *view*. It cannot run audits — those stay
in the CLI, where they are deterministic and testable.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from .cannibalization import analyse_corpus

INVENTORY_PATH = Path("blogs/BLOG_INVENTORY.yaml")
REPORT_DIRS = [Path("audit-reports/roi"), Path("audit-reports/old-agency")]
DEFAULT_OUTPUT = Path("dashboard/index.html")


def collect_data(inventory_path: Path = INVENTORY_PATH) -> dict:
    """Gather everything the dashboard shows into one JSON-serialisable dict."""
    inventory = yaml.safe_load(inventory_path.read_text(encoding="utf-8")) or {}

    entries: list[dict] = []
    for section in ("already_processed", "roi_google_docs", "old_agency_local"):
        for item in inventory.get(section) or []:
            entries.append({**item, "_section": section})

    documents = []
    issue_totals: dict[str, int] = {}
    owner_totals: dict[str, int] = {}
    gate_failures: dict[str, int] = {}

    for entry in entries:
        local = entry.get("local_file") or entry.get("file")
        if not local:
            continue
        slug = Path(local).stem
        report = _find_report(slug)

        doc = {
            "slug": slug,
            "title": entry.get("title") or slug.replace("-", " ").title(),
            "score": entry.get("score"),
            "publishable": bool(entry.get("publishable")),
            "issues": entry.get("issues") or 0,
            "critical": entry.get("critical") or 0,
            "source": "ROI" if entry["_section"] != "old_agency_local" else "Old agency",
            "gates": {},
            "issue_list": [],
        }

        if report:
            doc["word_count"] = report.get("word_count")
            doc["gates"] = {g["gate"]: g["status"] for g in report.get("gates", [])}
            for gate, status in doc["gates"].items():
                if status == "FAIL":
                    gate_failures[gate] = gate_failures.get(gate, 0) + 1
            for issue in report.get("issues", []):
                sev = issue.get("severity", "info")
                owner = issue.get("owner", "ROI")
                issue_totals[sev] = issue_totals.get(sev, 0) + 1
                owner_totals[owner] = owner_totals.get(owner, 0) + 1
                doc["issue_list"].append({
                    "id": issue.get("issue_id"),
                    "severity": sev,
                    "owner": owner,
                    "summary": issue.get("summary", ""),
                    "claim": (issue.get("claim") or "")[:200],
                    "action": issue.get("recommended_action", ""),
                    "test": issue.get("acceptance_test", ""),
                })

        documents.append(doc)

    scored = [d for d in documents if isinstance(d["score"], int)]
    scores = [d["score"] for d in scored]

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "total": len(documents),
            "scored": len(scored),
            "publishable": sum(1 for d in documents if d["publishable"]),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "critical_docs": sum(1 for d in documents if d["critical"]),
            "bands": {
                "90+": sum(1 for s in scores if s >= 90),
                "80-89": sum(1 for s in scores if 80 <= s < 90),
                "70-79": sum(1 for s in scores if 70 <= s < 80),
                "60-69": sum(1 for s in scores if 60 <= s < 70),
                "<60": sum(1 for s in scores if s < 60),
            },
        },
        "issue_totals": issue_totals,
        "owner_totals": owner_totals,
        "gate_failures": gate_failures,
        "documents": sorted(documents, key=lambda d: (d["score"] is None, d["score"] or 0)),
        "cannibalization": analyse_corpus(entries),
    }


def _find_report(slug: str) -> Optional[dict]:
    for directory in REPORT_DIRS:
        path = directory / f"{slug}-audit-report.json"
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return None
    return None


def build(output: Path = DEFAULT_OUTPUT,
          inventory_path: Path = INVENTORY_PATH) -> dict:
    """Write the dashboard and return the data it was built from."""
    data = collect_data(inventory_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_render(data), encoding="utf-8")
    return {
        "output": str(output),
        "documents": data["summary"]["total"],
        "publishable": data["summary"]["publishable"],
        "collisions": data["cannibalization"]["collisions"],
    }


def _render(data: dict) -> str:
    """Inline the data into the page template.

    Titles and quoted text come from agency documents, so they are untrusted.
    Escaping `<`, `>` and `&` as unicode sequences keeps a title containing
    `</script>` from closing the block and injecting markup. JSON.parse
    decodes them back to the original characters, so the data is unchanged.
    """
    payload = json.dumps(data, indent=None, separators=(",", ":"), default=str)
    for char, escaped in (
        ("&", "\\u0026"), ("<", "\\u003c"), (">", "\\u003e"),
        ("\u2028", "\\u2028"), ("\u2029", "\\u2029"),
    ):
        payload = payload.replace(char, escaped)
    return _TEMPLATE.replace("/*DATA*/", payload)


_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>County Group Content Dashboard</title>
<style>
:root{
  --ground:#F6F7F6;--surface:#FFFFFF;--raised:#EFF1EF;
  --ink:#15181B;--ink2:#4E545A;--ink3:#848B91;
  --rule:#DCE0DC;--rule-soft:#E9ECE9;
  --primary:#1F6152;
  --good:#1B6B45;--good-bg:#E6F2EA;
  --warn:#8A5D00;--warn-bg:#FBF2DE;
  --bad:#A32226;--bad-bg:#FAE9E9;
  --info:#1B4C96;--info-bg:#E8EFFA;
}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){
  --ground:#111315;--surface:#181B1E;--raised:#212528;
  --ink:#E4E5E2;--ink2:#A2A8AD;--ink3:#71787E;
  --rule:#2C3135;--rule-soft:#23272A;
  --primary:#5FB79E;
  --good:#5CC98D;--good-bg:#122619;
  --warn:#E0B44C;--warn-bg:#2A2110;
  --bad:#E97B7E;--bad-bg:#2B1516;
  --info:#7BA7EC;--info-bg:#141E2E;
}}
:root[data-theme=dark]{
  --ground:#111315;--surface:#181B1E;--raised:#212528;
  --ink:#E4E5E2;--ink2:#A2A8AD;--ink3:#71787E;
  --rule:#2C3135;--rule-soft:#23272A;
  --primary:#5FB79E;
  --good:#5CC98D;--good-bg:#122619;
  --warn:#E0B44C;--warn-bg:#2A2110;
  --bad:#E97B7E;--bad-bg:#2B1516;
  --info:#7BA7EC;--info-bg:#141E2E;
}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--ground);color:var(--ink);font-family:'DM Sans',system-ui,-apple-system,Segoe UI,sans-serif;font-size:14px;line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:22px 18px 60px}
header{border-bottom:2px solid var(--ink);padding-bottom:14px;margin-bottom:20px;display:flex;justify-content:space-between;align-items:flex-end;gap:14px;flex-wrap:wrap}
h1{font-size:23px;font-weight:700;letter-spacing:-.01em}
.stamp{font-size:11.5px;color:var(--ink3);font-variant-numeric:tabular-nums}
.kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:9px;margin-bottom:20px}
@media(max-width:760px){.kpis{grid-template-columns:repeat(2,1fr)}}
.kpi{background:var(--surface);border:1px solid var(--rule);border-radius:7px;padding:12px 14px}
.kpi-l{font-size:10.5px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--ink3)}
.kpi-v{font-size:25px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1.2;margin-top:1px}
.kpi-n{font-size:11px;color:var(--ink3)}
.g{color:var(--good)}.w{color:var(--warn)}.b{color:var(--bad)}.i{color:var(--info)}
nav.tabs{display:flex;gap:3px;border-bottom:1px solid var(--rule);margin-bottom:16px;overflow-x:auto}
.tab{padding:8px 15px;font-size:13px;font-weight:600;color:var(--ink3);background:none;border:none;border-bottom:2px solid transparent;cursor:pointer;white-space:nowrap;font-family:inherit}
.tab:hover{color:var(--ink)}
.tab[aria-selected=true]{color:var(--primary);border-bottom-color:var(--primary)}
.panel[hidden]{display:none}
.bar{display:flex;gap:8px;align-items:center;margin-bottom:12px;flex-wrap:wrap}
input[type=search],select{font-family:inherit;font-size:13px;padding:7px 10px;border:1px solid var(--rule);border-radius:6px;background:var(--surface);color:var(--ink)}
input[type=search]{flex:1;min-width:180px}
.count{font-size:12px;color:var(--ink3);font-variant-numeric:tabular-nums}
.tw{overflow-x:auto;border:1px solid var(--rule);border-radius:7px;background:var(--surface)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;color:var(--ink3);padding:9px 11px;background:var(--raised);border-bottom:1px solid var(--rule);font-weight:600;white-space:nowrap;cursor:pointer;user-select:none}
th:hover{color:var(--ink)}
td{padding:9px 11px;border-bottom:1px solid var(--rule-soft);vertical-align:top}
tbody tr:last-child td{border-bottom:none}
tbody tr.row{cursor:pointer}
tbody tr.row:hover{background:var(--raised)}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.pill{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;padding:2px 7px;border-radius:3px;white-space:nowrap}
.p-good{background:var(--good-bg);color:var(--good)}
.p-warn{background:var(--warn-bg);color:var(--warn)}
.p-bad{background:var(--bad-bg);color:var(--bad)}
.p-info{background:var(--info-bg);color:var(--info)}
.p-mut{background:var(--raised);color:var(--ink3)}
.detail{background:var(--raised)}
.detail td{padding:0}
.detail-in{padding:12px 14px}
.issue{border-left:3px solid var(--rule);padding:8px 0 8px 11px;margin-bottom:9px}
.issue:last-child{margin-bottom:0}
.issue.critical{border-left-color:var(--bad)}
.issue.high{border-left-color:var(--warn)}
.issue.medium{border-left-color:var(--ink3)}
.issue-h{font-weight:700;font-size:13px;margin-bottom:3px}
.issue-m{font-size:12px;color:var(--ink2);margin-bottom:2px}
.issue-m b{color:var(--ink)}
.quote{font-style:italic;color:var(--ink2);background:var(--surface);border:1px solid var(--rule-soft);border-radius:4px;padding:5px 8px;margin:4px 0;font-size:12px}
.bandrow{display:flex;align-items:center;gap:9px;margin-bottom:5px}
.bandlab{min-width:56px;font-size:12px;color:var(--ink2);text-align:right;font-variant-numeric:tabular-nums}
.bandtrack{flex:1;height:20px;background:var(--raised);border-radius:4px;overflow:hidden}
.bandfill{height:100%;border-radius:4px}
.bandnum{min-width:26px;font-size:12px;font-weight:700;text-align:right;font-variant-numeric:tabular-nums}
.card{background:var(--surface);border:1px solid var(--rule);border-radius:7px;padding:15px 17px;margin-bottom:13px}
.card h3{font-size:14.5px;font-weight:700;margin-bottom:7px}
.card p{font-size:13px;color:var(--ink2);margin-bottom:8px}
.card p:last-child{margin-bottom:0}
.note{background:var(--info-bg);border:1px solid var(--info);border-radius:6px;padding:12px 15px;font-size:13px;margin-bottom:14px}
.note b{color:var(--info)}
.rebut{background:var(--bad-bg);border:1px solid var(--bad);border-radius:6px;padding:11px 14px;margin-top:9px;font-size:12.5px}
.rebut b{color:var(--bad)}
.rebut ul{margin:6px 0 0 17px}
.rebut li{margin-bottom:4px}
.pair{font-weight:600;font-size:13px}
.terms{font-size:12px;color:var(--ink2);margin-top:3px}
.empty{padding:26px;text-align:center;color:var(--ink3);font-size:13px}
footer{margin-top:26px;padding-top:13px;border-top:1px solid var(--rule);font-size:11.5px;color:var(--ink3)}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div>
    <h1>County Group Content Dashboard</h1>
    <div class="stamp" id="stamp"></div>
  </div>
  <div class="stamp">Read-only view &middot; regenerate with <code>agent dashboard</code></div>
</header>

<div class="kpis" id="kpis"></div>

<nav class="tabs" role="tablist">
  <button class="tab" role="tab" aria-selected="true" data-panel="docs">Documents</button>
  <button class="tab" role="tab" aria-selected="false" data-panel="cannib">Keyword Overlap</button>
  <button class="tab" role="tab" aria-selected="false" data-panel="gates">Gates &amp; Owners</button>
</nav>

<section class="panel" id="docs">
  <div class="bar">
    <input type="search" id="q" placeholder="Search by title or slug…" aria-label="Search documents">
    <select id="filter" aria-label="Filter documents">
      <option value="all">All documents</option>
      <option value="blocked">Not publishable</option>
      <option value="critical">Has critical issues</option>
      <option value="publishable">Publishable</option>
      <option value="low">Score below 60</option>
    </select>
    <span class="count" id="count"></span>
  </div>
  <div class="tw">
    <table id="tbl">
      <thead><tr>
        <th data-sort="title">Document</th>
        <th data-sort="source">Source</th>
        <th data-sort="score" class="num">Score</th>
        <th data-sort="issues" class="num">Issues</th>
        <th data-sort="critical" class="num">Critical</th>
        <th data-sort="publishable">Status</th>
      </tr></thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>
</section>

<section class="panel" id="cannib" hidden>
  <div class="note">
    <b>What this is.</b> Two pages competing for the same search query. Google picks one — often not the one you want — and both rank worse than a single page would. This is <b>not</b> duplicate content, and canonical tags do not fix it.
  </div>
  <div class="bar">
    <select id="cfilter" aria-label="Filter by severity">
      <option value="high">High severity only</option>
      <option value="all">All severities</option>
      <option value="medium">Medium</option>
      <option value="low">Low</option>
    </select>
    <span class="count" id="ccount"></span>
  </div>
  <div id="clist"></div>
</section>

<section class="panel" id="gates" hidden>
  <div class="card">
    <h3>Score distribution</h3>
    <div id="bands"></div>
  </div>
  <div class="card">
    <h3>Gate failures across the corpus</h3>
    <div id="gatelist"></div>
  </div>
  <div class="card">
    <h3>Who owns the work</h3>
    <div id="owners"></div>
  </div>
</section>

<footer id="foot"></footer>
</div>

<script id="payload" type="application/json">/*DATA*/</script>
<script>
"use strict";
var DATA = JSON.parse(document.getElementById("payload").textContent);
var $ = function (id) { return document.getElementById(id); };

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}
function scoreClass(s) {
  if (s == null) return "p-mut";
  if (s >= 80) return "p-good";
  if (s >= 60) return "p-warn";
  return "p-bad";
}

/* ---- header ---- */
$("stamp").textContent = "Generated " + DATA.generated_at.replace("T", " ");
var s = DATA.summary;
$("kpis").innerHTML = [
  ["Documents", s.total, "audited", ""],
  ["Publishable", s.publishable, Math.round(s.publishable / Math.max(1, s.total) * 100) + "% of corpus", s.publishable / Math.max(1, s.total) >= 0.7 ? "g" : "w"],
  ["Average score", s.avg_score, "target 85+", s.avg_score >= 80 ? "g" : "w"],
  ["With critical issues", s.critical_docs, "cannot publish", s.critical_docs ? "b" : "g"],
  ["Keyword collisions", DATA.cannibalization.by_severity.high, "high severity", DATA.cannibalization.by_severity.high ? "b" : "g"]
].map(function (k) {
  return '<div class="kpi"><div class="kpi-l">' + k[0] + '</div><div class="kpi-v ' + k[3] + '">' + k[1] + '</div><div class="kpi-n">' + k[2] + "</div></div>";
}).join("");

/* ---- tabs ---- */
Array.prototype.forEach.call(document.querySelectorAll(".tab"), function (tab) {
  tab.addEventListener("click", function () {
    document.querySelectorAll(".tab").forEach(function (t) { t.setAttribute("aria-selected", String(t === tab)); });
    document.querySelectorAll(".panel").forEach(function (p) { p.hidden = p.id !== tab.dataset.panel; });
  });
});

/* ---- documents ---- */
var sortKey = "score", sortAsc = true, openRow = null;

function visibleDocs() {
  var q = $("q").value.trim().toLowerCase();
  var f = $("filter").value;
  return DATA.documents.filter(function (d) {
    if (q && (d.title + " " + d.slug).toLowerCase().indexOf(q) === -1) return false;
    if (f === "blocked" && d.publishable) return false;
    if (f === "publishable" && !d.publishable) return false;
    if (f === "critical" && !d.critical) return false;
    if (f === "low" && !(d.score != null && d.score < 60)) return false;
    return true;
  }).sort(function (a, b) {
    var x = a[sortKey], y = b[sortKey];
    if (x == null) x = -1; if (y == null) y = -1;
    if (typeof x === "string") { x = x.toLowerCase(); y = String(y).toLowerCase(); }
    if (x < y) return sortAsc ? -1 : 1;
    if (x > y) return sortAsc ? 1 : -1;
    return 0;
  });
}

function issueHTML(d) {
  if (!d.issue_list.length) return '<div class="empty">No issues recorded.</div>';
  var order = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
  return d.issue_list.slice().sort(function (a, b) {
    return (order[a.severity] || 9) - (order[b.severity] || 9);
  }).map(function (i) {
    return '<div class="issue ' + esc(i.severity) + '">' +
      '<div class="issue-h">' + esc(i.summary) + " " +
        '<span class="pill ' + (i.severity === "critical" ? "p-bad" : i.severity === "high" ? "p-warn" : "p-mut") + '">' + esc(i.severity) + "</span> " +
        '<span class="pill p-mut">' + esc(i.owner) + "</span></div>" +
      (i.claim ? '<div class="quote">' + esc(i.claim) + "</div>" : "") +
      '<div class="issue-m"><b>Fix:</b> ' + esc(i.action) + "</div>" +
      '<div class="issue-m"><b>Done when:</b> ' + esc(i.test) + "</div>" +
    "</div>";
  }).join("");
}

function renderDocs() {
  var rows = visibleDocs();
  $("count").textContent = rows.length + " of " + DATA.documents.length;
  $("tbody").innerHTML = rows.map(function (d) {
    var gateFails = Object.keys(d.gates || {}).filter(function (g) { return d.gates[g] === "FAIL"; });
    return '<tr class="row" data-slug="' + esc(d.slug) + '">' +
      "<td>" + esc(d.title) + (gateFails.length ? ' <span class="pill p-bad">' + gateFails.length + " gate" + (gateFails.length > 1 ? "s" : "") + "</span>" : "") +
        '<div class="issue-m" style="color:var(--ink3)">' + esc(d.slug) + "</div></td>" +
      "<td>" + esc(d.source) + "</td>" +
      '<td class="num"><span class="pill ' + scoreClass(d.score) + '">' + (d.score == null ? "—" : d.score) + "</span></td>" +
      '<td class="num">' + d.issues + "</td>" +
      '<td class="num">' + (d.critical ? '<span class="pill p-bad">' + d.critical + "</span>" : "0") + "</td>" +
      "<td>" + (d.publishable ? '<span class="pill p-good">Publishable</span>' : '<span class="pill p-bad">Blocked</span>') + "</td>" +
    "</tr>" +
    '<tr class="detail" hidden data-detail="' + esc(d.slug) + '"><td colspan="6"><div class="detail-in">' + issueHTML(d) + "</div></td></tr>";
  }).join("");

  Array.prototype.forEach.call(document.querySelectorAll("tr.row"), function (tr) {
    tr.addEventListener("click", function () {
      var det = document.querySelector('tr[data-detail="' + tr.dataset.slug + '"]');
      if (det) det.hidden = !det.hidden;
    });
  });
}

$("q").addEventListener("input", renderDocs);
$("filter").addEventListener("change", renderDocs);
Array.prototype.forEach.call(document.querySelectorAll("th[data-sort]"), function (th) {
  th.addEventListener("click", function () {
    var k = th.dataset.sort;
    if (sortKey === k) { sortAsc = !sortAsc; } else { sortKey = k; sortAsc = k === "title" || k === "source"; }
    renderDocs();
  });
});

/* ---- cannibalisation ---- */
function renderCannib() {
  var f = $("cfilter").value;
  var items = DATA.cannibalization.details.filter(function (c) { return f === "all" || c.severity === f; });
  $("ccount").textContent = items.length + " shown of " + DATA.cannibalization.collisions + " total";
  if (!items.length) { $("clist").innerHTML = '<div class="empty">No overlaps at this severity.</div>'; return; }
  $("clist").innerHTML = items.map(function (c) {
    return '<div class="card">' +
      '<div class="pair">' + esc(c.pages[0]) + '<br><span style="color:var(--ink3);font-weight:400">competing with</span><br>' + esc(c.pages[1]) +
        ' <span class="pill ' + (c.severity === "high" ? "p-bad" : c.severity === "medium" ? "p-warn" : "p-mut") + '">' + esc(c.severity) + "</span></div>" +
      '<div class="terms"><b>Shared terms:</b> ' + esc(c.shared_terms.join(", ")) + "</div>" +
      "<p style=\"margin-top:8px\"><b>Fix:</b> " + esc(c.recommended_action) + "</p>" +
      '<div class="rebut"><b>If someone says this is already handled:</b><ul>' +
        c.not_fixed_by.map(function (r) { return "<li>" + esc(r) + "</li>"; }).join("") +
      "</ul></div>" +
      '<p style="margin-top:8px;font-size:12.5px"><b>Verify it yourself:</b> ' + esc(c.how_to_verify) + "</p>" +
    "</div>";
  }).join("");
}
$("cfilter").addEventListener("change", renderCannib);

/* ---- gates ---- */
(function () {
  var bands = DATA.summary.bands;
  var max = Math.max.apply(null, Object.keys(bands).map(function (k) { return bands[k]; }).concat([1]));
  var colors = { "90+": "var(--good)", "80-89": "var(--good)", "70-79": "var(--warn)", "60-69": "var(--warn)", "<60": "var(--bad)" };
  $("bands").innerHTML = Object.keys(bands).map(function (k) {
    return '<div class="bandrow"><div class="bandlab">' + k + "</div>" +
      '<div class="bandtrack"><div class="bandfill" style="width:' + (bands[k] / max * 100) + "%;background:" + colors[k] + '"></div></div>' +
      '<div class="bandnum">' + bands[k] + "</div></div>";
  }).join("");

  var gf = DATA.gate_failures, gk = Object.keys(gf).sort(function (a, b) { return gf[b] - gf[a]; });
  $("gatelist").innerHTML = gk.length ? gk.map(function (g) {
    return '<div class="bandrow"><div class="bandlab" style="min-width:170px;text-align:left">' + esc(g) + "</div>" +
      '<div class="bandtrack"><div class="bandfill" style="width:' + (gf[g] / DATA.summary.total * 100) + '%;background:var(--bad)"></div></div>' +
      '<div class="bandnum">' + gf[g] + "</div></div>";
  }).join("") : '<div class="empty">No gate failures.</div>';

  var ot = DATA.owner_totals, ok = Object.keys(ot).sort(function (a, b) { return ot[b] - ot[a]; });
  var totalIssues = ok.reduce(function (n, k) { return n + ot[k]; }, 0) || 1;
  $("owners").innerHTML = ok.map(function (o) {
    return '<div class="bandrow"><div class="bandlab" style="min-width:80px;text-align:left">' + esc(o) + "</div>" +
      '<div class="bandtrack"><div class="bandfill" style="width:' + (ot[o] / totalIssues * 100) + '%;background:var(--primary)"></div></div>' +
      '<div class="bandnum">' + ot[o] + "</div></div>";
  }).join("");
})();

$("foot").textContent = "County Group Blog Authority System · " + DATA.summary.total +
  " documents · " + DATA.cannibalization.collisions + " keyword overlaps · generated " +
  DATA.generated_at.replace("T", " ");

renderDocs();
renderCannib();
</script>
</body>
</html>
"""
