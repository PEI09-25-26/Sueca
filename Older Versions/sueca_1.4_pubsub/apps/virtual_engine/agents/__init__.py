"""Compatibility shim: expose agent classes from the central agents service package."""

from apps.agents.agents import RandomAgent, WeakAgent, AverageAgent, SmartAgent

__all__ = ["RandomAgent", "WeakAgent", "AverageAgent", "SmartAgent"]
