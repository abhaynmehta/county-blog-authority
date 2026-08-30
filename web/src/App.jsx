import { useEffect, useMemo, useState } from "react";
import { api, sortIssues, scoreBand } from "./api.js";
import Corpus from "./Corpus.jsx";
import Hygiene from "./Hygiene.jsx";
import Overlap from "./Overlap.jsx";
import Reports from "./Reports.jsx";
import Social from "./Social.jsx";
import History from "./History.jsx";
import Benchmark from "./Benchmark.jsx";
import SchemaGenerator from "./SchemaGenerator.jsx";
import RegistryHealth from "./RegistryHealth.jsx";

const NAV = [
  { group: "Overview", items: [
    { id: "dashboard", label: "Dashboard", icon: "▣" },
  ]},
  { group: "Content", items: [
    { id: "audit", label: "Audit a draft", icon: "✎" },
    { id: "schema", label: "Schema generator", icon: "{ }" },
    { id: "corpus", label: "All content", icon: "☰" },
    { id: "history", label: "Repeat mistakes", icon: "↺" },
  ]},
  { group: "Search", items: [
    { id: "overlap", label: "Keyword overlap", icon: "↔" },
    { id: "hygiene", label: "Live pages", icon: "⚡" },
    { id: "benchmark", label: "Competitors", icon: "⚑" },
  ]},
  { group: "Performance", items: [
    { id: "reports", label: "Ads report", icon: "▲" },
    { id: "social", label: "Social report", icon: "●" },
  ]},
  { group: "Registry", items: [
    { id: "registry", label: "Registry health", icon: "♥" },
  ]},
];

/* ── Small presentational pieces ─────────────────────────────────────── */

function Pill({ tone = "mut", children }) {
  return <span className={`pill pill-${tone}`}>{children}</span>;
}

function severityTone(severity) {
  if (severity === "critical") return "bad";
  if (severity === "high") return "warn";
  if (severity === "info") return "info";
  return "mut";
}

function GateRow({ gate }) {
  const tone =
    gate.status === "PASS" ? "good" : gate.status === "FAIL" ? "bad" : "warn";
  return (
    <div className="gate">
      <Pill tone={tone}>{gate.status}</Pill>
      <span className="gate-name">{gate.gate}</span>
      <span className="gate-detail">{gate.details}</span>
    </div>
  );
}

const ISSUE_DOCS = {
  meta_title: {
    label: "Title element best practices",
    url: "https://developers.google.com/search/docs/appearance/title-link",
    tip: "Google rewrites titles that are too long, stuffed with keywords, or don't match the page. Keep it 30-60 characters, front-load the main keyword, and make it read like a headline a person would click.",
  },
  meta_description: {
    label: "Meta description guidance",
    url: "https://developers.google.com/search/docs/appearance/snippet",
    tip: "Google uses the meta description as the snippet under your title in search results. Keep it 120-155 characters, include the target keyword naturally, and make it a clear summary of what the reader will get.",
  },
  heading_structure: {
    label: "Heading structure for SEO",
    url: "https://developers.google.com/search/docs/fundamentals/seo-starter-guide#use-heading-tags",
    tip: "Headings (H1, H2, H3) tell Google what your page is about, like a table of contents. Use one H1 per page, then H2s for main sections, H3s for sub-sections. Don't skip levels (H1 then H3).",
  },
  factual_error: {
    label: "E-E-A-T quality guidelines",
    url: "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
    tip: "Factual errors hurt your site's trustworthiness. Google checks if content is accurate, especially for 'Your Money or Your Life' topics like real estate. Always verify facts against official sources (RERA portal, government sites).",
  },
  image_seo: {
    label: "Image SEO best practices",
    url: "https://developers.google.com/search/docs/appearance/google-images",
    tip: "Every image needs descriptive alt text (what's in the image, in plain words). Use descriptive filenames (floor-plan-3bhk.jpg, not IMG_001.jpg). Compress images so pages load fast.",
  },
  internal_links: {
    label: "Link best practices",
    url: "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
    tip: "Internal links help Google discover your other pages and understand which pages are important. Link to related blog posts and project pages using descriptive anchor text (not 'click here').",
  },
  external_links: {
    label: "Outbound link quality",
    url: "https://developers.google.com/search/docs/essentials/spam-policies#link-spam",
    tip: "Link to high-quality, relevant sources (government sites, official RERA portals, news outlets). Don't link to spammy or irrelevant sites. This builds credibility with Google.",
  },
  spam_signal: {
    label: "Google spam policies",
    url: "https://developers.google.com/search/docs/essentials/spam-policies",
    tip: "Repeating the same keyword too many times, excessive CTAs ('Buy Now! Call Now! Book Now!'), and hidden text are spam signals. Google can penalize or remove pages that use these tricks.",
  },
  schema_missing: {
    label: "Structured data (JSON-LD)",
    url: "https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data",
    tip: "Schema markup is invisible code that tells Google exactly what your page is about. For blogs, BlogPosting schema helps Google show rich results (author, date, image) in search.",
  },
  schema_invalid: {
    label: "Fix structured data errors",
    url: "https://developers.google.com/search/docs/appearance/structured-data/sd-policies",
    tip: "Schema must match what's actually on the page. If the schema says 'published 2024' but the page says 2025, Google ignores it. Use the Schema Generator tab to create valid schema.",
  },
  keyword_cannibalization: {
    label: "Content overlap guidance",
    url: "https://developers.google.com/search/docs/fundamentals/seo-starter-guide#avoid-duplicate-content",
    tip: "When two of your pages target the same keyword, they compete with each other. Google picks one — often not the one you want. Merge the pages or make each target a different keyword.",
  },
  rera_compliance: {
    label: "RERA Act reference",
    url: "https://www.up-rera.in/",
    tip: "RERA (Real Estate Regulatory Authority) requires that all property advertising matches the registered details. Never claim features not in the RERA filing. Always include the RERA registration number.",
  },
  prohibited_language: {
    label: "Advertising Standards Council",
    url: "https://ascionline.in/",
    tip: "Certain phrases are banned because they're misleading ('best in Noida', 'guaranteed returns', '100% on-time delivery'). Use factual, verifiable language instead.",
  },
  unsupported_claim: {
    label: "Content helpfulness guidelines",
    url: "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
    tip: "Every claim needs a source. 'Premium amenities' means nothing without specifics. 'Indoor heated swimming pool (per project brochure)' is verifiable and trustworthy.",
  },
  canonical: {
    label: "Canonical URL setup",
    url: "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    tip: "A canonical URL tells Google which version of a page is the 'main' one. Without it, Google might treat different URLs as duplicates and pick the wrong one to show.",
  },
  ai_readiness: {
    label: "AI citation optimization",
    url: "https://developers.google.com/search/docs/appearance/ai-overviews",
    tip: "AI search (like Google AI Overviews) pulls from pages that answer questions directly. Use clear Q&A format, put key facts early in paragraphs, and cite sources — this makes your content more likely to be quoted by AI.",
  },
};

function Issue({ issue }) {
  const [expanded, setExpanded] = useState(false);
  const doc = ISSUE_DOCS[issue.category];

  return (
    <article className={`issue issue-${issue.severity}`}>
      <header className="issue-head" onClick={() => setExpanded(!expanded)} style={{ cursor: "pointer" }}>
        <Pill tone={severityTone(issue.severity)}>{issue.severity}</Pill>
        <Pill tone="mut">{issue.owner}</Pill>
        <h4>{issue.summary}</h4>
        <span className="expand-icon">{expanded ? "▾" : "▸"}</span>
      </header>
      {issue.quoted_text && (
        <blockquote className="quote">{issue.quoted_text}</blockquote>
      )}
      {issue.verified_fact && (
        <p className="meta">
          <b>Verified fact:</b> {issue.verified_fact}
        </p>
      )}
      <p className="meta">
        <b>Fix:</b> {issue.recommended_action}
      </p>
      <p className="meta">
        <b>Done when:</b> {issue.acceptance_test}
      </p>
      {expanded && (
        <div className="issue-detail">
          {doc && (
            <>
              <p className="issue-tip">{doc.tip}</p>
              <a className="issue-doc-link" href={doc.url} target="_blank" rel="noopener noreferrer">
                Read Google's official guide: {doc.label} ↗
              </a>
            </>
          )}
          {issue.rule && (
            <p className="meta" style={{ marginTop: 8 }}>
              <b>Rule:</b> {issue.rule}
            </p>
          )}
        </div>
      )}
    </article>
  );
}

/* ── Reference panel: the verified figures, beside the editor ────────── */

function ProjectReference({ projects }) {
  const [open, setOpen] = useState(null);
  if (!projects?.length) return null;

  return (
    <section className="card">
      <h3>Verified figures</h3>
      <p className="hint">
        What the registry holds. Check any number against this before publishing.
      </p>
      {projects.map((project) => (
        <div key={project.slug} className="proj">
          <button
            className="proj-head"
            onClick={() => setOpen(open === project.slug ? null : project.slug)}
            aria-expanded={open === project.slug}
          >
            <b>{project.name}</b>
            <span className="proj-loc">
              {[project.sector && `Sector ${project.sector}`, project.city]
                .filter(Boolean)
                .join(", ")}
              {project.rera_authority ? ` · ${project.rera_authority}` : ""}
            </span>
          </button>
          {open === project.slug && (
            <div className="proj-body">
              {project.configurations?.length ? (
                <table className="mini">
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>Carpet</th>
                      <th>Super</th>
                      <th>Tier</th>
                    </tr>
                  </thead>
                  <tbody>
                    {project.configurations.map((c, i) => (
                      <tr key={i}>
                        <td>{c.type}</td>
                        <td className="num">{c.carpet_area_sqft ?? "—"}</td>
                        <td className="num">{c.super_area_sqft ?? "—"}</td>
                        <td>{c.tier ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="hint">No configurations recorded.</p>
              )}
              {project.prohibited?.length > 0 && (
                <ul className="banned">
                  {project.prohibited.map((rule, i) => (
                    <li key={i}>{rule}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      ))}
    </section>
  );
}

/* ── Dashboard overview ─────────────────────────────────────────────── */

function Dashboard({ onNavigate }) {
  const [health, setHealth] = useState(null);
  const [corpus, setCorpus] = useState(null);
  const [history, setHistory] = useState(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => {});
    api.corpus().then(setCorpus).catch(() => {});
    api.history().then(setHistory).catch(() => {});
  }, []);

  const summary = corpus?.summary;

  return (
    <>
      <div className="kpis">
        <div className="kpi">
          <div className="kpi-l">Documents</div>
          <div className="kpi-v">{summary?.total ?? "—"}</div>
          <div className="kpi-n">in corpus</div>
        </div>
        <div className="kpi">
          <div className="kpi-l">Publishable</div>
          <div className={`kpi-v ${summary ? (summary.publishable / summary.total >= 0.6 ? "good" : "bad") : ""}`}>
            {summary ? `${Math.round((summary.publishable / summary.total) * 100)}%` : "—"}
          </div>
          <div className="kpi-n">{summary?.publishable ?? 0} of {summary?.total ?? 0}</div>
        </div>
        <div className="kpi">
          <div className="kpi-l">Avg score</div>
          <div className={`kpi-v ${summary ? (summary.avg_score >= 80 ? "good" : summary.avg_score >= 60 ? "" : "bad") : ""}`}>
            {summary?.avg_score ?? "—"}
          </div>
          <div className="kpi-n">target 85+</div>
        </div>
        <div className="kpi">
          <div className="kpi-l">Audits recorded</div>
          <div className="kpi-v">{history?.runs ?? 0}</div>
          <div className="kpi-n">{history?.documents ?? 0} unique docs</div>
        </div>
      </div>

      <div className="overview-grid">
        <div className="overview-card" onClick={() => onNavigate("corpus")}>
          <h4>Content health</h4>
          <div className="overview-stat" style={{color: summary?.critical_docs ? "var(--bad)" : "var(--good)"}}>
            {summary?.critical_docs ?? 0} blocked
          </div>
          <p>{summary?.critical_docs ? `${summary.critical_docs} documents have critical issues and cannot be published` : "No documents are blocked from publication"}</p>
        </div>
        <div className="overview-card" onClick={() => onNavigate("history")}>
          <h4>Repeat mistakes</h4>
          <div className="overview-stat" style={{color: (history?.regressions?.length ?? 0) > 0 ? "var(--bad)" : "var(--good)"}}>
            {history?.regressions?.length ?? 0} regressions
          </div>
          <p>{history?.recurring_mistakes?.length ? `Top: ${history.recurring_mistakes[0].category.replace(/_/g, " ")} (${history.recurring_mistakes[0].share_pct}% of docs)` : "No recurring patterns detected yet"}</p>
        </div>
      </div>

      <section className="card" style={{marginTop: 14}}>
        <h3>System status</h3>
        <ul className="status-list">
          <li className="status-item">
            <span className={`status-dot ${health?.status === "ok" ? "ok" : "err"}`} />
            <span className="status-label">Engine</span>
            <span className="status-value">{health?.engine_version ?? "..."}</span>
          </li>
          <li className="status-item">
            <span className={`status-dot ${health?.registry_errors?.length === 0 ? "ok" : "err"}`} />
            <span className="status-label">Registry</span>
            <span className="status-value">{health?.projects_loaded ?? 0} projects, {health?.claims_loaded ?? 0} claims</span>
          </li>
          <li className="status-item">
            <span className={`status-dot ${health?.storage?.durable ? "ok" : "warn"}`} />
            <span className="status-label">Storage</span>
            <span className="status-value">{health?.storage?.durable ? "Durable" : "Ephemeral"}</span>
          </li>
          {health?.registry_errors?.length > 0 && (
            <li className="status-item">
              <span className="status-dot err" />
              <span className="status-label" style={{color: "var(--bad)"}}>
                {health.registry_errors.length} registry error(s)
              </span>
            </li>
          )}
        </ul>
      </section>

      <h3 style={{fontSize: 14, fontWeight: 700, margin: "20px 0 10px", color: "var(--ink2)"}}>Quick actions</h3>
      <div className="quick-actions">
        <button className="quick-action" onClick={() => onNavigate("audit")}>
          Audit a draft
          <span>Paste content and check before publishing</span>
        </button>
        <button className="quick-action" onClick={() => onNavigate("overlap")}>
          Check keyword overlap
          <span>Find pages competing for the same query</span>
        </button>
        <button className="quick-action" onClick={() => onNavigate("benchmark")}>
          Run competitor benchmark
          <span>Compare against Prateek, Ace, Eldeco, Gaursons</span>
        </button>
      </div>
    </>
  );
}

/* ── Audit panel ────────────────────────────────────────────────────── */

function AuditPanel() {
  const [content, setContent] = useState("");
  const [slug, setSlug] = useState("untitled");
  const [result, setResult] = useState(null);
  const [projects, setProjects] = useState([]);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .projects()
      .then((data) => setProjects(data.projects ?? []))
      .catch(() => setProjects([]));
  }, []);

  async function runAudit(event) {
    event.preventDefault();
    setStatus("loading");
    setError(null);
    try {
      setResult(await api.audit(content, slug || "untitled"));
      setStatus("done");
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }

  const issues = useMemo(() => sortIssues(result?.issues), [result]);
  const wordCount = content.trim() ? content.trim().split(/\s+/).length : 0;

  return (
    <div className="cols">
        <div className="col">
          <form className="card" onSubmit={runAudit}>
            <label className="lbl" htmlFor="slug">
              Slug
            </label>
            <input
              id="slug"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              placeholder="clove-county-amenities"
            />

            <label className="lbl" htmlFor="content">
              Draft content
            </label>
            <textarea
              id="content"
              rows={18}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Paste the blog draft here…"
            />

            <div className="row">
              <button type="submit" disabled={status === "loading" || !content.trim()}>
                {status === "loading" ? "Auditing…" : "Run audit"}
              </button>
              <span className="hint">{wordCount} words</span>
            </div>

            {error && (
              <p role="alert" className="err">
                {error}
              </p>
            )}
          </form>

          <ProjectReference projects={projects} />
        </div>

        <div className="col">
          {!result && status !== "loading" && (
            <div className="card empty">
              <p>Results appear here once you run an audit.</p>
            </div>
          )}

          {result && (
            <>
              <section className="card">
                <div className="score-row">
                  <div className={`score score-${scoreBand(result.score)}`}>
                    <div className="score-v">{result.score}</div>
                    <div className="score-l">out of 100</div>
                  </div>
                  <div>
                    <Pill tone={result.publishable ? "good" : "bad"}>
                      {result.publishable ? "Publishable" : "Blocked"}
                    </Pill>
                    <p className="hint">
                      {result.word_count} words · {result.issues.length} issues
                    </p>
                  </div>
                </div>
                <div className="gates">
                  {result.gates.map((gate) => (
                    <GateRow key={gate.gate} gate={gate} />
                  ))}
                </div>
              </section>

              <section className="card">
                <h3>Issues</h3>
                {issues.length === 0 ? (
                  <p className="hint">Nothing flagged.</p>
                ) : (
                  issues.map((issue) => (
                    <Issue key={issue.issue_id} issue={issue} />
                  ))
                )}
              </section>
            </>
          )}
      </div>
    </div>
  );
}

/* ── Page titles for the header ──────────────────────────────────────── */

const PAGE_TITLES = {
  dashboard: ["Dashboard", "System overview and quick actions"],
  audit: ["Audit a draft", "Paste content and check it before publishing"],
  corpus: ["All content", "87 documents audited against the registry"],
  history: ["Repeat mistakes", "What keeps coming back across audits"],
  overlap: ["Keyword overlap", "Pages competing for the same search query"],
  hygiene: ["Live pages", "Check published pages against the registry"],
  benchmark: ["Competitors", "Same signals measured on their blogs and ours"],
  reports: ["Ads report", "Week-over-week Meta and Google Ads comparison"],
  social: ["Social report", "Instagram engagement measured against reach"],
  schema: ["Schema generator", "JSON-LD for approved content, gated by audit"],
  registry: ["Registry health", "Stale claims, missing fields, load errors"],
};

/* ── Main ────────────────────────────────────────────────────────────── */

export default function App() {
  const [tab, setTab] = useState("dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => {});
  }, []);

  function navigate(id) {
    setTab(id);
    setSidebarOpen(false);
  }

  const [title, subtitle] = PAGE_TITLES[tab] ?? ["", ""];

  return (
    <div className="layout">
      {/* Mobile toggle */}
      <button
        className="sidebar-toggle"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        aria-label="Toggle navigation"
      >
        {sidebarOpen ? "✕" : "☰"}
      </button>
      <div
        className={`sidebar-overlay ${sidebarOpen ? "open" : ""}`}
        onClick={() => setSidebarOpen(false)}
      />

      {/* Sidebar */}
      <nav className={`sidebar ${sidebarOpen ? "open" : ""}`}>
        <div className="sidebar-brand">
          <h1>County Group</h1>
          <p>Blog Authority System</p>
          <div className="sidebar-health">
            <span className={`health-dot ${health?.status === "ok" ? "ok" : "err"}`} />
            {health?.status === "ok"
              ? `${health.projects_loaded} projects loaded`
              : "Connecting…"}
          </div>
        </div>

        <div className="sidebar-nav" role="tablist" aria-label="Sections">
          {NAV.map((group) => (
            <div className="nav-group" key={group.group}>
              <div className="nav-group-label">{group.group}</div>
              {group.items.map((item) => (
                <button
                  key={item.id}
                  role="tab"
                  className="nav-item"
                  aria-selected={tab === item.id}
                  onClick={() => navigate(item.id)}
                >
                  <span className="nav-icon">{item.icon}</span>
                  {item.label}
                </button>
              ))}
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          v{health?.engine_version ?? "..."} · {health?.storage?.durable ? "Durable" : "Ephemeral"}
        </div>
      </nav>

      {/* Main content */}
      <div className="main">
        <header className="main-header">
          <div>
            <h2>{title}</h2>
            <div className="main-header-sub">{subtitle}</div>
          </div>
        </header>

        <div className="main-content">
          {tab === "dashboard" && <Dashboard onNavigate={navigate} />}
          {tab === "audit" && <AuditPanel />}
          {tab === "corpus" && <Corpus />}
          {tab === "overlap" && <Overlap />}
          {tab === "hygiene" && <Hygiene />}
          {tab === "reports" && <Reports />}
          {tab === "social" && <Social />}
          {tab === "history" && <History />}
          {tab === "benchmark" && <Benchmark />}
          {tab === "schema" && <SchemaGenerator />}
          {tab === "registry" && <RegistryHealth />}
        </div>
      </div>
    </div>
  );
}
