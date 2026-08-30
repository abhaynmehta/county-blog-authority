import { useState } from "react";
import { api } from "./api.js";

export default function SchemaGenerator() {
  const [content, setContent] = useState("");
  const [slug, setSlug] = useState("untitled");
  const [datePublished, setDatePublished] = useState("");
  const [dateModified, setDateModified] = useState("");
  const [canonicalUrl, setCanonicalUrl] = useState("");
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  async function generate(event) {
    event.preventDefault();
    setStatus("loading");
    setError(null);
    setResult(null);
    try {
      const data = await api.schema(content, slug, datePublished, dateModified, canonicalUrl);
      setResult(data);
      setStatus("done");
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }

  function copyToClipboard() {
    if (!result?.jsonld) return;
    navigator.clipboard.writeText(result.jsonld).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  const wordCount = content.trim() ? content.trim().split(/\s+/).length : 0;

  return (
    <>
      <section className="card note">
        <b>How this works.</b> Paste the final, approved blog content below. The
        engine audits it first — if it fails any publication gate, no schema is
        emitted. This prevents structured data from being deployed for content
        that isn't fit to publish. The output is a JSON-LD block ready for AGO
        to paste into the CMS.
      </section>

      <div className="cols">
        <div className="col">
          <form className="card" onSubmit={generate}>
            <label className="lbl" htmlFor="schema-slug">Slug</label>
            <input
              id="schema-slug"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              placeholder="clove-county-amenities"
            />

            <label className="lbl" htmlFor="schema-date">
              Publication date (required)
            </label>
            <input
              id="schema-date"
              type="date"
              value={datePublished}
              onChange={(e) => setDatePublished(e.target.value)}
            />

            <label className="lbl" htmlFor="schema-modified">
              Date modified (optional)
            </label>
            <input
              id="schema-modified"
              type="date"
              value={dateModified}
              onChange={(e) => setDateModified(e.target.value)}
            />

            <label className="lbl" htmlFor="schema-url">
              Canonical URL (optional)
            </label>
            <input
              id="schema-url"
              value={canonicalUrl}
              onChange={(e) => setCanonicalUrl(e.target.value)}
              placeholder="https://www.countygroup.in/blog/clove-county-amenities"
            />

            <label className="lbl" htmlFor="schema-content">Blog content</label>
            <textarea
              id="schema-content"
              rows={14}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Paste the approved blog content here…"
            />

            <div className="row">
              <button
                type="submit"
                disabled={status === "loading" || !content.trim() || !datePublished}
              >
                {status === "loading" ? "Generating…" : "Generate schema"}
              </button>
              <span className="hint">{wordCount} words</span>
            </div>

            {error && <p role="alert" className="err">{error}</p>}
          </form>
        </div>

        <div className="col">
          {!result && status !== "loading" && (
            <div className="card empty">
              <p>JSON-LD output appears here once the content passes all gates.</p>
            </div>
          )}

          {result && (
            <section className="card">
              <div className="row" style={{ marginBottom: 12 }}>
                <h3 style={{ margin: 0 }}>JSON-LD</h3>
                <button type="button" onClick={copyToClipboard} className="btn-sm">
                  {copied ? "Copied" : "Copy to clipboard"}
                </button>
              </div>
              <p className="hint" style={{ marginBottom: 8 }}>
                Canonical: {result.canonical_url}
              </p>
              <pre className="schema-output">{result.jsonld}</pre>
            </section>
          )}
        </div>
      </div>
    </>
  );
}
