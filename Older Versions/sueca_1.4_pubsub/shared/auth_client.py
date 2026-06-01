"""Centralized token validation client for all services.

This module provides helper functions to validate tokens by calling
the centralized auth service, ensuring consistent validation logic
across all microservices.
"""

import os
import logging
import httpx
from typing import Any

logger = logging.getLogger(__name__)

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
VALIDATE_TOKEN_ENDPOINT = f"{AUTH_SERVICE_URL}/validate/token"
VALIDATE_SERVICE_TOKEN_ENDPOINT = f"{AUTH_SERVICE_URL}/validate/service"
ISSUE_SERVICE_TOKEN_ENDPOINT = f"{AUTH_SERVICE_URL}/service-token/issue"


async def validate_token_via_auth_service(token: str) -> dict[str, Any] | None:
    """
    Validate a user access token via the centralized auth service.
    
    Args:
        token: JWT token to validate
    
    Returns:
        Token payload dict if valid, None if invalid
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                VALIDATE_TOKEN_ENDPOINT,
                json={"token": token},
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("valid"):
                    return data.get("payload")
                else:
                    logger.debug(f"Token validation failed: {data.get('error')}")
                    return None
            else:
                logger.error(f"Auth service error: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Error calling auth service: {e}")
        return None


async def validate_service_token_via_auth_service(token: str) -> dict[str, Any] | None:
    """
    Validate a service-to-service token via the centralized auth service.
    
    Args:
        token: Service JWT token to validate
    
    Returns:
        Token payload dict if valid, None if invalid
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                VALIDATE_SERVICE_TOKEN_ENDPOINT,
                json={"token": token},
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("valid"):
                    return data.get("payload")
                else:
                    logger.debug(f"Service token validation failed: {data.get('error')}")
                    return None
            else:
                logger.error(f"Auth service error: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Error calling auth service: {e}")
        return None


async def issue_service_token(service_name: str, scope: str) -> str | None:
    """
    Issue a short-lived service-to-service token from the auth service.
    
    Args:
        service_name: Name of the service requesting the token
        scope: Token scope (e.g., 'control_plane')
    
    Returns:
        JWT token string if successful, None on error
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                ISSUE_SERVICE_TOKEN_ENDPOINT,
                json={"service_name": service_name, "scope": scope},
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return data.get("token")
                else:
                    logger.error(f"Failed to issue service token: {data}")
                    return None
            else:
                logger.error(f"Auth service error: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Error calling auth service: {e}")
        return None
