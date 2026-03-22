"""Centralized service endpoints and ports for Sueca 1.4."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceConfig:
    gateway_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:8000"
    virtual_engine_url: str = "http://localhost:5000"
    physical_engine_url: str = "http://localhost:8002"
    cv_service_url: str = "http://localhost:8001"
    cv_service_ws_url: str = "ws://localhost:8001"


SERVICES = ServiceConfig()
