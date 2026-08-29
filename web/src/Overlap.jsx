import { useEffect, useState } from "react";
import { api } from "./api.js";

/** Keyword cannibalisation, with the rebuttal for the usual pushback. */
export default function Overlap() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [severity, setSeverity] = useState("high");

  useEffect(() => {
    api.cannibalization().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="card err">{error}</div>;
  if (!data) return <div className="card empty">Analysing overlaps…</div>;

  const items = data.details.filter((c) => severity === "all" || c.severity === severity);

  return (
    <>
      <section className="card note">
        <b>What this is.</b> Two pages competing for the same query. Google picks
        one — often not the one you want — and both rank worse than a single page
        would. This is <b>not</b> duplicate content, and canonical tags do not fix it.
      </section>

      <section className="card">
        <div className="row">
          <select value={severity} onChange={(e) => setSeverity(e.target.value)}
                  aria-label="Filter by severity">
            <option value="high">High severity</option>
            <option value="medium">Medium</option>
            <option value="all">All</option>
          </select>
          <span className="hint">{items.length} shown of {data.collisions} total</span>
        </div>
      </section>

      {items.map((c, i) => (
        <section className="card" key={i}>
          <h4>{c.pages[0]}</h4>
          <p className="hint">competing with</p>
          <h4>
            {c.pages[1]}{" "}
            <span className={`pill pill-${c.severity === "high" ? "bad" : "warn"}`}>
              {c.severity}
            </span>
          </h4>
          <p className="meta"><b>Shared terms:</b> {c.shared_terms.join(", ")}</p>
          <p className="meta"><b>Fix:</b> {c.recommended_action}</p>
          <div className="rebut">
            <b>If someone says this is already handled:</b>
            <ul>{c.not_fixed_by.map((r, j) => <li key={j}>{r}</li>)}</ul>
          </div>
          <p className="meta"><b>Verify it yourself:</b> {c.how_to_verify}</p>
        </section>
      ))}
    </>
  );
}
