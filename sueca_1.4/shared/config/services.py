"""Centralized service endpoints and ports for Sueca 1.4."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceConfig:
    gateway_url: str = "http://10.225.61.214:8080"
    frontend_url: str = "http://10.225.61.214:8000"
    # Internal service targets must match lifecycle startup binds (127.0.0.1).
    virtual_engine_url: str = "http://127.0.0.1:5000"
    physical_engine_url: str = "http://127.0.0.1:8002"
    cv_service_url: str = "http://127.0.0.1:8001"
    cv_service_ws_url: str = "ws://127.0.0.1:8001"


SERVICES = ServiceConfig()
