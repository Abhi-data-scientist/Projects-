"""Router for Model Context Protocol (MCP) tool group specifications and execution."""

from fastapi import APIRouter
from pydantic import BaseModel

from core.logging import track_latency
from routers.documents import rag_tools
from routers.research import web_research_engine
from modules.web_research import WebResearchToolGroup

router = APIRouter(prefix="/api/mcp", tags=["mcp"])

web_research_tools = WebResearchToolGroup(web_research_engine)


class MCPToolCallRequest(BaseModel):
    name: str
    arguments: dict = {}


@router.get("/tools")
@track_latency
def get_mcp_tools() -> dict:
    """Return Model Context Protocol (MCP) tool group specification."""
    return {
        "tools": rag_tools.get_tool_definitions() + web_research_tools.get_tool_definitions(),
    }


@router.post("/tools/call")
@track_latency
async def call_mcp_tool(request: MCPToolCallRequest) -> dict:
    """Execute an MCP tool call (RAG or Web Research)."""
    web_tool_names = {"search_web", "scrape_webpage", "fetch_page", "compare_sources"}
    if request.name in web_tool_names:
        return await web_research_tools.execute_tool(request.name, request.arguments)
    return rag_tools.execute_tool(request.name, request.arguments)
