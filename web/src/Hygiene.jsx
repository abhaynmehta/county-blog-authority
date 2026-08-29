import { useState } from "react";
import { api } from "./api.js";
import { Kpi } from "./Corpus.jsx";

/** Live-page checks. Run on demand — it fetches around twenty pages. */
export default function Hygiene() {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);

  async function run() {
    setStatus("loading");
    setError(null);
    try {
      setData(await api.hygiene());
      setStatus("done");
    } catch (e) {
      setError(e.message);
      setStatus("error");
    }
  }

  return (
    <>
      <section className="card">
        <h3>Digital hygiene</h3>
        <p className="hint">
          Fetches every live County page and checks it against the registry.
          Areas and unit plans must match exactly, since unit plans do not
          change. Prices may change but must carry an effective date.
        </p>
        <div className="row">
          <button onClick={run} disabled={status === "loading"}>
            {status === "loading" ? "Checking live pages…" : "Run check"}
          </button>
          {data && <span className="hint">Last run {data.checked_at}</span>}
        </div>
        {error && (
          <p role="alert" className="err">
            {error}
          </p>
        )}
      </section>

      {data && (
        <>
          <div className="kpis">
            <Kpi label="Pages checked" value={data.pages_checked} note="live URLs" />
            <Kpi
              label="Unreachable"
              value={data.unreachable}
              note="failed to load"
              tone={data.unreachable ? "bad" : "good"}
            />
            <Kpi
              label="Critical"
              value={data.by_severity.critical}
              note="wrong facts live"
              tone={data.by_severity.critical ? "bad" : "good"}
            />
            <Kpi label="Total findings" value={data.total_findings} note="all pages" />
          </div>

          <section className="card">
            <h3>Findings</h3>
            {data.findings.length === 0 ? (
              <p className="hint">Nothing found.</p>
            ) : (
              data.findings.map((f, i) => (
                <div key={i} className={`issue issue-${f.severity}`}>
                  <div className="issue-head">
                    <span
                      className={`pill pill-${
                        f.severity === "critical"
                          ? "bad"
                          : f.severity === "high"
                            ? "warn"
                            : "mut"
                      }`}
                    >
                      {f.severity}
                    </span>
                    <span className="pill pill-mut">{f.owner}</span>
                    <h4>{f.detail}</h4>
                  </div>
                  <p className="meta">
                    <b>Page:</b> {f.url.replace("https://www.", "")}
                  </p>
                  <p className="meta">
                    <b>Fix:</b> {f.fix}
                  </p>
                </div>
              ))
            )}
          </section>
        </>
      )}
    </>
  );
}
