"""Document read endpoint (scenario 1: path traversal, CWE-22)."""
import os

from fastapi import APIRouter, HTTPException

router = APIRouter()

BASE_DIR = os.path.abspath(os.getenv("DOCS_DIR", "/app/public_docs"))


@router.get("/api/v1/documents/read")
def read_document(file: str = ""):
    if not file:
        raise HTTPException(status_code=400, detail="Missing required query parameter: 'file'")

    target_path = os.path.join(BASE_DIR, file)

    if not os.path.isfile(target_path):
        raise HTTPException(status_code=404, detail=f"File '{file}' not found.")

    with open(target_path, "r", errors="ignore") as handle:
        content = handle.read()

    return {"success": True, "filename": file, "size_bytes": len(content), "content": content}
