import { useState } from "react";
import { Kpi } from "./Corpus.jsx";

const BASE = import.meta.env?.VITE_API_BASE ?? "";

function num(value) {
  return typeof value === "number" ? value.toLocaleString() : "—";
}

/** Social post performance. One export, split into periods by post date. */
export default function Social() {
  const [file, setFile] = useState(null);
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);

  async function submit(event) {
    event.preventDefault();
    setStatus("loading");
    setError(null);
    try {
      const body = new FormData();
      body.append("export", file);
      const response = await fetch(`${BASE}/report/social`, { method: "POST", body });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail?.error ?? "Could not read that export");
      }
      setData(payload);
      setStatus("done");
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }

  const current = data?.current_period;
  const previous = data?.previous_period;

  return (
    <>
      <form className="card" onSubmit={submit}>
        <h3>Social performance</h3>
        <p className="hint">
          One export covering both periods — post dates split it automatically.
          Engagement is measured against reach, so a post pushed to more people
          does not look better simply for having more likes.
        </p>

        <label className="lbl" htmlFor="social-export">Post export (CSV)</label>
        <input id="social-export" type="file" accept=".csv,text/csv"
               onChange={(e) => setFile(e.target.files[0] ?? null)} />

        <div className="row">
          <button type="submit" disabled={!file || status === "loading"}>
            {status === "loading" ? "Analysing…" : "Analyse"}
          </button>
          {data && <span className="hint">{data.posts_analysed} posts</span>}
        </div>

        {error && <p role="alert" className="err">{error}</p>}
      </form>

      {data && (
        <>
          <div className="kpis">
            <Kpi label="Posts this period" value={current.posts}
                 note={`${current.from} to ${current.to}`} />
            <Kpi label="Reach" value={num(current.reach)} note="accounts reached" />
            <Kpi
              label="Engagement rate"
              value={`${current.engagement_rate}%`}
              note={`was ${previous.engagement_rate}%`}
              tone={current.engagement_rate >= previous.engagement_rate ? "good" : "bad"}
            />
            <Kpi label="Interactions" value={num(current.engagement)}
                 note="likes, comments, shares, saves" />
          </div>

          <section className="card">
            <h3>Analysis</h3>
            {data.findings.map((f, i) => (
              <div key={i} className={`issue issue-${f.severity}`}>
                <div className="issue-head">
                  <span className={`pill pill-${f.severity === "high" ? "warn" : "mut"}`}>
                    {f.severity}
                  </span>
                  <h4>{f.headline}</h4>
                </div>
                <p className="meta"><b>Why:</b> {f.why}</p>
                <p className="meta"><b>Do:</b> {f.action}</p>
              </div>
            ))}
          </section>

          <section className="card">
            <h3>By format</h3>
            <p className="hint">
              Groups under three posts are omitted: too few to say anything.
            </p>
            <table className="mini wide">
              <thead>
                <tr>
                  <th>Format</th><th className="num">Posts</th>
                  <th className="num">Reach</th><th className="num">Engagement rate</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(data.by_type)
                  .sort((a, b) => b[1].engagement_rate - a[1].engagement_rate)
                  .map(([name, d]) => (
                    <tr key={name}>
                      <td>{name}{d.posts < 3 && <span className="hint"> (small sample)</span>}</td>
                      <td className="num">{d.posts}</td>
                      <td className="num">{num(d.reach)}</td>
                      <td className="num">{d.engagement_rate}%</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </section>

          <section className="card">
            <h3>By project</h3>
            <table className="mini wide">
              <thead>
                <tr>
                  <th>Project</th><th className="num">Posts</th>
                  <th className="num">Reach</th><th className="num">Engagement rate</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(data.by_project)
                  .sort((a, b) => b[1].engagement_rate - a[1].engagement_rate)
                  .map(([name, d]) => (
                    <tr key={name}>
                      <td>{name}{d.posts < 3 && <span className="hint"> (small sample)</span>}</td>
                      <td className="num">{d.posts}</td>
                      <td className="num">{num(d.reach)}</td>
                      <td className="num">{d.engagement_rate}%</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </section>

          <section className="card">
            <h3>Best performing posts</h3>
            <table className="mini wide">
              <thead>
                <tr>
                  <th>Project</th><th>Format</th>
                  <th className="num">Reach</th><th className="num">Rate</th><th>Link</th>
                </tr>
              </thead>
              <tbody>
                {data.top_posts.map((p, i) => (
                  <tr key={i}>
                    <td>{p.project}</td>
                    <td>{p.type}</td>
                    <td className="num">{num(p.reach)}</td>
                    <td className="num good">{p.engagement_rate}%</td>
                    <td>
                      {p.url && (
                        <a href={p.url} target="_blank" rel="noopener noreferrer">open</a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </>
  );
}
