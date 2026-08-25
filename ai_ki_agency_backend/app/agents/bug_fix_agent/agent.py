from app.agents.base_agent import BaseAgent
from app.agents.bug_fix_agent.prompt import SYSTEM_PROMPT, build_user_prompt
from app.config import settings
from app.groq_client import call_llm_json


class BugFixAgent(BaseAgent):
    name = "bug_fix"

    def run(self, context: dict) -> dict:
        bug_report = context.get("bug_report") or {}

        # Cost-friendly short-circuit: if the free static-analysis stage
        # found nothing, don't spend a single token calling the LLM.
        if bug_report.get("clean"):
            coding = context.get("coding") or {}
            return {
                "files": coding.get("files", []),
                "fix_summary": [],
                "skipped_llm_call": True,
            }

        user_prompt = build_user_prompt(context)
        result = call_llm_json(
            SYSTEM_PROMPT,
            user_prompt,
            heavy=True,
            temperature=0.1,
            max_tokens=settings.max_tokens_bug_fix,
        )
        result.setdefault("skipped_llm_call", False)
        return result
