"""Centralized service endpoints and ports for Sueca 1.4."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceConfig:
    gateway_url: str = "http://10.225.61.214:8080"
    frontend_url: str = "http://10.225.61.214:8000"
    # Internal service targets use Docker service names (container-to-container).
    virtual_engine_url: str = "http://virtual_engine:5000"
    physical_engine_url: str = "http://physical_engine:8002"
    cv_service_url: str = "http://physical_engine:8001"
    cv_service_ws_url: str = "ws://physical_engine:8001"
    # New service endpoints for modular backend
    auth_service_url: str = "http://auth:5010"
    friends_service_url: str = "http://friends:5020"
    agents_service_url: str = "http://agents:5030"


SERVICES = ServiceConfig()
