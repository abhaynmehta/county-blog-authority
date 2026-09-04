"""Data models for the audit engine."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    CRITICAL = "critical"  # Cannot publish
    HIGH = "high"          # Must fix before publish
    MEDIUM = "medium"      # Should fix
    LOW = "low"            # Nice to have
    INFO = "info"          # Informational


class Owner(str, Enum):
    ROI = "ROI"    # Content/SEO agency
    AGO = "AGO"    # Website/CMS agency
    BOTH = "BOTH"  # Shared responsibility
    INTERNAL = "INTERNAL"  # County Group internal team


class IssueCategory(str, Enum):
    FACTUAL_ERROR = "factual_error"
    STALE_CLAIM = "stale_claim"
    HEADING_STRUCTURE = "heading_structure"
    META_TITLE = "meta_title"
    META_DESCRIPTION = "meta_description"
    SCHEMA_MISSING = "schema_missing"
    SCHEMA_INVALID = "schema_invalid"
    INTERNAL_LINKS = "internal_links"
    EXTERNAL_LINKS = "external_links"
    IMAGE_SEO = "image_seo"
    KEYWORD_CANNIBALIZATION = "keyword_cannibalization"
    CONTENT_OVERLAP = "content_overlap"
    RERA_COMPLIANCE = "rera_compliance"
    PROHIBITED_LANGUAGE = "prohibited_language"
    # Search-spam signals (keyword stuffing, CTA spam). Kept separate from
    # PROHIBITED_LANGUAGE so they do not fail the RERA & Legal gate — a
    # repeated phrase is an SEO problem, not a compliance breach.
    SPAM_SIGNAL = "spam_signal"
    GRAMMAR = "grammar"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    MISSING_EVIDENCE = "missing_evidence"
    INFRASTRUCTURE_STATUS = "infrastructure_status"
    AI_READINESS = "ai_readiness"
    CANONICAL = "canonical"
    DEPLOYMENT = "deployment"


class GateStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    NOT_APPLICABLE = "N/A"
    MANUAL_REVIEW = "MANUAL_REVIEW"


@dataclass
class AuditIssue:
    """A single audit finding with actionable fix and owner assignment."""
    issue_id: str
    category: IssueCategory
    severity: Severity
    owner: Owner
    summary: str
    paragraph: Optional[int] = None
    line: Optional[int] = None
    claim: Optional[str] = None
    reason: str = ""
    evidence_source: Optional[str] = None
    verified_status: Optional[str] = None
    recommended_action: str = ""
    suggested_replacement: Optional[str] = None
    acceptance_test: str = ""
    google_rule: Optional[str] = None
    editorial_rule: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v.value if isinstance(v, Enum) else v
                for k, v in asdict(self).items() if v is not None}


@dataclass
class GateResult:
    """Result of a single publication gate check."""
    gate_name: str
    gate_number: int
    status: GateStatus
    details: str = ""
    issues: list[AuditIssue] = field(default_factory=list)


@dataclass
class MetadataAnalysis:
    """Analysis of a blog's metadata."""
    title: Optional[str] = None
    title_length: int = 0
    title_issues: list[str] = field(default_factory=list)
    meta_description: Optional[str] = None
    meta_description_length: int = 0
    meta_description_issues: list[str] = field(default_factory=list)
    h1: Optional[str] = None
    h1_count: int = 0
    headings: list[dict] = field(default_factory=list)
    heading_issues: list[str] = field(default_factory=list)
    keywords: Optional[str] = None
    category: Optional[str] = None
    image_alt: Optional[str] = None
    image_filename: Optional[str] = None
    faq_schema: Optional[str] = None


@dataclass
class ContentAnalysis:
    """Full content analysis result."""
    file_path: str
    word_count: int = 0
    paragraph_count: int = 0
    metadata: MetadataAnalysis = field(default_factory=MetadataAnalysis)
    issues: list[AuditIssue] = field(default_factory=list)
    gates: list[GateResult] = field(default_factory=list)
    score: int = 0
    publishable: bool = False

    def to_json(self) -> str:
        data = {
            "file_path": self.file_path,
            "word_count": self.word_count,
            "paragraph_count": self.paragraph_count,
            "score": self.score,
            "publishable": self.publishable,
            "issue_count": len(self.issues),
            "issues_by_severity": {
                s.value: len([i for i in self.issues if i.severity == s])
                for s in Severity
            },
            "issues_by_owner": {
                o.value: len([i for i in self.issues if i.owner == o])
                for o in Owner
            },
            "gates": [
                {"gate": g.gate_name, "status": g.status.value, "details": g.details}
                for g in self.gates
            ],
            "issues": [i.to_dict() for i in self.issues],
        }
        return json.dumps(data, indent=2)
