# mersenne_ghost_adapter.py
# ========================
# Enchufe para el MersenneEngine real dentro del GHOST-HUNTER LAB.

import sys
import os
from typing import Any, Dict, Union

# Asegurar que el directorio raíz está en el path para importar el motor
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from research.mersenne.MERSENNE_PROBE_V1 import MersenneEngine
except ImportError:
    # Fallback si se movió a research/ o similar
    try:
        from MERSENNE_PROBE_V1 import MersenneEngine
    except ImportError:
        # Fallback local
        from MERSENNE_PROBE_V1 import MersenneEngine

# Instancia global del motor para el adapter
engine = MersenneEngine()

def compute_ll_residue(p: int) -> Union[int, bytes, str]:
    """
    Usa el Lucas-Lehmer real del motor Antigravity.
    """
    print(f"  [ADAPTER] Computing LL for p={p}...", file=sys.stderr)
    is_prime, residue, duration, h_rigidity = engine.lucas_lehmer(p)
    return residue

def compute_rigidity_H(residue: Union[int, bytes, str], meta: Dict[str, Any]) -> float:
    """
    Extrae la rigidez H. 
    Nota: El motor actual devuelve H=0.0 para tests exitosos.
    """
    # Si el meta contiene 'repr', estamos en un test de falsabilidad algorítmica.
    # Podríamos implementar una métrica de entropía real aquí si el residuo cambia.
    
    if isinstance(residue, bytes):
        b = residue
    elif isinstance(residue, int):
        b = residue.to_bytes((residue.bit_length()+7)//8 or 1, "big")
    else:
        b = residue.encode("utf-8")
        
    # Mock de métrica H basada en la anomalía de entropía para tests de representación
    # Si es exactamente 0 (el residuo de un primo), H=0.
    # De lo contrario, calculamos una rigidez simulada.
    if b == b"\x00":
        return 0.0
    
    # Simulación de H: Si el primer byte es par, H es bajo (GHOST).
    return 0.0 if (b[0] % 2 == 0) else 1.0

def compute_wall_time(p: int) -> float:
    # El motor ya mide el tiempo, pero dejamos que el lab lo mida externamente
    return None

def label_of(p: int) -> str:
    return f"M_{p}"
