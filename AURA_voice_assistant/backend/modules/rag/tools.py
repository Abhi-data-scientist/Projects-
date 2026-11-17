"""MCP Tool Group for Personal RAG Knowledge Base.

Implements Model Context Protocol (MCP) tool schemas and execution handlers
for:
1. search_documents
2. list_documents
3. get_document_details
"""

from __future__ import annotations

import json
from typing import Any

from core.logging import logger, track_latency
from modules.rag.engine import PersonalRAGKnowledgeBase


class RAGToolGroup:
    """Model Context Protocol (MCP) tool group for Personal Document RAG."""

    def __init__(self, knowledge_base: PersonalRAGKnowledgeBase) -> None:
        self.kb = knowledge_base

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Return MCP-compliant tool definitions with standard JSON Schemas."""
        return [
            {
                "name": "search_documents",
                "description": (
                    "Search user's uploaded personal documents and PDF knowledge base for relevant passages, "
                    "facts, or answers matching a query. Returns ranked text chunks with page numbers and relevance scores."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query or topic to look up in the documents.",
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Maximum number of relevant chunks to retrieve (default: 3).",
                            "default": 3,
                        },
                        "doc_id": {
                            "type": "string",
                            "description": "Optional specific document ID to limit the search scope to.",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "list_documents",
                "description": (
                    "List all personal PDF documents available in the knowledge base, including "
                    "document names, IDs, page counts, and upload timestamps."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "name": "get_document_details",
                "description": (
                    "Retrieve comprehensive metadata, page counts, total chunks, and sample snippets "
                    "for a specific uploaded document by its doc_id."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "doc_id": {
                            "type": "string",
                            "description": "The unique document ID to fetch details for.",
                        },
                    },
                    "required": ["doc_id"],
                },
            },
        ]

    def get_groq_tools(self) -> list[dict[str, Any]]:
        """Return OpenAI/Groq function calling format for the tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["inputSchema"],
                },
            }
            for t in self.get_tool_definitions()
        ]

    @track_latency
    def search_documents(
        self,
        query: str,
        top_k: int = 3,
        doc_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute search_documents tool directly."""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query argument must be a non-empty string.")
        return self.kb.search_documents(query=query.strip(), top_k=top_k, doc_id=doc_id)

    def list_documents(self) -> list[dict[str, Any]]:
        """Execute list_documents tool directly."""
        return self.kb.list_documents()

    def get_document_details(self, doc_id: str) -> dict[str, Any]:
        """Execute get_document_details tool directly."""
        if not doc_id or not isinstance(doc_id, str):
            raise ValueError("doc_id argument must be a non-empty string.")
        return self.kb.get_document_details(doc_id)

    @track_latency
    def execute_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """MCP standard tool execution handler.

        Returns MCP-compliant response:
        {"content": [{"type": "text", "text": "..."}], "isError": bool}
        """
        args = arguments or {}
        try:
            if name == "search_documents":
                query = args.get("query", "")
                top_k = int(args.get("top_k", 3))
                doc_id = args.get("doc_id")
                results = self.search_documents(query=query, top_k=top_k, doc_id=doc_id)
                formatted = json.dumps(
                    {
                        "query": query,
                        "matches_found": len(results),
                        "results": results,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                return {"content": [{"type": "text", "text": formatted}], "isError": False}

            elif name == "list_documents":
                docs = self.list_documents()
                formatted = json.dumps(
                    {
                        "total_documents": len(docs),
                        "documents": docs,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                return {"content": [{"type": "text", "text": formatted}], "isError": False}

            elif name == "get_document_details":
                doc_id = args.get("doc_id", "")
                details = self.get_document_details(doc_id=doc_id)
                formatted = json.dumps(details, ensure_ascii=False, indent=2)
                return {"content": [{"type": "text", "text": formatted}], "isError": False}

            else:
                error_msg = f"Unknown tool: '{name}'. Supported tools: search_documents, list_documents, get_document_details"
                logger.warning("mcp_unknown_tool name=%s", name)
                return {
                    "content": [{"type": "text", "text": error_msg}],
                    "isError": True,
                }

        except KeyError as ke:
            return {"content": [{"type": "text", "text": f"Not found: {ke}"}], "isError": True}
        except Exception as exc:
            logger.exception("mcp_tool_execution_failed name=%s", name)
            return {"content": [{"type": "text", "text": f"Tool execution error: {exc}"}], "isError": True}
