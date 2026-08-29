import { Fragment, useEffect, useState } from "react";
import { api, scoreBand } from "./api.js";

/** All 87 audited documents, filterable. */
export default function Corpus() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [open, setOpen] = useState(null);

  useEffect(() => {
    api.corpus().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="card err">{error}</div>;
  if (!data) return <div className="card empty">Loading corpus…</div>;

  const rows = data.documents.filter((d) => {
    if (query && !`${d.title} ${d.slug}`.toLowerCase().includes(query.toLowerCase()))
      return false;
    if (filter === "blocked") return !d.publishable;
    if (filter === "critical") return d.critical > 0;
    if (filter === "publishable") return d.publishable;
    return true;
  });

  const s = data.summary;

  return (
    <>
      <div className="kpis">
        <Kpi label="Documents" value={s.total} note="audited" />
        <Kpi label="Publishable" value={s.publishable} note={`${Math.round((s.publishable / s.total) * 100)}%`} />
        <Kpi label="Average score" value={s.avg_score} note="target 85+" />
        <Kpi label="With criticals" value={s.critical_docs} note="cannot publish" tone={s.critical_docs ? "bad" : "good"} />
      </div>

      <section className="card">
        <div className="row">
          <input
            type="search" value={query} aria-label="Search documents"
            onChange={(e) => setQuery(e.target.value)} placeholder="Search…"
          />
          <select value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Filter">
            <option value="all">All</option>
            <option value="blocked">Not publishable</option>
            <option value="critical">Has criticals</option>
            <option value="publishable">Publishable</option>
          </select>
          <span className="hint">{rows.length} of {data.documents.length}</span>
        </div>

        <table className="mini wide">
          <thead>
            <tr><th>Document</th><th className="num">Score</th><th className="num">Issues</th><th>Status</th></tr>
          </thead>
          <tbody>
            {rows.map((d) => (
              <Fragment key={d.slug}>
                <tr className="clickable"
                    onClick={() => setOpen(open === d.slug ? null : d.slug)}>
                  <td>{d.title}<div className="hint">{d.slug}</div></td>
                  <td className="num">
                    <span className={`pill pill-${scoreBand(d.score) === "good" ? "good" : scoreBand(d.score) === "fair" ? "warn" : "bad"}`}>
                      {d.score ?? "—"}
                    </span>
                  </td>
                  <td className="num">{d.issues}</td>
                  <td>
                    <span className={`pill pill-${d.publishable ? "good" : "bad"}`}>
                      {d.publishable ? "Publishable" : "Blocked"}
                    </span>
                  </td>
                </tr>
                {open === d.slug && (
                  <tr>
                    <td colSpan={4} className="detail">
                      {d.issue_list.length === 0 ? (
                        <p className="hint">No issues recorded.</p>
                      ) : (
                        d.issue_list.map((i) => (
                          <div key={i.id} className={`issue issue-${i.severity}`}>
                            <div className="issue-head">
                              <span className={`pill pill-${i.severity === "critical" ? "bad" : i.severity === "high" ? "warn" : "mut"}`}>
                                {i.severity}
                              </span>
                              <span className="pill pill-mut">{i.owner}</span>
                              <h4>{i.summary}</h4>
                            </div>
                            {i.claim && <blockquote className="quote">{i.claim}</blockquote>}
                            <p className="meta"><b>Fix:</b> {i.action}</p>
                          </div>
                        ))
                      )}
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}

export function Kpi({ label, value, note, tone }) {
  return (
    <div className="kpi">
      <div className="kpi-l">{label}</div>
      <div className={`kpi-v ${tone ?? ""}`}>{value}</div>
      <div className="kpi-n">{note}</div>
    </div>
  );
}
