"""Router for Document Library and RAG knowledge base management."""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from core.logging import logger, track_latency
from modules.rag import PersonalRAGKnowledgeBase, RAGToolGroup

router = APIRouter(prefix="/api/documents", tags=["documents"])

knowledge_base = PersonalRAGKnowledgeBase()
rag_tools = RAGToolGroup(knowledge_base)


class DocumentSearchRequest(BaseModel):
    query: str
    top_k: int = 3
    doc_id: str | None = None


@router.post("/upload")
@track_latency
async def upload_document(file: UploadFile = File(...)) -> dict:
    """Upload and ingest a PDF document into the personal vector knowledge base."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(file_bytes) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds maximum limit of 25MB.")

    try:
        meta = knowledge_base.ingest_pdf(file_bytes, file.filename)
        return {
            "status": "success",
            "message": f"Successfully ingested '{file.filename}'",
            "document": meta,
        }
    except Exception as exc:
        logger.exception("document_upload_failed filename=%s", file.filename)
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {exc}") from exc


@router.get("")
@track_latency
def list_documents() -> dict:
    """List all documents in the personal knowledge base."""
    docs = rag_tools.list_documents()
    return {"status": "success", "count": len(docs), "documents": docs}


@router.get("/{doc_id}")
@track_latency
def get_document(doc_id: str) -> dict:
    """Get metadata and chunk details for a specific document."""
    try:
        details = rag_tools.get_document_details(doc_id)
        return {"status": "success", "document": details}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Document with ID '{doc_id}' not found.")


@router.post("/search")
@track_latency
def search_documents(request: DocumentSearchRequest) -> dict:
    """Search documents using semantic vector similarity."""
    results = rag_tools.search_documents(
        query=request.query,
        top_k=request.top_k,
        doc_id=request.doc_id,
    )
    return {
        "status": "success",
        "query": request.query,
        "count": len(results),
        "results": results,
    }


@router.delete("/{doc_id}")
@track_latency
def delete_document(doc_id: str) -> dict:
    """Delete a document and its chunks from the knowledge base."""
    success = knowledge_base.delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    return {"status": "success", "message": f"Document '{doc_id}' deleted."}
