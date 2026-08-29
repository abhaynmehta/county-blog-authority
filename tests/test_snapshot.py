"""Snapshot tests: catch rule changes that silently move scores.

The corpus is 87 documents. Re-running the batch and reading the average
catches a large shift, but not six documents moving four points each while
the mean holds. That is exactly the change most likely to be a bug.

A committed baseline turns every score movement into a reviewable diff. When
a change is intended, run:

    python -m pytest tests/test_snapshot.py --snapshot-update

and the diff appears in the commit for review, rather than nowhere.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from search_authority.content_auditor import audit_text
from search_authority.truth_layer import load_truth_layer

BASELINE = Path(__file__).parent / "fixtures" / "score_baseline.json"

# Fixed inputs covering each rule family. Kept here rather than pointing at
# the live corpus so the baseline does not churn whenever a blog is edited.
CASES: dict[str, str] = {
    "clean_compliant": (
        "# The Center Court, Sector 88-A Gurugram\n\n"
        "Meta Title: The Center Court Sector 88-A Gurugram Buyer Guide\n"
        "Meta Description: A guide to The Center Court in Sector 88-A Gurugram "
        "with carpet areas, HARERA registration and sources for every figure.\n\n"
        "The Center Court is in Sector 88-A, Gurugram, Haryana, registered with "
        "HARERA under registration number RC/REP/HARERA/GGM/46 of "
        "2017/7(3)/45/2024/04, verifiable on the "
        "[HARERA portal](https://www.haryanarera.gov.in/).\n\n"
        "![Tower elevation](center-court-gurugram.jpg)\n\n"
        "Carpet area is 888 sq ft for Type A. Approximate drive times are "
        "30 minutes from IFFCO Chowk, varying with traffic.\n\n"
        "RERA registration records a project with the authority. It is not an "
        "endorsement of quality or an investment guarantee.\n\n"
        + ("A substantive sentence about the development and its context. " * 120)
    ),
    "wrong_city_and_authority": (
        "# Center Court\n\n"
        "The Center Court in Noida offers homes with super area of 1565 sq. ft.\n"
        "Registered under UP-RERA, this project offers assured returns.\n"
    ),
    "stale_infrastructure": (
        "# Noida Growth\n\n"
        "The upcoming airport at Jewar will transform the region.\n"
        "Property values will grow because of it.\n"
    ),
    "prohibited_language": (
        "# Investment Guide\n\n"
        "This is the best investment in Noida with guaranteed appreciation "
        "and risk-free returns for every buyer.\n"
    ),
    "wrong_carpet_area": (
        "# Jade County\n\n"
        "Jade County has a carpet area of 1850 sq ft for its 3 BHK homes.\n"
    ),
    "prose_tells": (
        "# Living Well\n\n"
        "In today's fast-paced world, let us delve into the tapestry of luxury.\n\n"
        "Nestled in the heart of Noida, these homes are luxurious, spacious, "
        "and premium.\n\n"
        "Moreover, it is not only well connected but also close to schools.\n"
    ),
    "link_problems": (
        "# Guide\n\n"
        "Read more [here](https://www.countygroup.in/centercourt/) about our "
        "projects and offerings across the region.\n"
    ),
    "thin_content": "# Short\n\nA very short post about flats.\n",
    # Boundary cases. A snapshot only catches what its fixtures exercise, so
    # these sit deliberately close to a threshold: a quiet tweak to the
    # word-count floor or the keyword-repetition limit changes their result.
    "just_above_thin_threshold": (
        "# Boundary\n\n" + ("A sentence with exactly ten words in it for counting. " * 85)
    ),
    "just_below_keyword_stuffing_limit": (
        "# Boundary\n\n"
        + ("Luxury homes here are pleasant. " * 40)
        + ("The premium residential area is calm. " * 7)
    ),
}


def current_snapshot() -> dict:
    """Score, gate status and issue IDs for every case."""
    snapshot = {}
    for name, text in sorted(CASES.items()):
        result = audit_text(text)
        snapshot[name] = {
            "score": result.score,
            "publishable": result.publishable,
            "gates": {g.gate_name: g.status.value for g in result.gates},
            "issue_ids": sorted(i.issue_id for i in result.issues),
            "issue_count": len(result.issues),
        }

    layer = load_truth_layer()
    snapshot["_registry"] = {
        "projects": sorted(p.name for p in layer.projects),
        "rera_numbers": {
            p.name: sorted(p.rera_numbers) for p in layer.projects if p.rera_numbers
        },
        "carpet_areas": {
            p.name: sorted(p.carpet_areas()) for p in layer.projects if p.carpet_areas()
        },
        "prohibited_phrase_count": len(layer.prohibited_wording),
        "load_errors": layer.load_errors,
    }
    return snapshot


@pytest.fixture(scope="module")
def baseline(request) -> dict:
    snapshot = current_snapshot()
    if request.config.getoption("--snapshot-update", default=False):
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
        pytest.skip("baseline rewritten")
    if not BASELINE.exists():
        pytest.skip("no baseline yet; run with --snapshot-update")
    return json.loads(BASELINE.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", sorted(CASES))
def test_score_has_not_moved(baseline, case):
    """A score change is either intended — commit the new baseline — or a bug."""
    current = current_snapshot()[case]
    expected = baseline[case]
    assert current["score"] == expected["score"], (
        f"{case}: score {expected['score']} -> {current['score']}. "
        "If intended, rerun with --snapshot-update and commit the diff."
    )


@pytest.mark.parametrize("case", sorted(CASES))
def test_gate_results_have_not_moved(baseline, case):
    assert current_snapshot()[case]["gates"] == baseline[case]["gates"], case


@pytest.mark.parametrize("case", sorted(CASES))
def test_the_same_issues_are_still_found(baseline, case):
    """Catches a rule that stopped firing, which a score check can miss when
    another rule starts firing at the same weight."""
    current = set(current_snapshot()[case]["issue_ids"])
    expected = set(baseline[case]["issue_ids"])
    assert current == expected, (
        f"{case}: gained {sorted(current - expected)}, "
        f"lost {sorted(expected - current)}"
    )


def test_registry_contents_have_not_changed(baseline):
    """Registry edits are deliberate. An unexpected change here means a YAML
    file was altered without the baseline being updated."""
    assert current_snapshot()["_registry"] == baseline["_registry"]


def test_the_registry_still_loads_without_errors():
    assert load_truth_layer().load_errors == []


def test_every_project_has_a_rera_authority():
    """Three of five projects silently loaded no authority at all before the
    loader understood phased registrations."""
    missing = [p.name for p in load_truth_layer().projects if not p.rera_authority]
    assert missing == ["County Courtyard"], (
        f"unexpected projects without a RERA authority: {missing}"
    )


def test_residential_projects_carry_at_least_one_registration():
    layer = load_truth_layer()
    residential = [p for p in layer.projects if p.name != "County Courtyard"]
    missing = [p.name for p in residential if not p.rera_numbers]
    assert missing == [], f"projects with no RERA registration: {missing}"
