import { useState } from "react";
import { api } from "./api.js";
import { Kpi } from "./Corpus.jsx";

const LABELS = {
  word_count: "Words per page",
  headings: "Headings",
  h2_count: "Section headings (H2)",
  external_links: "Links to outside sources",
  internal_links: "Internal links",
  images: "Images",
  images_with_alt: "Images with alt text",
  tables: "Tables",
  lists: "Lists",
  faq_present: "Has an FAQ",
  has_author: "Shows an author",
  has_date: "Shows a date",
};

const ORDER = [
  "word_count", "h2_count", "external_links", "internal_links",
  "images", "images_with_alt", "tables", "lists", "faq_present",
  "has_author", "has_date",
];

function show(value) {
  if (value === null || value === undefined) return "—";
  if (value === 0 || value === 1) return value === 1 ? "yes" : "no";
  return value;
}

export default function Benchmark() {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);

  async function run() {
    setStatus("loading");
    setError(null);
    try {
      setData(await api.competitors());
      setStatus("done");
    } catch (e) {
      setError(e.message);
      setStatus("error");
    }
  }

  return (
    <>
      <section className="card">
        <h3>Competitor benchmark</h3>
        <p className="hint">
          Fetches their blog articles and ours, and measures the same signals on
          both. Competitors are measured, never treated as sources of fact —
          nothing here feeds the project registry. Fetching respects robots.txt.
        </p>
        <div className="row">
          <button onClick={run} disabled={status === "loading"}>
            {status === "loading" ? "Fetching blogs…" : "Run benchmark"}
          </button>
          {data && <span className="hint">Last run {data.checked_at}</span>}
        </div>
        {error && <p role="alert" className="err">{error}</p>}
      </section>

      {data && (
        <>
          <div className="kpis">
            <Kpi label="Our pages" value={data.own_pages.length} note="articles read" />
            <Kpi label="Their pages" value={data.competitor_pages.length}
                 note="articles read" />
            <Kpi label="Compared against" value={data.compared_against.length}
                 note={data.compared_against.join(", ") || "none"} />
            <Kpi label="Not reachable" value={data.not_compared.length}
                 note="see below"
                 tone={data.not_compared.length ? "bad" : "good"} />
          </div>

          {data.not_compared.length > 0 && (
            <section className="card note">
              <b>This is not a market comparison.</b> Only{" "}
              {data.compared_against.join(", ") || "no competitor"} could be
              fetched. Treat the numbers below as one rival, not the field.
              <ul style={{ margin: "8px 0 0 18px", fontSize: "12.5px" }}>
                {data.not_compared.map((c) => (
                  <li key={c.name}>
                    <b>{c.name}</b> — {c.reason.replace(/_/g, " ")}
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="card">
            <h3>What to do</h3>
            {data.findings.map((f, i) => (
              <div key={i} className={`issue issue-${f.severity}`}>
                <div className="issue-head">
                  <span className={`pill pill-${
                    f.severity === "high" ? "warn"
                      : f.severity === "good" ? "good" : "mut"}`}>
                    {f.severity}
                  </span>
                  <h4>{f.headline}</h4>
                </div>
                <p className="meta"><b>Why it matters:</b> {f.why}</p>
                <p className="meta"><b>Do:</b> {f.action}</p>
              </div>
            ))}
          </section>

          <section className="card">
            <h3>Signal by signal</h3>
            <p className="hint">
              Median across the pages read, so one unusually long article cannot
              skew the picture.
            </p>
            <table className="mini wide">
              <thead>
                <tr>
                  <th>Signal</th>
                  <th className="num">Ours</th>
                  <th className="num">Theirs</th>
                  <th className="num">Difference</th>
                </tr>
              </thead>
              <tbody>
                {ORDER.filter((k) => data.comparison[k]).map((key) => {
                  const row = data.comparison[key];
                  const ahead = row.gap != null && row.gap > 0;
                  return (
                    <tr key={key}>
                      <td>{LABELS[key] ?? key}</td>
                      <td className="num">{show(row.ours)}</td>
                      <td className="num">{show(row.theirs)}</td>
                      <td className={`num ${row.gap == null ? "" : ahead ? "good" : "bad"}`}>
                        {row.gap == null ? "—" : `${ahead ? "+" : ""}${row.gap}`}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>

          {data.by_competitor && (
            <section className="card">
              <h3>Competitor by competitor</h3>
              <p className="hint">
                A median across rivals hides who is driving a gap. One of them
                citing heavily can make the field look stronger than it is.
              </p>
              <table className="mini wide">
                <thead>
                  <tr>
                    <th>Site</th>
                    <th className="num">Pages</th>
                    <th className="num">Words</th>
                    <th className="num">H2s</th>
                    <th className="num">Outside links</th>
                    <th className="num">Tables</th>
                    <th className="num">Writing tells</th>
                  </tr>
                </thead>
                <tbody>
                  <tr style={{ fontWeight: 700 }}>
                    <td>County Group (us)</td>
                    <td className="num">{data.own_pages.length}</td>
                    <td className="num">{show(data.comparison.word_count.ours)}</td>
                    <td className="num">{show(data.comparison.h2_count.ours)}</td>
                    <td className="num">{show(data.comparison.external_links.ours)}</td>
                    <td className="num">{show(data.comparison.tables.ours)}</td>
                    <td className="num">{show(data.comparison.prose_tells?.ours)}</td>
                  </tr>
                  {Object.entries(data.by_competitor).map(([name, d]) => (
                    <tr key={name}>
                      <td>{name}</td>
                      <td className="num">{d.pages}</td>
                      <td className="num">{show(d.word_count)}</td>
                      <td className="num">{show(d.h2_count)}</td>
                      <td className="num">{show(d.external_links)}</td>
                      <td className="num">{show(d.tables)}</td>
                      <td className="num">{show(d.prose_tells)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="hint" style={{ marginTop: "8px" }}>
                Writing tells count machine-written or boilerplate phrasing.
                Lower is better, and it is the one column where a high number
                is a competitor's weakness rather than their strength.
              </p>
            </section>
          )}

          <section className="card">
            <h3>Structured data</h3>
            <div className="cols">
              <div>
                <p className="meta"><b>We deploy</b></p>
                <p className="hint">
                  {data.comparison.schema_types.ours.join(", ") || "none"}
                </p>
              </div>
              <div>
                <p className="meta"><b>They deploy</b></p>
                <p className="hint">
                  {data.comparison.schema_types.theirs.join(", ") || "none"}
                </p>
              </div>
            </div>
            {data.comparison.schema_types.they_have_we_do_not.length > 0 && (
              <p className="meta" style={{ marginTop: "10px" }}>
                <b>Missing on our side:</b>{" "}
                {data.comparison.schema_types.they_have_we_do_not.join(", ")}
              </p>
            )}
          </section>
        </>
      )}
    </>
  );
}
