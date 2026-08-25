from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings
from app.pipeline import run_requested_agent
from app.schemas import PipelineRequest, PipelineResponse
from app.session_store import create_session, get_session

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("", response_model=PipelineResponse)
def pipeline(payload: PipelineRequest) -> PipelineResponse:
    """Start a chat session or run exactly one selected pipeline agent."""
    if payload.action == "start":
        session = create_session(payload.query or "", payload.tech_hint)
        return PipelineResponse(
            message="Session created. Run the Requirement Agent to begin.",
            session=session,
        )

    session = get_session(payload.session_id or "")
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if payload.action == "download":
        return _download_artifact(session, payload.artifact or "")

    try:
        result = run_requested_agent(session, payload.agent or "")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return PipelineResponse(
        message=f"{result.agent.replace('_', ' ').title()} Agent finished with status: {result.status}.",
        session=session,
        agent_result=result,
    )


def _download_artifact(session, artifact_id: str) -> FileResponse:
    for result in session.results.values():
        if result.status != "success" or not isinstance(result.output, dict):
            continue
        for artifact in result.output.get("downloads", []):
            if artifact.get("id") != artifact_id:
                continue
            filename = artifact.get("filename", "")
            if not filename or Path(filename).name != filename:
                break
            path = settings.generated_path(filename)
            if not path.is_file():
                break
            media_type = "application/pdf" if artifact.get("kind") == "pdf" else "application/zip"
            return FileResponse(path, media_type=media_type, filename=filename)
    raise HTTPException(status_code=404, detail="Requested download is not available")
