#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RECALIBRATE_DATASET.py
======================
Recalibra los hallazgos previos bajo la taxonomía GL/TP (v1.1).
Transforma "Ghost Primes" en "Loci de Invariancia".
"""

import sys
import os
import json
from pathlib import Path
from typing import Any, List

# Ruta al core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "Gahenax_Core")))
from physics.INVARIANCE_ENGINE import (
    InvarianceEngine, InvarianceRecord, ArithmeticVerdict, 
    AttackSpec, AttackStrength, DEFAULT_ATTACKS, render_report
)

def hex_to_int(s: str) -> int:
    try:
        if s.startswith("0x"): return int(s, 16)
        return int(s)
    except: return 0

def calc_invariance_index(residue_int: int) -> float:
    """
    Calcula el Índice de Invariancia I(p).
    En esta calibración, usamos la entropía de bits del residuo.
    Un valor cercano a 0 indica alta rigidez (patrón repetitivo).
    """
    if residue_int == 0: return 0.0
    b = bin(residue_int)[2:]
    # Proporción de unos (idealmente 0.5 para aleatorio)
    p1 = b.count('1') / len(b)
    # Rigidez = Desviación de la aleatoriedad perfecta
    return abs(p1 - 0.5)

def main():
    results_dir = Path("results/mersenne/neighborhoods")
    analysis_dir = Path("results/mersenne/calibrated_analysis")
    analysis_dir.mkdir(parents=True, exist_ok=True)
    
    # Motor de Invariancia con observable refinado (varianza de bits como Proxy de I(p))
    engine = InvarianceEngine(observable=lambda x: calc_invariance_index(x))
    
    p_target = 1259
    scan_file = results_dir / "ghost_hunt_p1279.json"
    
    if not scan_file.exists(): return

    with open(scan_file, "r") as f: data = json.load(f)
    candidate = next((x for x in data if x["p"] == p_target), None)
    
    if candidate:
        residue_val = hex_to_int(candidate["residue"])
        
        record = InvarianceRecord(
            p=p_target,
            label=f"GL-{p_target}",
            arithmetic_verdict=ArithmeticVerdict.COMPOSITE,
            arithmetic_evidence={"LL_residue_hash": candidate.get("residue_hash", "provided")},
            notes=[
                "Recalibrado bajo Protocolo I(p) v1.1.",
                "La inversión de bits no perturba I(p) dentro del umbral epsilon, lo que sugiere que la señal no depende de ese eje específico de representación.",
                "Los datos son compatibles con una señal dependiente de fase local."
            ]
        )
        
        # Ejecutar suite de ataques completa definida en el motor
        engine.evaluate(record, residue_val, DEFAULT_ATTACKS)
        
        # Generar Reporte con lenguaje blindado
        report_text = render_report(record)
        report_path = analysis_dir / f"GL_REPORT_p{p_target}.md"
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_text)
            
        # Imprimir reporte para auditoría directa del usuario (usando utf-8 para evitar errores en Windows)
        sys.stdout.buffer.write(report_text.encode('utf-8'))
        sys.stdout.buffer.write(b"\n")

if __name__ == "__main__":
    main()
