# antigravity/core/contracts.py
"""
Base contracts for Antigravity Modules.
These are the interfaces expected by research engines (Riemann, Mersenne).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class ExecutionResult:
    """Standard container for an engine's output."""
    success: bool
    payload: Dict[str, Any]
    ua_spent: float
    evidence_hash: str

class AntigravityModule:
    """Base interface for all Antigravity engines."""
    name: str = "BaseModule"
    version: str = "1.0.0"
    
    def execute(self, params: Dict[str, Any]) -> ExecutionResult:
        raise NotImplementedError

class Auditable:
    """Module supports audit trails."""
    def get_audit_trail(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

class HodgeAuditable(Auditable):
    """Module supports Hodge stability metrics (H, M, S)."""
    def get_stability_metrics(self, result: ExecutionResult) -> Dict[str, float]:
        raise NotImplementedError

class Deferrable:
    """Module supports delegation to external compute (Jules)."""
    def get_delegation_order(self, params: Dict[str, Any]) -> str:
        raise NotImplementedError
