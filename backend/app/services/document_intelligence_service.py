"""V2 document intelligence for Smart Copilot Creation.

This first implementation is deterministic and deliberately provider-free:
it gives us a safe, testable baseline for domain/type recommendation before
we add an LLM classifier as a fallback. The signal set is intentionally
small and explainable so the UI can show why a Copilot was recommended.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.document_classification import (
    DocumentClassificationRequest,
    DocumentClassificationResponse,
)


@dataclass(frozen=True)
class _DomainProfile:
    domain: str
    copilot: str
    document_types: tuple[tuple[str, tuple[str, ...]], ...]
    keywords: tuple[str, ...]


_PROFILES = (
    _DomainProfile(
        domain="HR",
        copilot="HR Copilot",
        document_types=(
            ("Leave & Time Off Policy", ("leave", "vacation", "pto", "time off", "absence")),
            ("Employee Policy", ("employee handbook", "code of conduct", "hr policy", "employee")),
            ("Benefits & Compensation", ("benefits", "compensation", "salary", "payroll", "insurance")),
        ),
        keywords=("hr", "human resources", "employee", "leave", "benefits", "payroll", "onboarding"),
    ),
    _DomainProfile(
        domain="Finance",
        copilot="Finance Copilot",
        document_types=(
            ("Expense & Reimbursement Policy", ("expense", "reimbursement", "travel expense", "claim")),
            ("Invoice & Accounts Payable", ("invoice", "accounts payable", "ap", "vendor payment")),
            ("Finance Policy", ("finance policy", "budget", "accounting", "financial")),
        ),
        keywords=("finance", "expense", "reimbursement", "invoice", "accounting", "budget", "payment", "tax"),
    ),
    _DomainProfile(
        domain="Legal",
        copilot="Legal Copilot",
        document_types=(
            ("Contract", ("contract", "agreement", "nda", "master services", "statement of work")),
            ("Legal & Compliance Policy", ("legal", "compliance", "regulation", "regulatory", "privacy")),
        ),
        keywords=("legal", "contract", "agreement", "nda", "compliance", "regulatory", "clause", "law"),
    ),
    _DomainProfile(
        domain="IT Support",
        copilot="IT Support Copilot",
        document_types=(
            ("Troubleshooting Guide", ("troubleshooting", "error", "incident", "diagnostic", "fix")),
            ("IT Policy & Procedure", ("it policy", "password", "access", "service desk", "procedure")),
        ),
        keywords=("it support", "service desk", "ticket", "incident", "troubleshooting", "password", "network", "software"),
    ),
)


def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower().replace("_", " ").replace("-", " ")).strip()


class DocumentIntelligenceService:
    """Recommend the most likely enterprise Copilot for a document."""

    def classify(self, request: DocumentClassificationRequest) -> DocumentClassificationResponse:
        haystack = _normalise(f"{request.filename} {request.text}")
        ranked: list[tuple[int, _DomainProfile, list[str], str]] = []

        for profile in _PROFILES:
            domain_hits = [keyword for keyword in profile.keywords if keyword in haystack]
            best_type = "General Knowledge"
            best_type_hits: list[str] = []
            for document_type, signals in profile.document_types:
                hits = [signal for signal in signals if signal in haystack]
                if len(hits) > len(best_type_hits):
                    best_type = document_type
                    best_type_hits = hits
            score = (len(domain_hits) * 2) + (len(best_type_hits) * 3)
            ranked.append((score, profile, domain_hits + best_type_hits, best_type))

        ranked.sort(key=lambda item: item[0], reverse=True)
        score, profile, signals, document_type = ranked[0]
        second_score = ranked[1][0]

        if score == 0:
            confidence = 0.25
        else:
            # Conservative confidence: deterministic recommendations should
            # visibly remain uncertain when the evidence is weak or tied.
            confidence = min(0.98, 0.55 + (0.08 * min(score, 5)))
            if score == second_score:
                confidence = min(confidence, 0.55)

        return DocumentClassificationResponse(
            domain=profile.domain,
            document_type=document_type,
            confidence=round(confidence, 2),
            recommended_copilot=profile.copilot,
            matched_signals=signals[:8],
        )
