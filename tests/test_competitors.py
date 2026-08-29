"""Tests for competitor benchmarking.

The risk here is producing a confident comparison from a misread page, so
most of these cover parsing edge cases that would silently skew a signal.
"""

import pytest

from search_authority import competitors
from search_authority.competitors import (
    PageProfile, _compare, _findings, _resolution_base, _schema_types,
    _visible_text, benchmark, discover_articles, profile_page,
)


def page(**kwargs) -> PageProfile:
    defaults = dict(url="https://x/1", status=200, word_count=1000)
    return PageProfile(**{**defaults, **kwargs})


@pytest.fixture
def allow_all(monkeypatch):
    monkeypatch.setattr(competitors, "_robots_allows", lambda url: (True, None))


# ── robots.txt ────────────────────────────────────────────────────────────

def test_a_disallowed_page_is_not_fetched(monkeypatch):
    monkeypatch.setattr(competitors, "_robots_allows", lambda url: (False, None))
    called = []
    monkeypatch.setattr(competitors, "_fetch",
                        lambda url: called.append(url) or (200, "<html></html>", None))

    result = profile_page("https://rival.example/blog/post")

    assert called == []
    assert result.error == "disallowed by robots.txt"


def test_an_unreachable_robots_file_proceeds_but_says_so(monkeypatch, allow_all):
    monkeypatch.setattr(competitors, "_robots_allows",
                        lambda url: (True, "robots.txt unreachable; proceeded"))
    monkeypatch.setattr(competitors, "_fetch",
                        lambda url: (200, "<html><body>word</body></html>", None))
    assert "unreachable" in profile_page("https://x/1").error


# ── Base tag ──────────────────────────────────────────────────────────────

def test_a_base_tag_governs_link_resolution():
    """countygroup.in sets one. Ignoring it turned every relative blog link
    into a 404 that was not actually broken."""
    html = '<html><head><base href="https://x.in/" /></head></html>'
    assert _resolution_base(html, "https://x.in/blog/") == "https://x.in/"


def test_without_a_base_tag_the_document_url_is_used():
    assert _resolution_base("<html></html>", "https://x.in/blog/") == "https://x.in/blog/"


def test_discovery_honours_the_base_tag(monkeypatch, allow_all):
    html = ('<html><head><base href="https://x.in/" /></head><body>'
            '<a href="blog/first-post">One</a></body></html>')
    monkeypatch.setattr(competitors, "_fetch", lambda url: (200, html, None))
    assert discover_articles("https://x.in/blog/") == ["https://x.in/blog/first-post"]


# ── Discovery ─────────────────────────────────────────────────────────────

def test_discovery_skips_pagination_and_category_listings(monkeypatch, allow_all):
    html = ('<a href="/blog/real-post">a</a>'
            '<a href="/blog/page/2">b</a>'
            '<a href="/blog/category/news">c</a>'
            '<a href="/blog/tag/noida">d</a>')
    monkeypatch.setattr(competitors, "_fetch", lambda url: (200, html, None))
    assert discover_articles("https://x.in/blog") == ["https://x.in/blog/real-post"]


def test_discovery_stays_on_the_same_domain(monkeypatch, allow_all):
    html = '<a href="/blog/ours">a</a><a href="https://other.com/blog/theirs">b</a>'
    monkeypatch.setattr(competitors, "_fetch", lambda url: (200, html, None))
    assert discover_articles("https://x.in/blog") == ["https://x.in/blog/ours"]


def test_discovery_does_not_return_the_index_itself(monkeypatch, allow_all):
    monkeypatch.setattr(competitors, "_fetch",
                        lambda url: (200, '<a href="/blog/">home</a>', None))
    assert discover_articles("https://x.in/blog") == []


def test_discovery_respects_the_limit(monkeypatch, allow_all):
    html = "".join(f'<a href="/blog/post-{i}">x</a>' for i in range(20))
    monkeypatch.setattr(competitors, "_fetch", lambda url: (200, html, None))
    assert len(discover_articles("https://x.in/blog", limit=3)) == 3


# ── Parsing ───────────────────────────────────────────────────────────────

def test_navigation_and_footers_are_excluded_from_word_count():
    """Counting the nav would make every page on a site look the same length."""
    html = ("<nav>menu links here</nav><body><p>real body text</p></body>"
            "<footer>footer text</footer>")
    assert _visible_text(html) == "real body text"


def test_schema_types_are_read_from_json_ld():
    html = ('<script type="application/ld+json">'
            '{"@type":"BlogPosting","author":{"@type":"Person"}}</script>')
    assert _schema_types(html) == ["BlogPosting", "Person"]


def test_schema_types_survive_malformed_json():
    """Broken JSON-LD is common and should not hide what a page declares."""
    html = ('<script type="application/ld+json">'
            '{"@type":"FAQPage", trailing garbage</script>')
    assert "FAQPage" in _schema_types(html)


def test_a_list_of_types_is_expanded():
    html = ('<script type="application/ld+json">'
            '{"@type":["WebPage","Article"]}</script>')
    assert _schema_types(html) == ["Article", "WebPage"]


def test_images_are_counted_separately_from_described_images(monkeypatch, allow_all):
    html = ('<body><img src="a.jpg" alt="described"><img src="b.jpg">'
            '<img src="c.jpg" alt=""></body>')
    monkeypatch.setattr(competitors, "_fetch", lambda url: (200, html, None))
    result = profile_page("https://x/1")
    assert result.images == 3 and result.images_with_alt == 1


def test_internal_and_external_links_are_distinguished(monkeypatch, allow_all):
    html = ('<a href="/about">a</a><a href="https://x.in/more">b</a>'
            '<a href="https://anarock.com/report">c</a>'
            '<a href="#top">d</a><a href="mailto:a@b.c">e</a>')
    monkeypatch.setattr(competitors, "_fetch", lambda url: (200, html, None))
    result = profile_page("https://x.in/blog/post", own_domains=("x.in",))
    assert result.internal_links == 2
    assert result.external_links == 1


# ── Comparison ────────────────────────────────────────────────────────────

def test_comparison_uses_the_median_not_the_mean():
    """One long outlier should not make their typical page look twice as long."""
    ours = [page(word_count=1000), page(word_count=1000), page(word_count=1000)]
    theirs = [page(word_count=1000), page(word_count=1000), page(word_count=9000)]
    assert _compare(ours, theirs)["word_count"]["theirs"] == 1000.0


def test_schema_comparison_names_what_each_side_is_missing():
    ours = [page(schema_types=["BlogPosting", "FAQPage"])]
    theirs = [page(schema_types=["BlogPosting", "BreadcrumbList"])]
    schema = _compare(ours, theirs)["schema_types"]
    assert schema["they_have_we_do_not"] == ["BreadcrumbList"]
    assert schema["we_have_they_do_not"] == ["FAQPage"]


def test_a_shortfall_becomes_a_finding():
    ours = [page(external_links=5)]
    theirs = [page(external_links=40)]
    assert any("cite more outside sources" in f["headline"] for f in _findings(ours, theirs))


def test_a_small_difference_is_not_reported():
    """Under 20% is noise, not a gap worth acting on."""
    ours = [page(external_links=38)]
    theirs = [page(external_links=40)]
    assert not any("outside sources" in f["headline"] for f in _findings(ours, theirs))


def test_being_ahead_is_reported_too():
    ours = [page(word_count=3000, external_links=40)]
    theirs = [page(word_count=1000, external_links=40)]
    assert any(f["severity"] == "good" for f in _findings(ours, theirs))


def test_no_reachable_pages_says_so_rather_than_comparing_nothing():
    findings = _findings([], [page()])
    assert findings[0]["severity"] == "high"
    assert "Not enough reachable pages" in findings[0]["headline"]


# ── End to end ────────────────────────────────────────────────────────────

def test_benchmark_reports_unreachable_pages(monkeypatch, allow_all):
    def fetch(url):
        if "broken" in url:
            return 404, "", None
        return 200, "<body><p>" + ("word " * 300) + "</p></body>", None

    monkeypatch.setattr(competitors, "_fetch", fetch)
    result = benchmark(["https://r.com/broken"], ["https://x.in/good"])
    assert result["unreachable"] == ["https://r.com/broken"]


# ── Prose quality ─────────────────────────────────────────────────────────
#
# Writing quality is a universal measure, so unlike the County registry
# checks it is fair to apply to a competitor's content.

def test_writing_tells_are_counted_on_a_competitor_page(monkeypatch, allow_all):
    html = ("<body><p>In today's fast-paced world, let us delve into the "
            "tapestry of luxury living here.</p></body>")
    monkeypatch.setattr(competitors, "_fetch", lambda url: (200, html, None))
    result = profile_page("https://rival.example/post")
    assert result.prose_tells >= 2
    assert result.prose_examples


def test_clean_writing_records_no_tells(monkeypatch, allow_all):
    html = "<body><p>" + ("The project has three bedrooms and two bathrooms. " * 20) + "</p></body>"
    monkeypatch.setattr(competitors, "_fetch", lambda url: (200, html, None))
    assert profile_page("https://rival.example/post").prose_tells == 0
