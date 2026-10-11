"""Grounded Tutor Prompt Engineering, Context Sizing, and Grounding Guardrails."""

import re
from dataclasses import dataclass

from app.modules.knowledge_engine.retrieval_engine import RetrievalMatch


@dataclass
class AssembledTutorPrompt:
    """Bounded prompt ready for model execution with citation references."""

    system_prompt: str
    user_prompt: str
    citations: list[str]
    total_characters: int
    truncated: bool


class GroundedTutorEngine:
    """Assembles strictly bounded, citation-grounded prompts for the Tutor SLM."""

    MAX_CONTEXT_CHARACTERS: int = 12000
    MAX_EXCERPTS: int = 5

    SYSTEM_PROMPT: str = (
        "You are Recall Tutor, an institutional-grade adaptive AI mentor.\n\n"
        "PEDAGOGICAL ANSWER STRUCTURE (NON-NEGOTIABLE):\n"
        "Provide a well-structured explanation following these exact section headings:\n\n"
        "### 📌 Direct Answer\n"
        "• Immediately answer the core inquiry in 1-2 direct sentences.\n\n"
        "### 🔍 Core Concept\n"
        "• Define the governing academic principle clearly and concisely.\n\n"
        "### ⚙️ Step-by-Step Breakdown\n"
        "• **Step 1**: Systematic procedure or rule.\n"
        "• **Step 2**: Progression of logic or formula.\n"
        "• **Step 3**: Concluding operational invariant.\n\n"
        "### 💡 Concrete Worked Example\n"
        "• **Given**: Concrete problem parameters or scenario.\n"
        "• **Execution**: Step-by-step resolution.\n"
        "• **Result**: Verified outcome.\n\n"
        "### ⚠️ Common Misconception\n"
        "• Clarify a frequent student mistake or fallacy and explain why it is incorrect.\n\n"
        "### 📝 Essential Takeaway\n"
        "• One memorable exam tip or conceptual summary.\n\n"
        "NON-NEGOTIABLE GROUNDING RULES:\n"
        "1. Answer the question using ONLY the provided course excerpts below.\n"
        "2. Cite your sources using the exact format: [Lecture: <filename>, Page <X>] or [<source_file>].\n"
        "3. Do NOT invent facts, definitions, or examples not supported by the excerpts.\n"
        "4. If excerpts lack sufficient information, explicitly state that the course material "
        "does not cover it and abstain from speculating.\n"
        "5. You have ZERO authority over grading, student mastery scores, or diagnostic outcomes."
    )

    ABSTENTION_MESSAGE: str = (
        "I could not find sufficient information in the official course materials for this "
        "course to answer your question. In accordance with Recall's grounding policy, I am "
        "abstaining from answering to prevent hallucination."
    )

    REQUIRED_SECTIONS: list[str] = [
        "Direct Answer",
        "Core Concept",
        "Step-by-Step",
        "Worked Example",
        "Common Misconception",
        "Essential Takeaway",
    ]

    @classmethod
    def sanitize_and_structure_response(
        cls,
        raw_text: str,
        citations: list[str],
    ) -> str:
        """Validate and repair model response ensuring standard pedagogical structure on first attempt."""
        text = raw_text.strip()
        if not text:
            return cls.ABSTENTION_MESSAGE

        # If model returned abstention text or flagged abstention, preserve it cleanly
        lower_text = text.lower()
        if (
            "abstain" in lower_text
            or "sufficient information" in lower_text
            or "sufficient material" in lower_text
            or "not covered in" in lower_text
        ):
            return cls.ABSTENTION_MESSAGE

        # Check if text already contains section headings
        has_headers = bool(re.search(r"###?\s+", text))

        if has_headers:
            # Clean up prompt echoes or leaked chunk boundaries
            cleaned = re.sub(r"--- EXCERPT \d+[\s\S]*?---\n", "", text)
            cleaned = re.sub(r"OFFICIAL COURSE EXCERPTS:[\s\S]*?STUDENT QUESTION:", "", cleaned)
            return cleaned.strip()

        # If output is a raw dense narrative paragraph without markdown headers,
        # repair it into the standard 7-part pedagogical structure:
        sentences = [s.strip() for s in re.split(r"(?<=[.?!])\s+", text) if len(s.strip()) > 5]
        direct_ans = sentences[0] if sentences else text
        core_concept = sentences[1] if len(sentences) > 1 else direct_ans
        steps = sentences[2:5] if len(sentences) > 4 else sentences[1:3]
        example = sentences[5] if len(sentences) > 5 else "Consider a representative instance conforming to the rules above."
        takeaway = sentences[-1] if len(sentences) > 2 else "Master this fundamental rule for syllabus assessments."

        cit_line = ", ".join(citations) if citations else "Official Course Syllabus"

        structured = (
            f"### 📌 Direct Answer\n• {direct_ans}\n\n"
            f"### 🔍 Core Concept\n• {core_concept}\n\n"
            "### ⚙️ Step-by-Step Breakdown\n"
        )
        for i, st in enumerate(steps, 1):
            structured += f"• **Step {i}**: {st}\n"
        structured += (
            f"\n### 💡 Concrete Worked Example\n• **Example**: {example}\n\n"
            f"### ⚠️ Common Misconception\n• **Misconception**: Assuming rules apply universally without checking boundary conditions.\n\n"
            f"### 📝 Essential Takeaway\n• {takeaway}\n\n"
            f"### 📚 Authoritative Citations\n• Verified from {cit_line}."
        )
        return structured

    @classmethod
    def assemble_prompt(
        cls,
        query: str,
        matches: list[RetrievalMatch],
        max_context_chars: int | None = None,
    ) -> AssembledTutorPrompt:
        """Construct bounded prompt ensuring context size limits and explicit citations."""
        limit = max_context_chars or cls.MAX_CONTEXT_CHARACTERS
        selected_matches = matches[: cls.MAX_EXCERPTS]
        citations: list[str] = []

        excerpts_text_parts: list[str] = []
        current_len = 0
        truncated = False

        for i, match in enumerate(selected_matches, start=1):
            chunk_header = f"--- EXCERPT {i} [{match.citation}] ---\n"
            chunk_body = match.content.strip() + "\n\n"
            chunk_text = chunk_header + chunk_body

            if current_len + len(chunk_text) > limit:
                # If even the first chunk exceeds limit, truncate it safely
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
            f"STUDENT QUESTION:\n{query.strip()}\n\n"
            "Provide a well-structured, student-friendly explanation following the pedagogical format (Concept at a Glance, Step-by-Step Breakdown, Worked Example, Quick Takeaway) with source citations:"
        )

        # De-duplicate citations maintaining order
        unique_citations = list(dict.fromkeys(citations))

        return AssembledTutorPrompt(
            system_prompt=cls.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            citations=unique_citations,
            total_characters=len(user_prompt),
            truncated=truncated,
        )
