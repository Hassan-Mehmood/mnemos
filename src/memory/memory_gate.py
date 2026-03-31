import re
from enum import Enum

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.core.config import get_settings

settings = get_settings()


class GateDecision(str, Enum):
    RETRIEVE = "RETRIEVE"
    SKIP = "SKIP"


class GateOutput(BaseModel):
    decision: GateDecision
    reason: str


GATE_PROMPT = """
You are a retrieval gate for a personal AI assistant.
Your ONLY job is to decide if answering a user message requires fetching personal context from memory.

Return RETRIEVE if answering well requires knowing personal context about the user, such as:
- Questions about themselves ("what's my name", "what are my goals", "who am i")
- Requests for personalised advice ("what should I learn next", "which framework should I use")
- Messages that reference their situation ("help me with my project", "based on my stack")
- Ambiguous requests where personal context changes the answer ("what should I do", "is this a good idea")
- Follow-up messages in a personal conversation ("what about me", "and in my case")

Return SKIP if the message can be answered well without knowing anything about the user, such as:
- Pure knowledge questions ("how does recursion work", "what is async/await")
- General task requests with no personal angle ("write a regex for emails", "explain binary trees")
- Math or factual lookups ("what is 15% of 340", "when was Python created")
- Hypothetical or roleplay scenarios ("pretend you are a Rust expert")
- Questions about someone else ("my friend wants to learn ML, where should they start")

The question to ask yourself:
Would knowing personal facts about this user change the answer meaningfully?
If yes → RETRIEVE. If no → SKIP.

Be aggressive about SKIP for pure knowledge questions.
Be aggressive about RETRIEVE when the message is personal or advice-seeking.

Message: {message}
"""


class MemoryGate:
    # Layer 1 — definite skips, never worth extracting
    HARD_SKIP_PATTERNS = [
        r"^(what|how|why|when|where|who|which|can you|could you|explain|tell me)\b",
        r"\bi'?m not sure\b",
        r"\bi'?m trying to understand\b",
        r"\bremember to\b",
        r"\bhelp me (understand|learn|explain|implement|fix|debug|write)\b",
        r"\bwhat (is|are|does|do|was|were)\b",
        r"\bhow (do|does|can|should|would|to)\b",
    ]

    # Layer 1 — definite extracts, always worth running extractor
    HARD_EXTRACT_PATTERNS = [
        r"\bi'?m a\b",
        r"\bi am a\b",
        r"\bi work (as|at|for|in)\b",
        r"\bmy (job|profession|occupation|career|role)\b",
        r"\bi prefer\b",
        r"\bi (love|hate|dislike|enjoy)\b",
        r"\bmy goal is\b",
        r"\bmy (main |current |side )?project\b",
        r"\bremember that\b",
        r"\bremember i\b",
        r"\bi (just |have )?(quit|joined|started|founded|cofounded|launched)\b",
    ]

    HARD_RETRIEVE_PATTERNS = [
        r"\bwhat('?s| is| are) my\b",  # "what's my name", "what are my goals"
        r"\bwho am i\b",
        r"\bdo you remember me\b",
        r"\bwhat do you know about me\b",
        r"\btell me about me\b",
    ]

    def __init__(self):
        self.llm_gate = Agent(
            model=OpenAIChatModel(
                settings.MEMORY_GATE_MODEL,
                provider=OpenAIProvider(api_key=settings.OPENAI_API_KEY),
            ),
            system_prompt=GATE_PROMPT,
            output_type=GateOutput,
        )

    async def should_retrieve(self, message: str) -> tuple[bool, str]:
        msg = message.lower().strip()

        for pattern in self.HARD_RETRIEVE_PATTERNS:
            if re.search(pattern, msg):
                return True, f"hard_retrieve: {pattern}"

        # Layer 1a — hard skip
        for pattern in self.HARD_SKIP_PATTERNS:
            if re.search(pattern, msg):
                return False, f"hard_skip: {pattern}"

        # Layer 1b — hard extract
        for pattern in self.HARD_EXTRACT_PATTERNS:
            if re.search(pattern, msg):
                return True, f"hard_extract: {pattern}"

        # Layer 2 — ambiguous, ask the LLM
        result = await self.llm_gate.run(message)
        return (
            result.output.decision == GateDecision.RETRIEVE,
            f"llm_gate: {result.output.reason}",
        )
