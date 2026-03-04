# servers/google_drive/gdrive_get_document.py
from client import call_mcp_tool


async def gdrive_get_document(document_id: str) -> dict:
    """
    Retrieve a document from Google Drive by its document ID.

    Args:
        document_id: The document ID to retrieve

    Returns:
        Document dict containing title, content, created_at
    """
    result = await call_mcp_tool("gdrive_get_document", {
        "document_id": document_id,
    })
    contents = result.content
    if contents and len(contents) > 0:
        import json
        return json.loads(contents[0].text)
    return {}
