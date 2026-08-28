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

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

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
class TruthLayer:
    """The loaded registry: claims plus the wording rules they imply."""

    claims: list[Claim] = field(default_factory=list)
    prohibited_wording: list[str] = field(default_factory=list)
    loaded_from: Optional[str] = None

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
        return not self.claims and not self.prohibited_wording


def load_truth_layer(base_dir: Path | str = CONTEXT_DIR) -> TruthLayer:
    """Load every claims file under `base_dir/claims/`.

    Returns an empty TruthLayer when the directory is absent, so callers
    degrade to their built-in rules rather than failing.
    """
    base = Path(base_dir)
    claims_dir = base / "claims"
    layer = TruthLayer(loaded_from=str(base))

    if not claims_dir.is_dir():
        return layer

    for path in sorted(claims_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        if not isinstance(data, dict):
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

    return layer


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
        "prohibited_phrases": len(layer.prohibited_wording),
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
