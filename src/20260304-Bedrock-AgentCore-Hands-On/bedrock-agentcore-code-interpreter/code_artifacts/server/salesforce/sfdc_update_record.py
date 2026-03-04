# servers/salesforce/sfdc_update_record.py
from client import call_mcp_tool


async def sfdc_update_record(record_id: str, data: dict) -> dict:
    """
    Update fields on a Salesforce opportunity record.

    Args:
        record_id: The Salesforce record ID to update
        data: Dictionary of field names and values to update

    Returns:
        Status dict with update confirmation
    """
    result = await call_mcp_tool("sfdc_update_record", {
        "record_id": record_id,
        "data": data,
    })
    contents = result.content
    if contents and len(contents) > 0:
        import json
        return json.loads(contents[0].text)
    return {}
