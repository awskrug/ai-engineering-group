# servers/google_drive/gdrive_search_documents.py
from client import call_mcp_tool


async def gdrive_search_documents(query: str) -> list[dict]:
    """
    Search Google Drive documents by keyword in title or content.

    Args:
        query: Search keyword

    Returns:
        List of matching documents with document_id and title
    """
    result = await call_mcp_tool("gdrive_search_documents", {
        "query": query,
    })
    contents = result.content
    if contents and len(contents) > 0:
        import json
        return json.loads(contents[0].text)
    return []
