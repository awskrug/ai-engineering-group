"""
Cognito setup module for PII Masking Gateway with FGAC
"""

import time
from typing import Dict, List
from src.utils.aws_utils import *


def setup_cognito_with_multiple_clients(cognito_client, user_pool_name: str, 
                                      resource_server_id: str, deployment_id: str,
                                      region: str) -> Dict:
    """
    Setup Cognito user pool with HR-specific clients.
    
    Returns:
        Dict containing user pool info and client configurations
    """
    print("\n" + "="*40)
    print("Setting up HR Cognito with Multiple Clients")
    print("="*40)
    
    # Create or get user pool
    user_pool_id = get_or_create_user_pool(cognito_client, user_pool_name)
    print(f"✓ User Pool ID: {user_pool_id}")
    
    # Create or get resource server
    resource_server_name = 'HR Gateway Resource Server'
    scopes = [{'ScopeName': 'tools', 'ScopeDescription': 'Access to HR gateway tools'}]
    
    get_or_create_resource_server(
        cognito_client, user_pool_id, resource_server_id, resource_server_name, scopes
    )
    
    # Wait for resource server to propagate
    print("Waiting for resource server to propagate...")
    time.sleep(3)
    
    # Create HR-specific app clients
    client_configs = [
        {'name': 'hr-manager', 'description': 'HR Manager - Full access to all employee data and leave management'},
        {'name': 'employee', 'description': 'Regular Employee - Limited access to basic info and own leave data'}
    ]
    
    clients = {}
    for config in client_configs:
        client_name = config['name']
        client_id, client_secret = get_or_create_m2m_client(
            cognito_client,
            user_pool_id,
            f"{client_name}-client-{deployment_id}",
            resource_server_id,
            scopes=[f"{resource_server_id}/tools"]
        )
        clients[client_name] = {
            'client_id': client_id, 
            'client_secret': client_secret,
            'description': config['description']
        }
        print(f"✓ Created/found client: {client_name}")
    
    # Construct OAuth URLs
    pool_domain = user_pool_id.replace('_', '').lower()
    discovery_url = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration"
    token_url = f"https://{pool_domain}.auth.{region}.amazoncognito.com/oauth2/token"
    
    result = {
        'user_pool_id': user_pool_id,
        'discovery_url': discovery_url,
        'token_url': token_url,
        'clients': clients,
        'client_ids': {name: info['client_id'] for name, info in clients.items()}
    }
    
    print(f"\n✓ HR Cognito setup complete")
    print(f"  User Pool ID: {user_pool_id}")
    print(f"  Discovery URL: {discovery_url}")
    print(f"  Created {len(clients)} HR clients")
    
    return result