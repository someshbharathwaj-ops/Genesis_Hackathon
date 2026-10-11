"""Grounded Revisor Prompt Engineering, Evidence Verification, and Adversarial Audit."""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.modules.adaptive_learning.dbms_engine import (
    compute_attribute_closure,
)
from app.modules.knowledge_engine.retrieval_engine import RetrievalMatch


class GroundedAuditStatus(str, Enum):
    """Authoritative audit verdict from the Revisor."""

    VERIFIED_GROUNDED = "verified_grounded"
    UNGROUNDED_CLAIM_DETECTED = "ungrounded_claim_detected"
    CONTRADICTION_DETECTED = "contradiction_detected"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass
class AssembledRevisorPrompt:
    """Bounded Revisor prompt ready for SLM execution."""

    system_prompt: str
    user_prompt: str
    citations: list[str]
    candidate_text: str
    query_or_topic: str
    total_characters: int
    truncated: bool


@dataclass
class RevisorAuditResult:
    """Structured audit outcome produced by the Revisor engine."""

    audit_status: GroundedAuditStatus
    is_approved: bool
    summary: str
    verified_points: list[str]
    flagged_issues: list[str]
    suggested_revision: str | None
    citations_verified: list[str]
    abstention_recommended: bool
    raw_model_text: str
    deterministic_checks: dict[str, Any] = field(default_factory=dict)


class RevisorEngine:
    """Evidence Reviewer and Adversarial Challenger coordinating grounded audits."""

    MAX_CONTEXT_CHARACTERS: int = 12000
    MAX_EXCERPTS: int = 5

    SYSTEM_PROMPT: str = (
        "You are Recall Revisor, an institutional-grade evidence reviewer and "
        "adversarial auditor.\n"
        "Your task is to independently audit candidate pedagogical explanations, student claims, "
        "or misconception statements against official course excerpts.\n\n"
        "NON-NEGOTIABLE AUDIT RULES:\n"
        "1. Compare every assertion in the candidate text against official course excerpts.\n"
        "2. Output an audit verdict:\n"
        "   - VERIFIED_GROUNDED: All claims are fully backed by excerpts with citations.\n"
        "   - UNGROUNDED_CLAIM_DETECTED: Contains statements not found in excerpts.\n"
        "   - CONTRADICTION_DETECTED: Directly contradicts official course excerpts.\n"
        "   - INSUFFICIENT_EVIDENCE: Excerpts do not contain enough facts to evaluate.\n"
        "3. Provide explicit bullet points for verified claims and flagged issues.\n"
        "4. Provide a corrected, grounded revision citing [Lecture: <filename>, Page <X>].\n"
        "5. You have ZERO authority over grading, student mastery scores, or diagnostic outcomes."
    )

    ABSTENTION_MESSAGE: str = (
        "Course excerpts do not contain sufficient verified evidence to audit or substantiate "
        "the candidate text. In accordance with Recall's grounding policy, the Revisor abstains "
        "from validating unverified claims."
    )

    @classmethod
    def assemble_prompt(
        cls,
        candidate_text: str,
        query_or_topic: str,
        matches: list[RetrievalMatch],
        max_context_chars: int | None = None,
    ) -> AssembledRevisorPrompt:
        """Assemble bounded audit prompt with excerpts, candidate text, and audit rubric."""
        limit = max_context_chars or cls.MAX_CONTEXT_CHARACTERS
        selected_matches = matches[: cls.MAX_EXCERPTS]
        citations: list[str] = []

        excerpts_text_parts: list[str] = []
        current_len = 0
        truncated = False

        for i, match in enumerate(selected_matches, start=1):
            chunk_header = f"--- OFFICIAL EXCERPT {i} [{match.citation}] ---\n"
            chunk_body = match.content.strip() + "\n\n"
            chunk_text = chunk_header + chunk_body

            if current_len + len(chunk_text) > limit:
                if not excerpts_text_parts:
                    available = limit - len(chunk_header) - 10
                    if available > 50:
                        chunk_text = chunk_header + chunk_body[:available] + "...\n\n"
                        excerpts_text_parts.append(chunk_text)
                        citations.append(match.citation)
                truncated = True
                break

            excerpts_text_parts.append(chunk_text)
            citations.append(match.citation)
            current_len += len(chunk_text)

        excerpts_block = "".join(excerpts_text_parts).strip()

        user_prompt = (
            f"OFFICIAL COURSE EXCERPTS:\n{excerpts_block}\n\n"
            f"SUBJECT / TOPIC:\n{query_or_topic.strip()}\n\n"
            f"CANDIDATE TEXT UNDER REVIEW:\n{candidate_text.strip()}\n\n"
            "INSTRUCTIONS FOR AUDIT REPORT:\n"
            "Format your response as follows:\n"
            "STATUS: [VERIFIED_GROUNDED | UNGROUNDED_CLAIM_DETECTED | "
            "CONTRADICTION_DETECTED | INSUFFICIENT_EVIDENCE]\n"
            "SUMMARY: <Concise executive summary of grounding audit>\n"
            "VERIFIED POINTS:\n- <Point 1>\n"
            "FLAGGED ISSUES:\n- <Issue 1 (or 'None' if verified)>\n"
            "SUGGESTED REVISION:\n<Corrected revision with source citations [Lecture: ...], "
            "or 'None needed'>\n"
        )

        unique_citations = list(dict.fromkeys(citations))

        return AssembledRevisorPrompt(
            system_prompt=cls.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            citations=unique_citations,
            candidate_text=candidate_text,
            query_or_topic=query_or_topic,
            total_characters=len(user_prompt),
            truncated=truncated,
        )

    @classmethod
    def parse_model_output(
        cls,
        model_text: str,
        citations: list[str],
        deterministic_checks: dict[str, Any] | None = None,
    ) -> RevisorAuditResult:
        """Parse SLM audit output into a structured RevisorAuditResult."""
        det_checks = deterministic_checks or {}
        raw = model_text.strip()

        det_contradiction = det_checks.get("contradiction_detected", False)
        det_contradiction_details = det_checks.get("contradiction_reason")

        # 1. Determine status
        status = GroundedAuditStatus.VERIFIED_GROUNDED
        lower_raw = raw.lower()

        if "insufficient_evidence" in lower_raw or "abstain" in lower_raw:
            status = GroundedAuditStatus.INSUFFICIENT_EVIDENCE
        elif (
            det_contradiction
            or "contradiction_detected" in lower_raw
            or "contradiction" in lower_raw
        ):
            status = GroundedAuditStatus.CONTRADICTION_DETECTED
        elif (
            "ungrounded_claim_detected" in lower_raw
            or "ungrounded" in lower_raw
            or "unsupported" in lower_raw
        ):
            status = GroundedAuditStatus.UNGROUNDED_CLAIM_DETECTED
        elif "verified_grounded" in lower_raw or "verified" in lower_raw:
            status = GroundedAuditStatus.VERIFIED_GROUNDED

        # 2. Extract sections using regex
        summary = ""
        sum_pat = r"SUMMARY:\s*(.*?)(?=\n[A-Z\s]+:|$)"
        summary_match = re.search(sum_pat, raw, re.DOTALL | re.IGNORECASE)
        if summary_match:
            summary = summary_match.group(1).strip()
        else:
            first_line = raw.split("\n")[0].strip()
            summary = first_line if len(first_line) > 5 else "Audit completed."

        verified_points: list[str] = []
        vp_pat = r"VERIFIED POINTS:\s*(.*?)(?=\n[A-Z\s]+:|$)"
        vp_match = re.search(vp_pat, raw, re.DOTALL | re.IGNORECASE)
        if vp_match:
            lines = vp_match.group(1).strip().split("\n")
            verified_points = [
                line.lstrip("-*• ").strip()
                for line in lines
                if line.strip() and not line.strip().lower().startswith("none")
            ]

        flagged_issues: list[str] = []
        if det_contradiction and det_contradiction_details:
            flagged_issues.append(f"Deterministic logic failure: {det_contradiction_details}")

        fi_pat = r"FLAGGED ISSUES:\s*(.*?)(?=\n[A-Z\s]+:|$)"
        fi_match = re.search(fi_pat, raw, re.DOTALL | re.IGNORECASE)
        if fi_match:
            lines = fi_match.group(1).strip().split("\n")
            parsed_issues = [
                line.lstrip("-*• ").strip()
                for line in lines
                if line.strip() and not line.strip().lower().startswith("none")
            ]
            flagged_issues.extend(parsed_issues)

        suggested_revision: str | None = None
        sr_pat = r"SUGGESTED REVISION:\s*(.*?)$"
        sr_match = re.search(sr_pat, raw, re.DOTALL | re.IGNORECASE)
        if sr_match:
            cand = sr_match.group(1).strip()
            if cand and not cand.lower().startswith("none"):
                suggested_revision = cand

        found_citations = re.findall(r"\[Lecture:[^\]]+\]", raw)
        valid_citations = [c for c in dict.fromkeys(found_citations) if c in citations]
        if not valid_citations and citations and status == GroundedAuditStatus.VERIFIED_GROUNDED:
            valid_citations = citations

        is_approved = (
            status == GroundedAuditStatus.VERIFIED_GROUNDED
            and not flagged_issues
            and not det_contradiction
        )

        return RevisorAuditResult(
            audit_status=status,
            is_approved=is_approved,
            summary=summary,
            verified_points=verified_points,
            flagged_issues=flagged_issues,
            suggested_revision=suggested_revision,
            citations_verified=valid_citations,
            abstention_recommended=(status == GroundedAuditStatus.INSUFFICIENT_EVIDENCE),
            raw_model_text=raw,
            deterministic_checks=det_checks,
        )

    @classmethod
    def verify_deterministic_claims(cls, candidate_text: str) -> dict[str, Any]:
        """Verify mathematical and relational database assertions using deterministic logic."""
        checks: dict[str, Any] = {"inspected": True, "contradiction_detected": False}

        # Check for attribute closure claims
        pattern = (
            r"closure of\s*\{?([A-Za-z,\s]+)\}?\s*(?:under|with respect to)?.*?"
            r"([A-Za-z\s,\->]+)\s*is\s*\{?([A-Za-z,\s]+)\}?"
        )
        closure_match = re.search(pattern, candidate_text, re.IGNORECASE)
        if closure_match:
            attrs = {a.strip().upper() for a in closure_match.group(1).split(",") if a.strip()}
            claimed_closure = {
                a.strip().upper() for a in closure_match.group(3).split(",") if a.strip()
            }
            fd_str = closure_match.group(2)
            fd_pairs = re.findall(r"([A-Za-z]+)\s*->\s*([A-Za-z]+)", fd_str)
            if fd_pairs and attrs and claimed_closure:
                fds: list[tuple[frozenset[str], frozenset[str]]] = [
                    (frozenset(a.upper() for a in lhs), frozenset(b.upper() for b in rhs))
                    for lhs, rhs in fd_pairs
                ]
                actual_closure = compute_attribute_closure(attrs, fds)
                if actual_closure != claimed_closure:
                    checks["contradiction_detected"] = True
                    checks["contradiction_reason"] = (
                        f"Claimed closure of {attrs} was {claimed_closure}, but deterministic "
                        f"closure under {fd_pairs} is {actual_closure}."
                    )
                    checks["actual_closure"] = sorted(actual_closure)
                    checks["claimed_closure"] = sorted(claimed_closure)

        return checks
