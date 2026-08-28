"""Tests for project-aware auditing and link checking.

These cover the checks that depend on the project registry: a project placed
in the wrong city, cited under the wrong RERA authority, quoted by super area
alone, and the internal/external link rules.
"""

from pathlib import Path

import pytest

from search_authority.truth_layer import load_truth_layer
from search_authority.content_auditor import audit_text, _near


@pytest.fixture
def registry(tmp_path: Path) -> Path:
    """Two projects in different states, so cross-contamination shows up."""
    projects = tmp_path / "projects"
    projects.mkdir(parents=True)
    (projects / "center_court.yaml").write_text(
        "project:\n"
        "  name: The Center Court\n"
        "  registered_promoter: Ashiana Landcraft Realty Private Limited\n"
        "location:\n"
        "  city: Gurugram\n"
        "  state: Haryana\n"
        "  sector: 88-A\n"
        "rera:\n"
        "  authority: HARERA\n"
        "  registration_number: RC/REP/HARERA/GGM/46\n"
        "configurations:\n"
        "  - {type: 3 BHK, super_area_sqft: 1565, carpet_area_sqft: 888}\n"
        "county_urls:\n"
        "  project_page: https://www.countygroup.in/centercourt/\n"
        "prohibited_for_this_project:\n"
        "  - Describing this project as being in Noida\n",
        encoding="utf-8",
    )
    (projects / "ivory_county.yaml").write_text(
        "project:\n"
        "  name: Ivory County\n"
        "location:\n"
        "  city: Noida\n"
        "  state: Uttar Pradesh\n"
        "rera:\n"
        "  authority: UP-RERA\n"
        "configurations:\n"
        "  - {type: 3 BHK, super_area_sqft: 2034, carpet_area_sqft: 1255}\n"
        "county_urls:\n"
        "  project_page: https://www.countygroup.in/ivorycounty/\n",
        encoding="utf-8",
    )
    (tmp_path / "site_urls.yaml").write_text(
        "project_sites:\n"
        "  - url: https://www.countygroup.in/centercourt/\n"
        "  - url: https://www.countygroup.in/ivorycounty/\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def patched(monkeypatch, registry):
    """Point the auditor at the fixture registry."""
    import search_authority.content_auditor as ca
    monkeypatch.setattr(ca, "load_truth_layer", lambda *a: load_truth_layer(registry))
    return registry


def criticals(result):
    return [i for i in result.issues if i.severity.name == "CRITICAL"]


def summaries(result):
    return " | ".join(i.summary for i in result.issues)


# --- Project loading ---

def test_projects_load_with_location_and_authority(registry):
    layer = load_truth_layer(registry)
    cc = layer.project_by_name("The Center Court")
    assert (cc.city, cc.state, cc.rera_authority) == ("Gurugram", "Haryana", "HARERA")


def test_malformed_project_file_is_recorded_not_silently_dropped(tmp_path):
    """A registry file that stops parsing must never fail quietly."""
    projects = tmp_path / "projects"
    projects.mkdir(parents=True)
    (projects / "broken.yaml").write_text("project:\n  name: X\n bad: [\n", encoding="utf-8")

    layer = load_truth_layer(tmp_path)

    assert layer.projects == []
    assert layer.load_errors and "broken.yaml" in layer.load_errors[0]["file"]


def test_project_file_without_a_name_is_reported(tmp_path):
    projects = tmp_path / "projects"
    projects.mkdir(parents=True)
    (projects / "nameless.yaml").write_text("location:\n  city: Noida\n", encoding="utf-8")

    errors = load_truth_layer(tmp_path).load_errors
    assert any("no project.name" in e["error"] for e in errors)


# --- Wrong city ---

def test_project_placed_in_the_wrong_city_is_critical(patched):
    result = audit_text("# X\n\nThe Center Court in Noida offers 3 BHK homes.\n")
    assert any("placed in Noida" in i.summary for i in criticals(result))


def test_correct_city_raises_nothing(patched):
    result = audit_text("# X\n\nThe Center Court in Gurugram offers 3 BHK homes.\n")
    assert not any("placed in" in i.summary for i in result.issues)


def test_gurgaon_is_accepted_as_gurugram(patched):
    """The city was renamed; both spellings are correct."""
    result = audit_text("# X\n\nThe Center Court in Gurgaon offers 3 BHK homes.\n")
    assert not any("placed in" in i.summary for i in result.issues)


@pytest.mark.parametrize("sentence", [
    "The Center Court in Noida offers 3 BHK homes.",
    "The Center Court, Noida is a landmark project.",
    "The Center Court is located in Noida near the metro.",
    "The Center Court is situated in Noida.",
])
def test_explicit_location_assertions_are_caught(patched, sentence):
    result = audit_text(f"# X\n\n{sentence}\n")
    assert any("placed in Noida" in i.summary for i in criticals(result)), sentence


@pytest.mark.parametrize("sentence", [
    # A road name, not a location claim.
    "The Center Court sits on the Greater Noida Expressway with good access.",
    # The region, not the city.
    "The Center Court has strong Delhi NCR connectivity.",
    "The Center Court is well connected across Delhi-NCR.",
    # An airport, not a city.
    "The Center Court is near the Noida International Airport corridor.",
    # A keyword list, not prose.
    "The Center Court: flats in ghaziabad, delhi ncr, luxury homes.",
    # An authority name.
    "The Center Court was approved by the Noida Authority.",
])
def test_city_names_inside_larger_proper_nouns_are_not_location_claims(patched, sentence):
    """The check must not fire on roads, regions, airports, or keyword lists.

    Indian property copy says "Delhi NCR" and "Greater Noida Expressway"
    constantly. Flagging those would make every report untrustworthy.
    """
    result = audit_text(f"# X\n\n{sentence}\n")
    assert not any("placed in" in i.summary for i in result.issues), sentence


def test_an_unmentioned_project_is_not_judged(patched):
    """A blog about Ivory County must not be checked against Center Court."""
    result = audit_text("# X\n\nIvory County in Noida offers 3 BHK homes.\n")
    assert not any("Center Court" in i.summary for i in result.issues)


# --- Wrong RERA authority ---

def test_wrong_rera_authority_is_critical(patched):
    result = audit_text(
        "# X\n\nThe Center Court offers homes with super area of 1565 sq. ft.\n"
        "Registered under UP-RERA, it is a landmark.\n"
    )
    assert any("UP-RERA" in i.summary and "HARERA" in i.summary for i in criticals(result))


def test_correct_rera_authority_raises_nothing(patched):
    result = audit_text("# X\n\nThe Center Court is registered under HARERA.\n")
    assert not any("registered with" in i.summary for i in result.issues)


def test_abbreviations_do_not_break_proximity_matching(patched):
    """'sq. ft.' must not act as a sentence boundary between name and claim."""
    text = (
        "# X\n\nThe Center Court has a super area of 1565 sq. ft. and a built-up "
        "area of 1260 sq. ft. It is registered under UP-RERA.\n"
    )
    assert any("UP-RERA" in i.summary for i in criticals(audit_text(text)))


# --- Area disclosure ---

def test_super_area_without_carpet_area_is_flagged(patched):
    result = audit_text("# X\n\nThe Center Court offers 1565 sq ft homes in Gurugram.\n")
    assert any("super area 1565" in i.summary for i in result.issues)


def test_super_area_with_carpet_area_present_is_accepted(patched):
    result = audit_text(
        "# X\n\nThe Center Court in Gurugram: super area 1565 sq ft, "
        "carpet area 888 sq ft.\n"
    )
    assert not any("with no carpet area" in i.summary for i in result.issues)


# --- Links ---

def test_generic_anchor_text_on_internal_link_is_flagged(patched):
    result = audit_text(
        "# X\n\nSee [here](https://www.countygroup.in/centercourt/) for details.\n"
    )
    assert any("Generic anchor text" in i.summary for i in result.issues)


def test_descriptive_anchor_text_is_accepted(patched):
    result = audit_text(
        "# X\n\nSee the [Center Court project page]"
        "(https://www.countygroup.in/centercourt/).\n"
    )
    assert not any("Generic anchor" in i.summary for i in result.issues)


def test_only_internal_links_triggers_the_external_source_rule(patched):
    result = audit_text(
        "# X\n\n[Center Court page](https://www.countygroup.in/centercourt/)\n"
    )
    assert any("No external authority links" in i.summary for i in result.issues)


def test_an_external_citation_satisfies_the_rule(patched):
    result = audit_text(
        "# X\n\n[Center Court page](https://www.countygroup.in/centercourt/) and "
        "[HARERA](https://www.haryanarera.gov.in/)\n"
    )
    assert not any("No external authority" in i.summary for i in result.issues)


def test_unregistered_county_url_is_flagged(patched):
    result = audit_text(
        "# X\n\n[Typo page](https://www.countygroup.in/centrecourt/) and "
        "[HARERA](https://www.haryanarera.gov.in/)\n"
    )
    assert any("needs verification" in i.summary for i in result.issues)


def test_registered_county_url_is_accepted(patched):
    result = audit_text(
        "# X\n\n[Center Court page](https://www.countygroup.in/centercourt/) and "
        "[HARERA](https://www.haryanarera.gov.in/)\n"
    )
    assert not any("needs verification" in i.summary for i in result.issues)


def test_deep_blog_urls_are_not_treated_as_project_pages(patched):
    """Only top-level County URLs are checked against the project registry."""
    result = audit_text(
        "# X\n\n[a post](https://www.countygroup.in/blog/some-article/) and "
        "[HARERA](https://www.haryanarera.gov.in/)\n"
    )
    assert not any("needs verification" in i.summary for i in result.issues)


# --- URL normalisation ---

def test_normalisation_preserves_path_case():
    """URL paths are case-sensitive; countygroup.in/Residential is a real page
    while /residential 404s. Folding the path would invent broken links."""
    from search_authority.truth_layer import _normalise_url
    assert _normalise_url("https://www.countygroup.in/Residential").endswith("/Residential")


def test_normalisation_lowercases_only_the_host():
    from search_authority.truth_layer import _normalise_url
    assert _normalise_url("HTTPS://WWW.CountyGroup.IN/Foo") == "countygroup.in/Foo"


@pytest.mark.parametrize("variant", [
    "https://www.countygroup.in/centercourt/",
    "http://countygroup.in/centercourt",
    "https://www.countygroup.in/centercourt/?utm_source=x",
    "https://www.countygroup.in/centercourt/#top",
])
def test_equivalent_url_forms_normalise_together(variant):
    from search_authority.truth_layer import _normalise_url
    assert _normalise_url(variant) == "countygroup.in/centercourt"


def test_raw_site_urls_are_fetchable_as_written(tmp_path):
    """check_links must use the original URLs, not normalised ones — a
    normalised URL has no scheme and cannot be requested."""
    from search_authority.truth_layer import raw_site_urls
    (tmp_path / "site_urls.yaml").write_text(
        "project_sites:\n  - url: https://www.countygroup.in/Residential\n",
        encoding="utf-8",
    )
    assert raw_site_urls(tmp_path) == ["https://www.countygroup.in/Residential"]


# --- Proximity helper ---

def test_near_matches_in_either_order():
    assert _near("HARERA governs The Center Court", "The Center Court", "HARERA")
    assert _near("The Center Court under HARERA", "The Center Court", "HARERA")


def test_near_respects_the_window():
    text = "The Center Court" + (" filler" * 100) + " HARERA"
    assert _near(text, "The Center Court", "HARERA", window=30) is None
