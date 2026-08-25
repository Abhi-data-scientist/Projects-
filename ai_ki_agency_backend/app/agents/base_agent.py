"""
Base class for every agent in the pipeline.

Each concrete agent lives in its own folder with:
  - prompt.py  -> SYSTEM_PROMPT + a build_user_prompt(context) function
                  (skipped for the two non-LLM agents: preview, bug_report)
  - agent.py   -> a class implementing run(context) -> dict

This keeps prompts fully isolated per agent, as requested, so you can
tune/version one agent's prompt without touching any other file.
"""
from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    name: str = "base"

    @abstractmethod
    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        context contains the original query, tech_hint, and every prior
        agent's output keyed by agent name, e.g.:

        {
          "query": "...",
          "tech_hint": "...",
          "requirement": {...},
          "architecture": {...},
          ...
        }

        Must return a JSON-serializable dict.
        """
        raise NotImplementedError
