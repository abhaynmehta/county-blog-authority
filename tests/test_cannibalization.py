"""Tests for keyword cannibalisation detection.

The distinction this module has to hold onto: cannibalisation is not
duplicate content, and the fixes are different. Tests here cover both the
detection and the guidance that goes with it.
"""

import pytest

from search_authority.cannibalization import (
    Collision, extract_keywords, find_collisions, recommend_fix, analyse_corpus,
)


def page(slug, text="", title=None, h1=None):
    return extract_keywords(text, slug=slug, title=title, h1=h1)


# --- Keyword extraction ---

def test_title_phrases_become_primary_terms():
    p = page("a", title="Luxury Flats in Noida Sector 151")
    assert any("flats" in t for t in p.primary_terms)


def test_sector_numbers_are_captured():
    p = page("a", title="Clove County Sector 151 Noida")
    assert "sector 151" in p.primary_terms


def test_stopwords_do_not_become_terms():
    p = page("a", title="The Best of the Year")
    assert not any(t in {"the best", "of the"} for t in p.primary_terms)


def test_phrases_without_intent_markers_are_ignored():
    """'monsoon gardening tips' is not a property query."""
    p = page("a", title="Monsoon Gardening Tips For Balconies")
    assert p.primary_terms == []


def test_repeated_body_phrases_become_secondary_terms():
    text = ("luxury flats in noida " * 5) + "some other words here"
    p = page("a", text=text)
    assert any("luxury flats" in t for t in p.body_terms)


def test_a_phrase_mentioned_once_is_not_a_target():
    p = page("a", text="We once mentioned luxury flats in passing here.")
    assert not any("luxury flats" in t for t in p.body_terms)


# --- Collision detection ---

def test_two_pages_with_the_same_title_target_collide_at_high_severity():
    a = page("a", title="Luxury Flats in Noida Sector 151")
    b = page("b", title="Luxury Flats Noida Sector 151 Guide")
    collisions = find_collisions([a, b])
    assert collisions and collisions[0].severity == "high"


def test_pages_targeting_different_queries_do_not_collide():
    a = page("a", title="Luxury Flats in Gurugram Sector 88")
    b = page("b", title="Monsoon Gardening Tips For Balconies")
    assert find_collisions([a, b]) == []


def test_body_only_overlap_is_ranked_below_title_overlap():
    shared = "luxury flats noida " * 5
    a = page("a", title="Monsoon Gardening Tips", text=shared)
    b = page("b", title="Balcony Plants Guide", text=shared)
    collisions = find_collisions([a, b])
    assert all(c.severity in ("low", "medium") for c in collisions)


def test_collisions_are_ordered_worst_first():
    a = page("a", title="Luxury Flats in Noida Sector 151")
    b = page("b", title="Luxury Flats Noida Sector 151 Guide")
    weak = "premium property investment " * 4
    c = page("c", title="Gardening Tips", text=weak)
    d = page("d", title="Plant Care", text=weak)
    severities = [x.severity for x in find_collisions([a, b, c, d])]
    assert severities == sorted(severities, key=lambda s: {"high": 0, "medium": 1, "low": 2}[s])


def test_a_single_page_cannot_collide_with_itself():
    assert find_collisions([page("a", title="Luxury Flats in Noida")]) == []


def test_min_shared_threshold_is_respected():
    a = page("a", title="Luxury Flats Noida")
    b = page("b", title="Luxury Flats Gurugram")
    assert find_collisions([a, b], min_shared=99) == []


# --- Guidance ---

def test_high_severity_recommends_consolidation():
    fix = recommend_fix(Collision("a", "b", ["luxury flats"], ["luxury flats"], "high"))
    assert "consolidate" in fix["recommended_action"].lower()


def test_medium_severity_recommends_differentiation():
    fix = recommend_fix(Collision("a", "b", ["luxury flats"], [], "medium"))
    assert "differentiate" in fix["recommended_action"].lower()


def test_low_severity_recommends_verifying_before_acting():
    fix = recommend_fix(Collision("a", "b", ["luxury flats"], [], "low"))
    assert "monitor" in fix["recommended_action"].lower()


def test_guidance_states_that_canonicals_do_not_fix_cannibalisation():
    """The standard agency rebuttal. The report must pre-empt it."""
    fix = recommend_fix(Collision("a", "b", ["x", "y"], ["x"], "high"))
    canonical = " ".join(fix["not_fixed_by"]).lower()
    assert "canonical" in canonical
    assert "duplicate" in canonical


def test_guidance_states_that_schema_does_not_fix_cannibalisation():
    fix = recommend_fix(Collision("a", "b", ["x", "y"], ["x"], "high"))
    assert any("schema" in reason.lower() for reason in fix["not_fixed_by"])


def test_guidance_explains_how_to_verify_in_search_console():
    fix = recommend_fix(Collision("a", "b", ["x", "y"], ["x"], "high"))
    assert "search console" in fix["how_to_verify"].lower()


# --- Corpus analysis ---

def test_corpus_analysis_reads_files_and_reports_totals(tmp_path):
    for name, title in [("a", "Luxury Flats in Noida Sector 151"),
                        ("b", "Luxury Flats Noida Sector 151 Guide")]:
        f = tmp_path / f"{name}.md"
        f.write_text(f"# {title}\n\nMeta Title: {title}\n\nBody text.\n", encoding="utf-8")

    result = analyse_corpus([
        {"local_file": str(tmp_path / "a.md")},
        {"local_file": str(tmp_path / "b.md")},
    ])
    assert result["pages_analysed"] == 2
    assert result["collisions"] >= 1


def test_corpus_analysis_skips_entries_whose_file_is_missing(tmp_path):
    result = analyse_corpus([{"local_file": str(tmp_path / "gone.md")}])
    assert result["pages_analysed"] == 0


def test_corpus_analysis_accepts_both_inventory_key_names(tmp_path):
    """Inventory sections use 'local_file' or 'file' depending on origin."""
    f = tmp_path / "a.md"
    f.write_text("# Luxury Flats in Noida\n\nBody.\n", encoding="utf-8")
    assert analyse_corpus([{"file": str(f)}])["pages_analysed"] == 1
