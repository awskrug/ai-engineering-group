"""
Bedrock Guardrails setup module for PII detection and anonymization
"""

from typing import Tuple
from src.utils.aws_utils import create_bedrock_guardrail


def setup_bedrock_guardrails(guardrail_name: str, pii_entity_config: dict, 
                           region: str) -> Tuple[str, str, str]:
    """
    Setup Bedrock Guardrails for PII detection and anonymization.
    
    Returns:
        Tuple of (guardrail_id, guardrail_version, guardrail_arn)
    """
    print("\n" + "="*40)
    print("Setting up Bedrock Guardrails")
    print("="*40)
    
    guardrail_id, guardrail_version, guardrail_arn = create_bedrock_guardrail(
        guardrail_name, pii_entity_config, region
    )
    
    print(f"✓ Configured {len(pii_entity_config['piiEntitiesConfig'])} PII types for anonymization:")
    for pii_config in pii_entity_config['piiEntitiesConfig']:
        print(f"  - {pii_config['type']}: {pii_config['action']}")
    
    return guardrail_id, guardrail_version, guardrail_arn