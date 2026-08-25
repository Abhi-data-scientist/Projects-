from app.agents.base_agent import BaseAgent
from app.agents.requirement_agent.prompt import SYSTEM_PROMPT, build_user_prompt
from app.groq_client import call_llm_json


class RequirementAgent(BaseAgent):
    name = "requirement"

    def run(self, context: dict) -> dict:
        user_prompt = build_user_prompt(context)
        return call_llm_json(SYSTEM_PROMPT, user_prompt, heavy=False)
