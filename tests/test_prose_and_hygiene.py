"""Tests for prose-quality checks and live-page hygiene.

Both modules earn their place only if they avoid false positives, so most of
these assert that ordinary correct content is left alone.
"""

import pytest

from search_authority.content_auditor import audit_text
from search_authority.prose import check_prose
from search_authority import hygiene


def prose(text):
    return check_prose(text, [0])


def summaries(issues):
    return " | ".join(i.summary for i in issues)


# ── Prose: the tells ──────────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("Let us delve into the details.", "Delve into"),
    ("This is a tapestry of luxury living.", "Decorative metaphor"),
    ("In today's fast-paced world, buyers want more.", "Filler opener"),
    ("Nestled in the heart of Noida sits the project.", "Nestled in"),
    ("Moreover, the location is strong.", "Essay connector"),
    ("Elevate your lifestyle today.", "Marketing verb"),
    ("It is not only spacious but also well lit.", "Not only"),
    ("Navigating the complex landscape of home buying.", "Navigating the landscape"),
])
def test_each_tell_is_caught(text, expected):
    assert expected in summaries(prose(text))


def test_stacked_adjectives_are_flagged():
    found = prose("Homes that are luxurious, spacious, and premium.")
    assert "Three stacked adjectives" in summaries(found)


def test_double_hyphen_is_flagged():
    assert "Double hyphen" in summaries(prose("The location--truly central--is strong."))



def test_repeated_paragraph_openers_are_flagged():
    text = "\n\n".join(["Located near the metro." for _ in range(5)])
    assert "paragraphs open with" in summaries(prose(text))


# ── Prose: what must NOT be flagged ───────────────────────────────────────

@pytest.mark.parametrize("text", [
    "The project has three bedrooms and two bathrooms.",
    "Carpet area is 888 sq ft. Super area is 1565 sq ft.",
    "Buyers should check the RERA portal before booking.",
    "The well-connected, high-rise development opened in 2026.",
    "Prices start from Rs 2.5 Cr, effective 01 September 2026.",
])
def test_plain_factual_writing_is_left_alone(text):
    assert prose(text) == [], text


def test_a_single_em_dash_is_not_flagged():
    """One em dash is a style choice. A habit of them is the signal."""
    text = "The project — completed in 2026 — sits near the metro. " + ("Filler words here. " * 60)
    assert "Em dash" not in summaries(prose(text))


def test_hyphenated_compounds_are_not_flagged():
    assert prose("A well-connected, ready-to-move, low-density project.") == []


def test_prose_findings_never_fail_a_gate():
    """Style is a quality problem, not a compliance one."""
    text = ("# T\n\nMeta Title: A perfectly adequate title for this article here\n"
            "Meta Description: " + "x" * 130 + "\n\n"
            "Let us delve into the tapestry of it. " * 3 + "\n\n" + ("Words here. " * 300))
    result = audit_text(text)
    prose_issues = [i for i in result.issues if i.issue_id.startswith("CG-PROSE")]
    compliance = next(g for g in result.gates if "RERA" in g.gate_name)
    assert prose_issues
    assert compliance.status.value == "PASS"


# ── Hygiene: table flattening ─────────────────────────────────────────────

def test_flattened_table_headings_are_not_read_as_labels():
    """The commonest live-page shape: a correct table whose headings land
    before the values once the HTML is flattened."""
    text = ("Jade County. Type Super Area Built-up Area Carpet Area "
            "Type A 5094 sq. ft. 4591 sq. ft. 2951 sq. ft.")
    result = audit_text(f"# T\n\n{text}\n")
    assert not any("registered configuration" in i.summary for i in result.issues)


def test_a_genuinely_wrong_figure_still_flags_after_that_fix():
    result = audit_text("# T\n\nJade County has a carpet area of 1850 sq ft.\n")
    assert any("1850" in i.summary for i in result.issues)


def test_is_table_header_detects_preceding_headings():
    text = "Super Area Built-up Area Carpet Area 5094"
    assert hygiene._is_table_header(text, text.index("Carpet Area"))


def test_is_table_header_allows_a_plain_label():
    text = "The carpet area is 888 sq ft"
    assert not hygiene._is_table_header(text, text.index("carpet area"))


# ── Hygiene: page parsing ─────────────────────────────────────────────────

def test_visible_text_strips_scripts_and_styles():
    html = "<html><script>var x=1;</script><style>.a{}</style><p>Real text</p></html>"
    assert hygiene._visible_text(html) == "Real text"


def test_technical_checks_read_the_markup(monkeypatch):
    html = (
        '<html><head><title>A short title</title>'
        '<link rel="canonical" href="https://x.in/">'
        '<meta name="description" content="d">'
        '<script type="application/ld+json">{}</script></head>'
        f'<body><p>{"word " * 200}</p></body></html>'
    )
    monkeypatch.setattr(hygiene, "_fetch", lambda url: (200, html, None))
    page = hygiene.check_page("https://x.in/")

    assert page.has_canonical and page.has_jsonld and page.has_meta_description
    assert page.findings == []


def test_missing_technical_elements_are_reported(monkeypatch):
    html = f'<html><head><title>t</title></head><body><p>{"word " * 200}</p></body></html>'
    monkeypatch.setattr(hygiene, "_fetch", lambda url: (200, html, None))
    kinds = {f["type"] for f in hygiene.check_page("https://x.in/").findings}
    assert {"canonical", "schema", "meta"} <= kinds


def test_a_javascript_rendered_page_is_reported_not_passed(monkeypatch):
    """An empty shell must not be reported as a clean page."""
    monkeypatch.setattr(
        hygiene, "_fetch",
        lambda url: (200, "<html><head><title>t</title></head><body></body></html>", None),
    )
    findings = hygiene.check_page("https://x.in/").findings
    assert any(f["type"] == "rendering" for f in findings)


def test_a_price_without_an_effective_date_is_flagged(monkeypatch):
    html = f'<html><head><title>t</title></head><body><p>Rs 2.5 Cr onwards. {"word " * 200}</p></body></html>'
    monkeypatch.setattr(hygiene, "_fetch", lambda url: (200, html, None))
    assert any(f["type"] == "pricing" for f in hygiene.check_page("https://x.in/").findings)


def test_a_price_with_an_effective_date_is_accepted(monkeypatch):
    html = (f'<html><head><title>t</title></head><body><p>Rs 2.5 Cr onwards, '
            f'w.e.f. 01 Sept 2026, subject to change. {"word " * 200}</p></body></html>')
    monkeypatch.setattr(hygiene, "_fetch", lambda url: (200, html, None))
    assert not any(f["type"] == "pricing" for f in hygiene.check_page("https://x.in/").findings)


def test_an_unreachable_page_records_the_error(monkeypatch):
    monkeypatch.setattr(hygiene, "_fetch", lambda url: (None, "", "dns failure"))
    page = hygiene.check_page("https://x.in/")
    assert not page.ok and page.error == "dns failure"


# ── Typographic quotes ────────────────────────────────────────────────────
#
# Published web content uses curly quotes far more often than straight ones.
# Matching only the straight apostrophe missed the single most recognisable
# tell there is on real competitor pages.

def test_smart_apostrophes_are_matched():
    assert "Filler opener" in summaries(prose("In today’s fast-paced world, buyers want more."))


def test_straight_apostrophes_still_match():
    assert "Filler opener" in summaries(prose("In today's fast-paced world, buyers want more."))


def test_curly_double_quotes_do_not_break_matching():
    text = "“Not only” is it spacious but also well lit."
    assert prose(text) is not None
