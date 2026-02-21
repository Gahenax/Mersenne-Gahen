from typing import Dict, Any, List
import hashlib
import json
import time
import sys
from pathlib import Path

# Add the project root to import logic
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from antigravity.core.contracts import AntigravityModule, ExecutionResult, Auditable, HodgeAuditable
from antigravity.core.roles import Simulator
from MERSENNE_PROBE_V1 import MersenneEngine

class MersenneMinerModule(Simulator, HodgeAuditable):
    """
    Mersenne Prime Miner module integrated into the Antigravity Lab.
    Role: Simulator (Arithmetic Dynamics).
    """
    name = "MersenneMiner"
    version = "2.1.0"

    def __init__(self, budget_ua: float = 10000.0):
        self.budget_ua = budget_ua
        self.audit_trail = []
        self.engine = MersenneEngine()

    def check_compliance(self, estimated_cost: float) -> bool:
        """Enforce UA budget compliance."""
        return estimated_cost <= self.budget_ua

    def execute(self, params: Dict[str, Any]) -> ExecutionResult:
        """
        Executes a Lucas-Lehmer certification on a given exponent p.
        """
        p = params.get("p", 127)
        
        # Estimate UA cost: O(p^2) or O(p log p log log p)
        # For simplicity: p * 0.5 UA
        estimated_ua = p * 0.05
        if not self.check_compliance(estimated_ua):
            return ExecutionResult(
                success=False,
                payload={"error": "BUDGET_EXCEEDED", "required": estimated_ua},
                ua_spent=0.0,
                evidence_hash="BLOCK"
            )

        print(f"[*] Starting Lucas-Lehmer for M_{p}...")
        is_prime, residue, dt, roundoff = self.engine.lucas_lehmer(p)
        
        payload = {
            "p": p,
            "is_prime": is_prime,
            "residue_hash": hashlib.sha256(str(residue).encode()).hexdigest(),
            "wall_time": dt,
            "roundoff_error": roundoff,
            "stability": {
                "H": float(roundoff),  # Roundoff drift is our rigidity metric
                "M": float(residue != 0), # 1.0 if not prime (residue exists), 0.0 if prime
                "S": 1.0 if is_prime else 0.0
            }
        }
        
        evidence_str = json.dumps(payload, sort_keys=True)
        evidence_hash = hashlib.sha256(evidence_str.encode()).hexdigest()

        result = ExecutionResult(
            success=True,
            payload=payload,
            ua_spent=estimated_ua,
            evidence_hash=evidence_hash
        )
        
        self.audit_trail.append(payload)
        return result

    def get_stability_metrics(self, result: ExecutionResult) -> Dict[str, float]:
        """Extract H, M, S from the payload."""
        return result.payload["stability"]

    def get_audit_trail(self) -> List[Dict[str, Any]]:
        return self.audit_trail
