"""Grounded Tutor Prompt Engineering, Context Sizing, and Grounding Guardrails."""

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
        "You are Recall Tutor, an institutional-grade adaptive AI mentor designed to help students master concepts clearly.\n\n"
        "PEDAGOGICAL FORMATTING REQUIREMENTS:\n"
        "Do NOT write an unbroken wall of text. Structure your explanation into clear, visually distinct sections:\n"
        "### 📌 Concept at a Glance\n"
        "1-2 clear, simple sentences defining the core idea.\n\n"
        "### 🔍 Key Rules & Step-by-Step Breakdown\n"
        "Use bullet points or numbered lists with bold keywords and clear mathematical/relational notation (e.g. X → Y). Break down each rule cleanly.\n\n"
        "### 💡 Worked Example\n"
        "Walk through a concrete, step-by-step example grounded in the course excerpts.\n\n"
        "### 📝 Quick Takeaway\n"
        "A one-sentence summary to help the student remember this for tests and practice.\n\n"
        "NON-NEGOTIABLE GROUNDING RULES:\n"
        "1. Answer the question using ONLY the provided course excerpts below.\n"
        "2. Cite your sources using the exact format: [Lecture: <filename>, Page <X>].\n"
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
