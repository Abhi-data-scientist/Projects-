"""
Pipeline orchestrator.

Runs agents in order, threading each agent's output into the shared
context so later agents can read everything produced so far - exactly the
"each agent uses the previous agent's output" behaviour requested.

Order (deliberately different from a literal 1-8 reading of the spec):
requirement -> architecture -> tools -> cost -> preview -> coding
-> bug_report -> bug_fix
-> package

Preview sits right after cost because it renders a proposal PDF of the
plan (requirements/architecture/tools/cost) - before any code is written.
Coding, then the two bug-handling agents, follow.
"""
import logging
from typing import Any

from app.agents.architecture_agent.agent import ArchitectureAgent
from app.agents.bug_fix_agent.agent import BugFixAgent
from app.agents.bug_report_agent.agent import BugReportAgent
from app.agents.coding_agent.agent import CodingAgent
from app.agents.cost_agent.agent import CostAgent
from app.agents.preview_agent.agent import PreviewAgent
from app.agents.package_agent.agent import PackageAgent
from app.agents.requirement_agent.agent import RequirementAgent
from app.agents.tools_agent.agent import ToolsAgent
from app.schemas import AgentResult, SessionState
from app.session_store import save_session

logger = logging.getLogger("ai_ki_agency.pipeline")

PIPELINE_ORDER: list[tuple[str, Any]] = [
    ("requirement", RequirementAgent),
    ("architecture", ArchitectureAgent),
    ("tools", ToolsAgent),
    ("cost", CostAgent),
    ("preview", PreviewAgent),
    ("coding", CodingAgent),
    ("bug_report", BugReportAgent),
    ("bug_fix", BugFixAgent),
    ("package", PackageAgent),
]


def _build_context(state: SessionState) -> dict:
    context: dict[str, Any] = {
        "session_id": state.session_id,
        "query": state.query,
        "tech_hint": state.tech_hint,
    }
    for name, result in state.results.items():
        if result.status == "success":
            context[name] = result.output
    return context


def run_agent_stage(state: SessionState, stage_name: str, agent_cls) -> AgentResult:
    context = _build_context(state)
    try:
        output = agent_cls().run(context)
        _attach_downloads(state, stage_name, output)
        result = AgentResult(agent=stage_name, status="success", output=output)
    except Exception as exc:  # noqa: BLE001 - surface every agent failure to the frontend
        logger.exception("Agent '%s' failed", stage_name)
        result = AgentResult(agent=stage_name, status="error", output=None, error=str(exc))

    state.results[stage_name] = result
    state.completed_stage = stage_name
    save_session(state)
    return result


def _attach_downloads(state: SessionState, stage_name: str, output: dict) -> None:
    """Add download metadata as soon as an artifact-producing stage finishes."""
    if stage_name == "preview":
        output["downloads"] = [
            {
                "id": "preview_pdf",
                "label": "Download preview PDF",
                "filename": output["pdf_filename"],
                "kind": "pdf",
            }
        ]
        return

    coding = (state.results.get("coding").output if state.results.get("coding") else {}) or {}
    coding_files = coding.get("files") or []
    if stage_name == "coding":
        output["downloads"] = [
            PackageAgent.create_archive(
                state.session_id,
                "coding_zip",
                "coding",
                output.get("files") or [],
                label="Download generated code ZIP",
            )
        ]
    elif stage_name == "bug_report":
        output["downloads"] = [
            PackageAgent.create_archive(
                state.session_id,
                "bug_report_zip",
                "bug_report",
                coding_files,
                label="Download code + bug report ZIP",
                extra_files={"bug-report.json": PackageAgent.report_json(output)},
            )
        ]
    elif stage_name == "bug_fix":
        output["downloads"] = [
            PackageAgent.create_archive(
                state.session_id,
                "bug_fix_zip",
                "bug_fix",
                output.get("files") or coding_files,
                label="Download bug-fixed code ZIP",
            )
        ]


def run_requested_agent(state: SessionState, stage_name: str) -> AgentResult:
    """Run one stage only, after every earlier stage has succeeded."""
    stages = [name for name, _ in PIPELINE_ORDER]
    try:
        index = stages.index(stage_name)
    except ValueError as exc:
        raise ValueError(f"Unknown agent: {stage_name}") from exc

    existing = state.results.get(stage_name)
    if existing and existing.status == "success":
        raise ValueError(f"Agent '{stage_name}' has already completed for this session.")

    if index:
        required_stage = stages[index - 1]
        required_result = state.results.get(required_stage)
        if not required_result or required_result.status != "success":
            raise ValueError(f"Run '{required_stage}' successfully before '{stage_name}'.")

    _, agent_cls = PIPELINE_ORDER[index]
    return run_agent_stage(state, stage_name, agent_cls)
