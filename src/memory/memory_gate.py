import re
from enum import Enum

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.groq import GroqProvider

from src.core.config import get_settings

settings = get_settings()


class GateDecision(str, Enum):
    EXTRACT = "EXTRACT"
    SKIP = "SKIP"


class GateOutput(BaseModel):
    decision: GateDecision
    reason: str


GATE_PROMPT = """
You are a memory gate for a personal AI assistant.
Your ONLY job is to decide if a user message contains personal facts worth remembering long-term.

Return EXTRACT if the message contains:
- Personal identity facts ("I'm a backend engineer", "I cofounded a startup")
- Preferences or opinions about their own choices ("I prefer Python", "I hate meetings")
- Goals or intentions ("I want to transition into AI", "I'm trying to get promoted")
- Current projects or work context ("I'm building a SaaS", "just switched my stack to Go")
- Constraints or life context ("I only have weekends", "I work at a small startup")

Return SKIP if the message is:
- A general question ("how does recursion work", "what is async/await")
- A task request with no personal context ("help me understand binary trees")
- About someone else ("my friend thinks I should learn Rust")
- Hypothetical or roleplay ("pretend you are a Python expert")
- Uncertain/weak signal ("I'm not sure about this")

Be aggressive about SKIP. When in doubt, SKIP.
Only EXTRACT when there is a clear, unambiguous personal fact.

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

    def __init__(self):
        self.llm_gate = Agent(
            model=GroqModel(
                "llama-3.1-8b-instant",  # fast + cheap, not your main model
                provider=GroqProvider(api_key=settings.GROQ_API_KEY),
            ),
            system_prompt=GATE_PROMPT,
            output_type=GateOutput,
        )

    async def should_extract(self, message: str) -> tuple[bool, str]:
        msg = message.lower().strip()

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
            result.output.decision == GateDecision.EXTRACT,
            f"llm_gate: {result.output.reason}",
        )
