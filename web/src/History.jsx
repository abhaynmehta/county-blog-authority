import { useEffect, useState } from "react";
import { api } from "./api.js";
import { Kpi } from "./Corpus.jsx";

/** Human-readable names for issue categories. */
const CATEGORY_LABELS = {
  image_seo: "Missing or unoptimised images",
  internal_links: "Internal linking",
  ai_readiness: "Thin or unstructured content",
  meta_description: "Meta description",
  meta_title: "Meta title",
  missing_evidence: "Unsourced claims",
  rera_compliance: "RERA compliance",
  spam_signal: "Keyword stuffing or CTA spam",
  prohibited_language: "Prohibited marketing language",
  factual_error: "Factual error",
  infrastructure_status: "Stale infrastructure claim",
  unsupported_claim: "Unsupported claim",
  external_links: "External sources",
  heading_structure: "Heading structure",
  grammar: "Writing quality",
};

function label(category) {
  return CATEGORY_LABELS[category] ?? category.replace(/_/g, " ");
}

/** A share this high is a process gap, not a run of individual mistakes. */
function severityOf(share) {
  if (share >= 75) return "bad";
  if (share >= 40) return "warn";
  return "mut";
}

export default function History() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.history().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="card err">{error}</div>;
  if (!data) return <div className="card empty">Loading history…</div>;

  if (!data.runs) {
    return (
      <div className="card empty">
        <p>{data.message}</p>
      </div>
    );
  }

  return (
    <>
      <div className="kpis">
        <Kpi label="Audits recorded" value={data.runs}
             note={`since ${data.first_run}`} />
        <Kpi label="Documents tracked" value={data.documents} note="unique" />
        <Kpi label="Improved" value={data.improved.length} note="score went up"
             tone={data.improved.length ? "good" : ""} />
        <Kpi label="Came back" value={data.regressions.length}
             note="fixed, then broke again"
             tone={data.regressions.length ? "bad" : "good"} />
      </div>

      <section className="card note">
        <b>What this is.</b> One audit says what is wrong today. This says
        whether the same thing keeps returning — the difference between a blog
        having a problem and an agency having a process gap.
      </section>

      <section className="card">
        <h3>Mistakes that repeat across documents</h3>
        <p className="hint">
          Counted by document, not by occurrence, so one blog audited many
          times cannot look like a pattern. Anything near 100% is a missing
          step in the workflow rather than a series of oversights.
        </p>
        <table className="mini wide">
          <thead>
            <tr>
              <th>Issue</th>
              <th className="num">Documents</th>
              <th className="num">Share</th>
              <th>Examples</th>
            </tr>
          </thead>
          <tbody>
            {data.recurring_mistakes.map((r) => (
              <tr key={r.category}>
                <td>{label(r.category)}</td>
                <td className="num">{r.documents}</td>
                <td className="num">
                  <span className={`pill pill-${severityOf(r.share_pct)}`}>
                    {r.share_pct}%
                  </span>
                </td>
                <td className="hint">{r.examples.slice(0, 2).join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {data.regressions.length > 0 && (
        <section className="card">
          <h3>Fixed, then broken again</h3>
          <p className="hint">
            These were corrected once and later returned. Worth raising: the
            fix was understood and applied, so it is a process problem rather
            than a knowledge one.
          </p>
          {data.regressions.map((r, i) => (
            <div key={i} className="issue issue-critical">
              <div className="issue-head">
                <span className="pill pill-bad">regression</span>
                <h4>{r.slug}: {label(r.category)}</h4>
              </div>
              <p className="meta">
                Fixed on {r.fixed_on}, returned on {r.returned_on}.
              </p>
            </div>
          ))}
        </section>
      )}

      {(data.declined.length > 0 || data.improved.length > 0) && (
        <section className="card">
          <h3>Score movement</h3>
          <table className="mini wide">
            <thead>
              <tr>
                <th>Document</th>
                <th className="num">First</th>
                <th className="num">Latest</th>
                <th className="num">Change</th>
                <th className="num">Runs</th>
              </tr>
            </thead>
            <tbody>
              {[...data.declined, ...data.improved].map((d) => (
                <tr key={d.slug}>
                  <td>{d.slug}</td>
                  <td className="num">{d.first_score}</td>
                  <td className="num">{d.latest_score}</td>
                  <td className={`num ${d.change > 0 ? "good" : "bad"}`}>
                    {d.change > 0 ? "+" : ""}{d.change}
                  </td>
                  <td className="num">{d.runs}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <section className="card">
        <h3>Who owns the open work</h3>
        <table className="mini">
          <tbody>
            {Object.entries(data.owners.by_owner).map(([owner, count]) => (
              <tr key={owner}>
                <td>{owner}</td>
                <td className="num">{count} documents</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
