"""
Central configuration.

Everything cost-related (which model each agent uses, token ceilings) lives
here so you can tune spend in one place without touching agent code.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str = ""

    # Two model tiers -> cost control. Light model handles structured,
    # short-reasoning tasks (requirements, tools, cost). Heavy model is
    # reserved for architecture + actual code generation + bug fixing,
    # where quality really matters.
    groq_model_light: str = "openai/gpt-oss-20b"
    groq_model_heavy: str = "openai/gpt-oss-120b"

    # GPT-OSS uses part of the completion budget for reasoning; 1024 can end
    # before it produces a complete JSON object even for short planning tasks.
    max_tokens_light: int = 4096
    max_tokens_heavy: int = 2048
    # Full source files can exceed the concise planning-agent budget.
    max_tokens_coding: int = 8192
    max_tokens_bug_fix: int = 8192
    max_tokens_json_retry: int = 8192

    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5500"
    open_browser_on_start: bool = True

    # Where the (non-LLM) Preview Agent writes generated PDFs
    generated_dir: str = str(PROJECT_ROOT / "generated")

    def generated_path(self, filename: str) -> Path:
        """Return a generated-file path and create its parent directory."""
        directory = Path(self.generated_dir).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        return directory / filename

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
