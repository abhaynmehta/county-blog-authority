import { useEffect, useMemo, useState } from "react";
import { api, sortIssues, scoreBand } from "./api.js";
import Corpus from "./Corpus.jsx";
import Hygiene from "./Hygiene.jsx";
import Overlap from "./Overlap.jsx";
import Reports from "./Reports.jsx";
import Social from "./Social.jsx";

const TABS = [
  { id: "audit", label: "Audit a draft" },
  { id: "corpus", label: "All content" },
  { id: "overlap", label: "Keyword overlap" },
  { id: "hygiene", label: "Live pages" },
  { id: "reports", label: "Ads report" },
  { id: "social", label: "Social report" },
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

function Issue({ issue }) {
  return (
    <article className={`issue issue-${issue.severity}`}>
      <header className="issue-head">
        <Pill tone={severityTone(issue.severity)}>{issue.severity}</Pill>
        <Pill tone="mut">{issue.owner}</Pill>
        <h4>{issue.summary}</h4>
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

/* ── Main ────────────────────────────────────────────────────────────── */

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

export default function App() {
  const [tab, setTab] = useState("audit");

  return (
    <div className="app">
      <header className="mast">
        <h1>County Content Console</h1>
        <p>
          Deterministic checks against the project registry. The same engine the
          CLI runs, so the browser and the terminal never disagree.
        </p>
      </header>

      <nav className="tabs" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            className="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "audit" && <AuditPanel />}
      {tab === "corpus" && <Corpus />}
      {tab === "overlap" && <Overlap />}
      {tab === "hygiene" && <Hygiene />}
      {tab === "reports" && <Reports />}
      {tab === "social" && <Social />}
    </div>
  );
}
