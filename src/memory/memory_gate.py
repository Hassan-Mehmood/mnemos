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

Return RETRIEVE only if the message is ACTIVELY REQUESTING something that personal context would change:
- Explicit questions about themselves ("what's my name", "what are my goals", "who am i")
- Explicit requests for personalised advice ("what should I learn next", "which framework should I use")
- Messages that directly reference stored context ("based on my stack", "given my situation")
- Direct follow-up questions in a personal conversation ("what about me", "and in my case")

Return SKIP if:
- The message is a STATEMENT, even if personal ("I have been learning Python", "I just finished a project")
- The message is a pure knowledge question ("how does recursion work", "what is async/await")
- The message is a general task request ("write a regex", "explain binary trees")
- The message mentions personal activity but asks nothing ("I like football", "I work in fintech")
- Math or factual lookups ("what is 15% of 340", "when was Python created")
- Hypothetical or roleplay ("pretend you are a Rust expert")
- Questions about someone else ("my friend wants to learn ML")

CRITICAL RULE:
A statement about the user is NOT a retrieval trigger.
Only retrieve when the user is ASKING FOR SOMETHING that requires knowing who they are.

"I have been learning Python"     → SKIP  (statement, no request)
"What should I learn after Python?" → RETRIEVE  (request, needs their context)
"I just launched my SaaS"         → SKIP  (statement)
"How should I market my SaaS?"    → RETRIEVE  (request referencing their situation)

The question to ask yourself:
Is the user ASKING FOR SOMETHING right now, AND would knowing their personal history change the answer?
Both must be true. If either is false → SKIP.

Message: {message}
"""


class MemoryGate:
    # Layer 1 — definite skips, never worth extracting
    HARD_SKIP_PATTERNS = [
        # question starters
        r"^(what|how|why|when|where|who|which|can you|could you|explain|tell me)\b",
        r"^(is|are|was|were|does|do|did|has|have|had|will|would|should|could)\b",
        r"^(define|describe|list|show|give|find|calculate|compute|convert)\b",
        # uncertainty / learning signals
        r"\bi'?m not sure\b",
        r"\bi'?m trying to understand\b",
        r"\bremember to\b",
        r"\bi don'?t (know|understand|get)\b",
        r"\bcan you (explain|clarify|elaborate|describe|show)\b",
        # help requests with no personal angle
        r"\bhelp me (understand|learn|explain|implement|fix|debug|write|create|build|make|find|check)\b",
        r"\bhow (do|does|can|should|would|to)\b",
        r"\bwhat (is|are|does|do|was|were|would|will)\b",
        # pure knowledge questions
        r"\bwhat('?s| is| are) (a|an|the) \w+",  # "what is a closure", "what's a tensor"
        r"\b(difference between|compare|vs\.?|versus)\b",
        r"\b(example|examples) of\b",
        r"\bhow (does .+ work|to .+)\b",
        # coding / technical tasks
        r"\b(write|create|generate|build|implement|code|make) (a|an|the)?\b",
        r"\b(fix|debug|refactor|review|optimize|improve) (this|my|the|a)?\b",
        r"\bwhat('?s| is) (wrong|the (issue|problem|error|bug))\b",
        r"\b(error|exception|traceback|crash|failing)\b",
        # math / factual lookups
        r"^\d[\d\s\+\-\*\/\%\(\)]*",  # starts with a number
        r"\b(calculate|compute|convert|how many|how much)\b",
        r"\bwhat('?s| is) \d",  # "what's 15% of..."
        # about others, not the user
        r"\b(my friend|my colleague|my teammate|my boss|my client|someone)\b",
        r"\b(they|them|their|he|she|his|her) (want|need|is|are|should)\b",
        # hypothetical / roleplay
        r"\b(pretend|imagine|suppose|assume|hypothetically|what if|if you were)\b",
        r"\bact as\b",
        r"\brole ?play\b",
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
