from app.agents.base_agent import BaseAgent
from app.agents.coding_agent.prompt import SYSTEM_PROMPT, build_user_prompt
from app.config import settings
from app.groq_client import call_llm_json


class CodingAgent(BaseAgent):
    name = "coding"

    def run(self, context: dict) -> dict:
        user_prompt = build_user_prompt(context)
        # Code quality matters most here - use the heavy model.
        return call_llm_json(
            SYSTEM_PROMPT,
            user_prompt,
            heavy=True,
            temperature=0.15,
            max_tokens=settings.max_tokens_coding,
        )
