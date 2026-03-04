from pydantic import Field
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base
import json

mcp = FastMCP(host="0.0.0.0", stateless_http=True)

# ------------------------------------------------------------
# 가상 데이터: Google Drive 문서
# ------------------------------------------------------------
google_drive_docs = {
    "doc_meeting_0115": {
        "title": "Sales Meeting - Acme Corp (Jan 15)",
        "content": """Meeting Date: 2026-01-15
Attendees: John Park (SA), Sarah Kim (AE), Mike Chen (Acme Corp CTO)

Key Discussion Points:
- Acme Corp currently runs 200+ EC2 instances across 3 regions
- Interested in Reserved Instances for cost optimization
- Requested a POC for Aurora PostgreSQL migration

Action Items:
- [John] Prepare Aurora migration POC by Jan 30
- [Sarah] Send RI pricing comparison by Jan 20

Next Meeting: Feb 5, 2026""",
        "created_at": "2026-01-15T14:00:00Z",
    },
    "doc_meeting_0205": {
        "title": "Sales Meeting - Acme Corp (Feb 5)",
        "content": """Meeting Date: 2026-02-05
Attendees: John Park (SA), Sarah Kim (AE), Mike Chen (Acme Corp CTO)

Key Discussion Points:
- Aurora POC showed 40% query performance improvement
- RI 1-year commitment preferred over 3-year
- Total estimated savings: $180K/year

Decision: Acme Corp verbally committed to proceed. Contract expected by Feb 28.""",
        "created_at": "2026-02-05T15:00:00Z",
    },
}

# ------------------------------------------------------------
# 가상 데이터: Salesforce CRM
# ------------------------------------------------------------
salesforce_records = {
    "OPP-2026-001": {
        "type": "Opportunity",
        "name": "Acme Corp - AWS Migration & Optimization",
        "stage": "Proposal",
        "amount": 850000,
        "close_date": "2026-03-31",
        "owner": "sarah.kim@example.com",
        "notes": "",
    },
    "OPP-2026-002": {
        "type": "Opportunity",
        "name": "Beta Inc - Serverless Modernization",
        "stage": "Discovery",
        "amount": 320000,
        "close_date": "2026-06-30",
        "owner": "sarah.kim@example.com",
        "notes": "Initial meeting scheduled for Feb 20",
    },
}

# ============================================================
# Google Drive Tools (2개)
# ============================================================

@mcp.tool(
    name="gdrive_get_document",
    description="Retrieve a document from Google Drive by its document ID.",
)
def gdrive_get_document(
    document_id: str = Field(description="The document ID to retrieve"),
) -> dict:
    if document_id not in google_drive_docs:
        raise ValueError(f"Document '{document_id}' not found")
    return google_drive_docs[document_id]

@mcp.tool(
    name="gdrive_search_documents",
    description="Search Google Drive documents by keyword in title or content.",
)
def gdrive_search_documents(
    query: str = Field(description="Search keyword"),
) -> list[dict]:
    results = []
    for doc_id, doc in google_drive_docs.items():
        if query.lower() in doc["title"].lower() or query.lower() in doc["content"].lower():
            results.append({"document_id": doc_id, "title": doc["title"]})
    return results

# ============================================================
# Salesforce Tools (2개)
# ============================================================

@mcp.tool(
    name="sfdc_get_record",
    description="Retrieve a Salesforce opportunity record by record ID.",
)
def sfdc_get_record(
    record_id: str = Field(description="The Salesforce record ID"),
) -> dict:
    if record_id not in salesforce_records:
        raise ValueError(f"Record '{record_id}' not found")
    return {"record_id": record_id, **salesforce_records[record_id]}

@mcp.tool(
    name="sfdc_update_record",
    description="Update fields on a Salesforce opportunity record.",
)
def sfdc_update_record(
    record_id: str = Field(description="The Salesforce record ID to update"),
    data: dict = Field(description="Dictionary of field names and values to update"),
) -> dict:
    if record_id not in salesforce_records:
        raise ValueError(f"Record '{record_id}' not found")
    salesforce_records[record_id].update(data)
    return {"status": "updated", "record_id": record_id}

# ============================================================
# Resources (Progressive Disclosure)
# ============================================================

@mcp.resource("servers://list", mime_type="application/json")
def list_servers() -> list[str]:
    return ["google-drive", "salesforce"]

@mcp.resource("servers://google-drive/tools", mime_type="application/json")
def list_gdrive_tools() -> list[dict]:
    return [
        {"name": "gdrive_get_document", "description": "Retrieve a document by ID"},
        {"name": "gdrive_search_documents", "description": "Search documents by keyword"},
    ]

@mcp.resource("servers://salesforce/tools", mime_type="application/json")
def list_sfdc_tools() -> list[dict]:
    return [
        {"name": "sfdc_get_record", "description": "Get a record by ID"},
        {"name": "sfdc_update_record", "description": "Update fields on a record"},
    ]

# ============================================================
# Prompts
# ============================================================

@mcp.prompt(
    name="sync_meeting_notes",
    description="Read meeting notes from Google Drive and update the corresponding Salesforce opportunity.",
)
def sync_meeting_notes(
    document_id: str = Field(description="Google Drive document ID"),
    opportunity_id: str = Field(description="Salesforce opportunity ID"),
) -> list[base.Message]:
    prompt = f"""
    Read the meeting notes from Google Drive (document ID: {document_id}),
    extract key points and action items, then update the Salesforce opportunity
    (record ID: {opportunity_id}) Notes field with a concise summary.
    """
    return [base.UserMessage(prompt)]

# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
