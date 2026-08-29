import { useState } from "react";
import { Kpi } from "./Corpus.jsx";

const BASE = import.meta.env?.VITE_API_BASE ?? "";

/** Metrics shown in the summary strip, in reading order. */
const HEADLINE_METRICS = [
  ["spend", "Spend", true],
  ["leads", "Leads", false],
  ["cpl", "Cost per lead", true],
  ["ctr", "Click-through", false],
];

function pct(value) {
  if (value == null) return "—";
  return `${value > 0 ? "+" : ""}${value}%`;
}

/** A rise is good for leads and CTR, bad for spend and CPL. */
function tone(metric, change) {
  if (change == null) return "";
  const lowerIsBetter = metric === "cpl" || metric === "cpc" || metric === "spend";
  const improving = lowerIsBetter ? change < 0 : change > 0;
  return improving ? "good" : "bad";
}

export default function Reports() {
  const [files, setFiles] = useState({ previous: null, current: null, leads: null });
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);

  function pick(which) {
    return (event) => setFiles((f) => ({ ...f, [which]: event.target.files[0] ?? null }));
  }

  async function submit(event) {
    event.preventDefault();
    setStatus("loading");
    setError(null);
    try {
      const body = new FormData();
      body.append("previous", files.previous);
      body.append("current", files.current);
      if (files.leads) body.append("leads", files.leads);

      const response = await fetch(`${BASE}/report/weekly`, { method: "POST", body });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(
          typeof payload.detail === "string"
            ? payload.detail
            : (payload.detail?.message ?? "Could not read those exports"),
        );
      }
      setData(payload);
      setStatus("done");
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }

  const ready = files.previous && files.current;

  return (
    <>
      <form className="card" onSubmit={submit}>
        <h3>Weekly performance report</h3>
        <p className="hint">
          Export the same report for both periods from Meta, Google Ads, GA4 or
          Search Console. Column names are detected automatically, so no
          reformatting is needed. Lead statuses are optional but change how the
          numbers should be read.
        </p>

        <label className="lbl" htmlFor="previous">Last period export (CSV)</label>
        <input id="previous" type="file" accept=".csv,text/csv" onChange={pick("previous")} />

        <label className="lbl" htmlFor="current">This period export (CSV)</label>
        <input id="current" type="file" accept=".csv,text/csv" onChange={pick("current")} />

        <label className="lbl" htmlFor="leads">Lead statuses (CSV, optional)</label>
        <input id="leads" type="file" accept=".csv,text/csv" onChange={pick("leads")} />

        <div className="row">
          <button type="submit" disabled={!ready || status === "loading"}>
            {status === "loading" ? "Analysing…" : "Analyse"}
          </button>
          {!ready && <span className="hint">Both period exports are required</span>}
        </div>

        {error && <p role="alert" className="err">{error}</p>}
      </form>

      {data && (
        <>
          <div className="kpis">
            {HEADLINE_METRICS.map(([key, label]) => {
              const metric = data.totals?.[key];
              if (!metric) return null;
              return (
                <Kpi
                  key={key}
                  label={label}
                  value={pct(metric.change_pct)}
                  note={`${metric.previous} → ${metric.current}`}
                  tone={tone(key, metric.change_pct)}
                />
              );
            })}
          </div>

          <section className="card">
            <h3>Analysis</h3>
            {data.findings.map((f, i) => (
              <div key={i} className={`issue issue-${f.severity}`}>
                <div className="issue-head">
                  <span
                    className={`pill pill-${
                      f.severity === "critical"
                        ? "bad"
                        : f.severity === "high"
                          ? "warn"
                          : f.severity === "good"
                            ? "good"
                            : "mut"
                    }`}
                  >
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
            <h3>Per campaign</h3>
            <table className="mini wide">
              <thead>
                <tr>
                  <th>Campaign</th>
                  <th className="num">Leads</th>
                  <th className="num">Spend</th>
                  <th className="num">CPL</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.campaigns.map((c) => (
                  <tr key={c.name}>
                    <td>{c.name}</td>
                    <td className={`num ${tone("leads", c.change.leads)}`}>{pct(c.change.leads)}</td>
                    <td className="num">{pct(c.change.spend)}</td>
                    <td className={`num ${tone("cpl", c.change.cpl)}`}>{pct(c.change.cpl)}</td>
                    <td>
                      <span className={`pill pill-${c.status === "stopped" ? "bad" : c.status === "new" ? "info" : "mut"}`}>
                        {c.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="card">
            <h3>Columns matched</h3>
            <p className="hint">
              Check these are right. A mis-matched column produces confident nonsense.
            </p>
            <table className="mini">
              <tbody>
                {Object.entries(data.columns_used ?? {}).map(([field, column]) => (
                  <tr key={field}>
                    <td>{field}</td>
                    <td>{column ?? <span className="hint">not found</span>}</td>
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
