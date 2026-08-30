import { useEffect, useState } from "react";
import { api } from "./api.js";
import { Kpi } from "./Corpus.jsx";

export default function RegistryHealth() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.registryHealth().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="card err">{error}</div>;
  if (!data) return <div className="card empty">Loading registry health…</div>;

  return (
    <>
      <div className="kpis">
        <Kpi label="Claims" value={data.total_claims} note="in registry" />
        <Kpi label="Projects" value={data.total_projects} note="loaded" />
        <Kpi
          label="Stale"
          value={data.stale_count}
          note="past refresh date"
          tone={data.stale_count > 0 ? "bad" : "good"}
        />
        <Kpi
          label="Incomplete"
          value={data.incomplete_count}
          note="missing fields"
          tone={data.incomplete_count > 0 ? "bad" : "good"}
        />
      </div>

      {data.load_errors?.length > 0 && (
        <section className="card">
          <h3 style={{ color: "var(--bad)" }}>Load errors</h3>
          <ul>
            {data.load_errors.map((err, i) => (
              <li key={i} className="err">{err}</li>
            ))}
          </ul>
        </section>
      )}

      {data.stale?.length > 0 && (
        <section className="card">
          <h3>Stale claims</h3>
          <p className="hint">
            These claims have not been re-verified within their refresh window.
            Re-check the source before using them in published content.
          </p>
          <table className="mini wide">
            <thead>
              <tr>
                <th>ID</th>
                <th>Claim</th>
                <th className="num">Days overdue</th>
                <th>Last verified</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {data.stale.map((c) => (
                <tr key={c.claim_id}>
                  <td><code>{c.claim_id}</code></td>
                  <td>{c.claim}</td>
                  <td className="num bad">{c.days_overdue}</td>
                  <td>{c.last_verified ?? "never"}</td>
                  <td>
                    {c.source ? (
                      <a href={c.source} target="_blank" rel="noopener noreferrer">
                        source
                      </a>
                    ) : (
                      <span className="hint">none</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {data.incomplete?.length > 0 && (
        <section className="card">
          <h3>Incomplete claims</h3>
          <p className="hint">
            These claims are missing required fields. The audit engine may not be
            able to enforce them properly until the gaps are filled.
          </p>
          <table className="mini wide">
            <thead>
              <tr>
                <th>ID</th>
                <th>Claim</th>
                <th>Missing</th>
                <th>Note</th>
              </tr>
            </thead>
            <tbody>
              {data.incomplete.map((c) => (
                <tr key={c.claim_id}>
                  <td><code>{c.claim_id}</code></td>
                  <td>{c.claim}</td>
                  <td>
                    {c.missing?.map((f) => (
                      <span key={f} className="pill pill-warn" style={{ marginRight: 4 }}>
                        {f}
                      </span>
                    ))}
                  </td>
                  <td className="hint">{c.note ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {data.stale_count === 0 && data.incomplete_count === 0 && (
        <section className="card">
          <p className="good" style={{ textAlign: "center", padding: 20 }}>
            All {data.total_claims} claims are complete and within their refresh window.
          </p>
        </section>
      )}

      <section className="card">
        <h3>Prohibited phrases</h3>
        <p className="hint">
          {data.prohibited_phrases} phrases are blocked across all content.
          These are enforced automatically during audit.
        </p>
      </section>
    </>
  );
}
