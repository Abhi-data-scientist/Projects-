from app.agents.base_agent import BaseAgent
from app.agents.architecture_agent.prompt import SYSTEM_PROMPT, build_user_prompt
from app.groq_client import call_llm_json


class ArchitectureAgent(BaseAgent):
    name = "architecture"

    def run(self, context: dict) -> dict:
        user_prompt = build_user_prompt(context)
        # Architecture benefits from the stronger model - it's the backbone
        # every later stage (including generated code) depends on.
        return call_llm_json(SYSTEM_PROMPT, user_prompt, heavy=True)
