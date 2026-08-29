"""Truth Layer loader — reads the county_context/ claim registry.

The registry is the single place where verified facts live: what is
operational, what is merely approved, which wording is forbidden, and when
each claim was last checked. The auditor reads facts from here rather than
hard-coding them, so updating a YAML file changes what every audit enforces.

Every claim carries a TTL (`refresh_days`). A claim past its TTL is stale:
still usable, but nobody has re-verified it, so it should be re-checked
before being relied on in published content.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from . import yaml_strict
import yaml

CONTEXT_DIR = Path("county_context")


def _parse_date(value) -> Optional[date]:
    """Accept a date, an ISO string, or None."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


@dataclass
class Claim:
    """A single verified (or unverified) fact from the registry."""

    claim_id: str
    claim: str
    category: str
    status: Optional[str] = None
    detail: Optional[str] = None
    source: Optional[str] = None
    last_verified: Optional[date] = None
    refresh_days: Optional[int] = None
    note: Optional[str] = None

    def is_stale(self, today: Optional[date] = None) -> bool:
        """True when the claim has a TTL and has outlived it.

        A claim that was never verified is not stale — it is incomplete,
        which is reported separately so the two problems stay distinct.
        """
        if self.last_verified is None or not self.refresh_days:
            return False
        today = today or date.today()
        return (today - self.last_verified).days > self.refresh_days

    def days_overdue(self, today: Optional[date] = None) -> int:
        if not self.is_stale(today):
            return 0
        today = today or date.today()
        return (today - self.last_verified).days - self.refresh_days

    def missing_fields(self) -> list[str]:
        """Fields a claim needs before content is allowed to rely on it."""
        missing = []
        if not self.status:
            missing.append("status")
        if not self.source:
            missing.append("source")
        if self.last_verified is None:
            missing.append("last_verified")
        return missing

    def is_incomplete(self) -> bool:
        return bool(self.missing_fields())


@dataclass
class Project:
    """A County Group project as the registry records it.

    `prohibited` holds rules that apply only when content discusses this
    project — e.g. Center Court must never be described as being in Noida.
    """

    name: str
    slug: str
    city: Optional[str] = None
    state: Optional[str] = None
    sector: Optional[str] = None
    rera_authority: Optional[str] = None
    # Every registration this project holds. A project may be registered in
    # phases, each with its own number, so a single field silently dropped
    # all but one — and for three of five projects, dropped all of them.
    rera_numbers: list[str] = field(default_factory=list)
    promoter_registration: Optional[str] = None
    promoter: Optional[str] = None
    project_page: Optional[str] = None
    prohibited: list[str] = field(default_factory=list)
    configurations: list[dict] = field(default_factory=list)
    # Figures seen in content but with no source document on file. Kept
    # apart from `configurations` so they are never treated as verified,
    # while still letting the auditor say "awaiting a source" rather than
    # "this number is wrong".
    unverified_configurations: list[dict] = field(default_factory=list)

    def carpet_areas(self) -> list[int]:
        out = []
        for c in self.configurations:
            v = c.get("carpet_area_sqft")
            if isinstance(v, (int, float)):
                out.append(int(v))
        return out

    @property
    def rera_number(self) -> Optional[str]:
        """The first registration, for callers that want one. Prefer
        `rera_numbers` — most projects have more than one."""
        return self.rera_numbers[0] if self.rera_numbers else None

    def unverified_carpet_areas(self) -> list[int]:
        out = []
        for c in self.unverified_configurations:
            v = c.get("carpet_area_sqft")
            if isinstance(v, (int, float)):
                out.append(int(v))
        return out

    def super_areas(self) -> list[int]:
        out = []
        for c in self.configurations:
            v = c.get("super_area_sqft")
            if isinstance(v, (int, float)):
                out.append(int(v))
        return out


@dataclass
class TruthLayer:
    """The loaded registry: claims plus the wording rules they imply."""

    claims: list[Claim] = field(default_factory=list)
    prohibited_wording: list[str] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    known_urls: set = field(default_factory=set)
    unverified_urls: set = field(default_factory=set)
    load_errors: list[dict] = field(default_factory=list)
    loaded_from: Optional[str] = None

    def project_by_name(self, name: str) -> Optional[Project]:
        target = name.strip().lower()
        for p in self.projects:
            if p.name.lower() == target or p.slug == target:
                return p
        return None

    def stale_claims(self, today: Optional[date] = None) -> list[Claim]:
        return [c for c in self.claims if c.is_stale(today)]

    def incomplete_claims(self) -> list[Claim]:
        return [c for c in self.claims if c.is_incomplete()]

    def by_id(self, claim_id: str) -> Optional[Claim]:
        for c in self.claims:
            if c.claim_id == claim_id:
                return c
        return None

    @property
    def is_empty(self) -> bool:
        return not self.claims and not self.prohibited_wording and not self.projects


def load_truth_layer(base_dir: Path | str = CONTEXT_DIR) -> TruthLayer:
    """Load every claims file under `base_dir/claims/`.

    Returns an empty TruthLayer when the directory is absent, so callers
    degrade to their built-in rules rather than failing.
    """
    base = Path(base_dir)
    claims_dir = base / "claims"
    layer = TruthLayer(loaded_from=str(base))

    # Claims and projects are independent: a registry may have either, both,
    # or neither. Missing claims must not stop projects from loading.
    for path in sorted(claims_dir.glob("*.yaml")) if claims_dir.is_dir() else []:
        try:
            data = yaml_strict.load_file(path) or {}
        except yaml.YAMLError as exc:
            layer.load_errors.append(
                {"file": str(path), "error": str(exc).splitlines()[0]}
            )
            continue
        if not isinstance(data, dict):
            layer.load_errors.append(
                {"file": str(path), "error": "top level is not a mapping"}
            )
            continue

        category = data.get("claim_category") or path.stem

        for raw in data.get("claims") or []:
            if not isinstance(raw, dict) or not raw.get("claim_id"):
                continue
            layer.claims.append(Claim(
                claim_id=str(raw["claim_id"]),
                claim=str(raw.get("claim", "")),
                category=str(category),
                status=raw.get("status"),
                detail=raw.get("detail"),
                source=raw.get("source"),
                last_verified=_parse_date(raw.get("last_verified")),
                refresh_days=raw.get("refresh_days"),
                note=raw.get("note"),
            ))

        for phrase in data.get("prohibited_wording") or []:
            text = str(phrase).split("#")[0].strip().strip('"\'')
            if text and text not in layer.prohibited_wording:
                layer.prohibited_wording.append(text)

    layer.projects = _load_projects(base / "projects", layer.load_errors)
    layer.known_urls, layer.unverified_urls = _load_site_urls(
        base / "site_urls.yaml", layer.load_errors
    )
    return layer


def _normalise_url(url: str) -> str:
    """Compare URLs without tripping over trailing slashes, query strings,
    fragments, or www/scheme differences.

    Only the host is lowercased. URL paths are case-sensitive on most
    servers — countygroup.in/Residential returns 200 while /residential
    returns 404 — so folding the path would invent broken links.
    """
    u = str(url).split("#")[0].split("?")[0].strip().rstrip("/")
    u = re.sub(r"^https?://", "", u, flags=re.IGNORECASE)
    u = re.sub(r"^www\.", "", u, flags=re.IGNORECASE)
    host, slash, path = u.partition("/")
    return host.lower() + slash + path


def _load_site_urls(path: Path, errors: list[dict]) -> tuple[set[str], set[str]]:
    """Load the authoritative URL list. Returns (known, unverified)."""
    if not path.is_file():
        return set(), set()
    try:
        data = yaml_strict.load_file(path) or {}
    except yaml.YAMLError as exc:
        errors.append({"file": str(path), "error": str(exc).split("\n")[0]})
        return set(), set()
    if not isinstance(data, dict):
        return set(), set()

    known: set[str] = set()
    for key in ("project_sites", "landing_pages"):
        for entry in data.get(key) or []:
            url = entry.get("url") if isinstance(entry, dict) else entry
            if url:
                known.add(_normalise_url(url))
                _RAW_URLS.add(str(url))

    unverified = set()
    for e in data.get("unverified") or []:
        if isinstance(e, dict) and e.get("url"):
            unverified.add(_normalise_url(e["url"]))
            _RAW_URLS.add(str(e["url"]))
    return known, unverified


# URLs exactly as written in site_urls.yaml. The normalised forms are for
# comparison only and must never be used to make a request — normalisation
# strips the scheme and cannot round-trip back to a fetchable URL.
_RAW_URLS: set[str] = set()


def raw_site_urls(base_dir: Path | str = CONTEXT_DIR) -> list[str]:
    """Every URL in site_urls.yaml, exactly as written."""
    _RAW_URLS.clear()
    load_truth_layer(base_dir)
    return sorted(_RAW_URLS)


# RERA data is spelled several ways across the registry: a `rera:` block, a
# newer `rera_project:` block, singular `registration_number`, plural
# `registration_numbers`, and `project_registration_numbers`. Rather than
# rewrite every file and hope, the loader reads all of them and prefers the
# project-level record over the older flat one.
_RERA_BLOCKS = ("rera_project", "rera")
_NUMBER_KEYS = ("registration_numbers", "project_registration_numbers",
                "registration_number", "project_registration_number")


def _read_rera(data: dict) -> tuple[Optional[str], list[str], Optional[str]]:
    """Return (authority, [registration numbers], promoter registration)."""
    authority = None
    numbers: list[str] = []
    promoter = None

    for block_name in _RERA_BLOCKS:
        block = data.get(block_name)
        if not isinstance(block, dict):
            continue
        authority = authority or block.get("authority")
        promoter = promoter or block.get("promoter_registration_number")

        for key in _NUMBER_KEYS:
            value = block.get(key)
            if isinstance(value, str) and value.strip():
                if value not in numbers:
                    numbers.append(value.strip())
            elif isinstance(value, list):
                for item in value:
                    text = str(item).split("#")[0].strip()
                    if text and text not in numbers:
                        numbers.append(text)

    # Infer the authority from the state when the file does not say.
    if not authority:
        state = ((data.get("location") or {}).get("state") or "").strip().lower()
        authority = {"uttar pradesh": "UP-RERA", "haryana": "HARERA"}.get(state)

    return authority, numbers, promoter


def _load_projects(projects_dir: Path, errors: list[dict]) -> list[Project]:
    """Load one Project per YAML file under `projects/`.

    A file that fails to parse is recorded in `errors` rather than skipped
    silently — an unreadable project file means its facts stop being
    enforced, which must never happen quietly.
    """
    if not projects_dir.is_dir():
        return []

    projects: list[Project] = []
    for path in sorted(projects_dir.glob("*.yaml")):
        try:
            data = yaml_strict.load_file(path) or {}
        except yaml.YAMLError as exc:
            errors.append({"file": str(path), "error": str(exc).split("\n")[0]})
            continue
        if not isinstance(data, dict):
            errors.append({"file": str(path), "error": "top level is not a mapping"})
            continue

        meta = data.get("project") or {}
        name = meta.get("name")
        if not name:
            errors.append({"file": str(path), "error": "no project.name"})
            continue

        loc = data.get("location") or {}
        authority, numbers, promoter_reg = _read_rera(data)

        projects.append(Project(
            name=str(name),
            slug=path.stem,
            city=loc.get("city"),
            state=loc.get("state"),
            sector=str(loc["sector"]) if loc.get("sector") is not None else None,
            rera_authority=authority,
            rera_numbers=numbers,
            promoter_registration=promoter_reg,
            promoter=meta.get("registered_promoter"),
            project_page=(data.get("county_urls") or {}).get("project_page"),
            prohibited=[
                str(p).split("#")[0].strip()
                for p in (data.get("prohibited_for_this_project") or [])
                if str(p).strip()
            ],
            # A sub-brand (Ivory Gold within Ivory County) is a tier of the
            # same project, so its units are registered configurations too.
            # Omitting them made valid carpet areas look unregistered.
            configurations=[
                c for c in (
                    (data.get("configurations") or [])
                    + ((data.get("sub_brand") or {}).get("configurations") or [])
                ) if isinstance(c, dict)
            ],
            unverified_configurations=[
                c for c in (
                    (data.get("unverified_configurations") or [])
                    + ((data.get("sub_brand") or {}).get("unverified_configurations") or [])
                ) if isinstance(c, dict)
            ],
        ))

    return projects


def registry_report(base_dir: Path | str = CONTEXT_DIR,
                    today: Optional[date] = None) -> dict:
    """Operator-facing health check of the registry itself.

    Answers: which facts has nobody re-verified lately, and which claims are
    too incomplete to enforce?
    """
    layer = load_truth_layer(base_dir)
    today = today or date.today()
    stale = layer.stale_claims(today)
    incomplete = layer.incomplete_claims()

    return {
        "loaded_from": layer.loaded_from,
        "total_claims": len(layer.claims),
        "total_projects": len(layer.projects),
        "prohibited_phrases": len(layer.prohibited_wording),
        "load_errors": layer.load_errors,
        "stale_count": len(stale),
        "incomplete_count": len(incomplete),
        "stale": [
            {
                "claim_id": c.claim_id,
                "claim": c.claim,
                "last_verified": c.last_verified.isoformat() if c.last_verified else None,
                "refresh_days": c.refresh_days,
                "days_overdue": c.days_overdue(today),
                "source": c.source,
            }
            for c in sorted(stale, key=lambda x: -x.days_overdue(today))
        ],
        "incomplete": [
            {
                "claim_id": c.claim_id,
                "claim": c.claim,
                "missing": c.missing_fields(),
                "note": c.note,
            }
            for c in incomplete
        ],
    }
