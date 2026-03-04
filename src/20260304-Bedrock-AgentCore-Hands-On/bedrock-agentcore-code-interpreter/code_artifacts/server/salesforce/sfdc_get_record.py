# servers/salesforce/sfdc_get_record.py
from client import call_mcp_tool


async def sfdc_get_record(record_id: str) -> dict:
    """
    Retrieve a Salesforce opportunity record by record ID.

    Args:
        record_id: The Salesforce record ID

    Returns:
        Record dict containing type, name, stage, amount, etc.
    """
    result = await call_mcp_tool("sfdc_get_record", {
        "record_id": record_id,
    })
    contents = result.content
    if contents and len(contents) > 0:
        import json
        return json.loads(contents[0].text)
    return {}
