import json
import time
import hashlib
from pathlib import Path
from MERSENNE_PROBE_V1 import MersenneEngine
from MERSENNE_MISSION_CONTROL import MissionControl

def run_ruta_b_crash_test():
    print(f"--- RUTA B: CRASH-TEST INSTRUMENTAL ---")
    mc = MissionControl("./mersenne_lab_recalibration")
    
    # B2) RED-TEAM: CORRUPCIÓN DE CHECKPOINT
    print("\n[B2] Audit: Corrupción de Checkpoint controlada")
    print("  -> Generando checkpoint parcial para p=1279...")
    engine = MersenneEngine()
    # Ejecutamos solo una parte del test para generar un checkpoint
    # p=1279, iteramos hasta la mitad
    m_p = (1 << 1279) - 1
    engine.save_checkpoint(1279, 123456789, 500) # Checkpoint falso/parcial
    
    cp_file = Path("checkpoint_p1279.json")
    print(f"  -> Checkpoint creado: {cp_file}")
    
    # Corrupción manual del archivo
    print("  -> Inyectando corrupción de hash en el checkpoint...")
    with open(cp_file, "r") as f:
        data = json.load(f)
    data["hash"] = "corrupted_hash_value_xyz"
    with open(cp_file, "w") as f:
        json.dump(data, f)
    
    # Intento de reanudación
    print("  -> Intentando reanudación con checkpoint corrupto...")
    res = mc.execute_p2_verify(1279)
    print(f"  -> Resultado B2: Status={res['status']} (Esperado: RED)")

    # B3) SENSIBILIDAD: DUAL-PATH VERIFICATION
    print("\n[B3] Audit: Dual-Path (Bitwise vs Modular) en p=2281")
    # p=2281 es conocido. Si hay mismatch en la lógica interna, saltará RED.
    res_b3 = mc.execute_p2_verify(2281)
    print(f"  -> Resultado B3: Status={res_b3['status']} (Esperado: GREEN)")

    # Consolidación de Log Operativo
    metrics = {
        "B2_Success": res["status"] == "RED",
        "B3_Success": res_b3["status"] == "GREEN"
    }
    print(f"\n[RUTA B CONSOLIDADA]")
    print(json.dumps(metrics, indent=2))
    
    if metrics["B2_Success"] and metrics["B3_Success"]:
        print("\nGATE CUMPLIDO: Sistema inmune a corrupción y errores de lógica dual.")
    else:
        print("\nGATE FALLIDO: Revisar integridad del motor.")

if __name__ == "__main__":
    run_ruta_b_crash_test()
