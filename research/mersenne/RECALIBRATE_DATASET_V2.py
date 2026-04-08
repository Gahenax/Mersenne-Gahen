#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RECALIBRATE_DATASET_V2.py
=========================
Recalibra y ALMACENA hallazgos usando el nuevo Schema v1.0 (NDJSON + Manifest).
"""

import sys
import os
import json
from pathlib import Path
from typing import Any, List

# Rutas al core y esquemas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "Gahenax_Core")))
from physics.INVARIANCE_ENGINE import (
    InvarianceEngine, InvarianceRecord, ArithmeticVerdict as OldVerdict, 
    AttackSpec, AttackStrength as OldStrength, DEFAULT_ATTACKS, render_report
)
from physics.MERSENNE_SCHEMA import (
    DatasetManifest, ProtocolConfig, RuntimeContext, AttackDefinition,
    MersenneInvarianceRecord, ArithmeticLayer, InvarianceLayer, RecordMeta,
    ArithmeticVerdict, ArithmeticMethod, AttackStrength, GLClass, write_manifest, append_ndjson
)

def hex_to_int(s: str) -> int:
    try:
        if s.startswith("0x"): return int(s, 16)
        return int(s)
    except: return 0

def calc_invariance_index(residue_int: int) -> float:
    if residue_int == 0: return 0.0
    b = bin(residue_int)[2:]
    p1 = b.count('1') / len(b)
    return abs(p1 - 0.5)

def map_engine_to_schema(old_rec: InvarianceRecord, run_id: str, manifest: DatasetManifest) -> MersenneInvarianceRecord:
    """Convierte el objeto InvarianceRecord del motor al nuevo Schema v1.0."""
    
    # Capa Aritmética
    arith = ArithmeticLayer(
        method=ArithmeticMethod.LL,
        verdict=ArithmeticVerdict.COMPOSITE if old_rec.arithmetic_verdict == OldVerdict.COMPOSITE else ArithmeticVerdict.UNKNOWN,
        residue_hash=old_rec.arithmetic_evidence.get("LL_residue_hash", ""),
        notes=old_rec.arithmetic_evidence
    )
    
    # Capa Invariancia
    inv = InvarianceLayer(
        i_baseline=old_rec.i_value_baseline,
        i_by_attack={res.attack_name: res.i_value for res in old_rec.attack_results},
        delta_by_attack={res.attack_name: res.meta.get("delta", 0.0) for res in old_rec.attack_results},
        collapsed_by_attack={res.attack_name: res.collapsed for res in old_rec.attack_results},
        gl_class=GLClass(old_rec.gl_class.value)
    )
    
    # Meta
    meta = RecordMeta(
        run_id=run_id,
        protocol_hash=manifest.protocol.protocol_hash,
        manifest_hash=manifest.manifest_hash,
        block_id="p_recalibration_2026",
        worker_id="NAVI_LOCAL_01"
    )
    
    return MersenneInvarianceRecord(
        p=old_rec.p,
        label=old_rec.label,
        arithmetic=arith,
        invariance=inv,
        meta=meta,
        notes=old_rec.notes
    )

def main():
    results_dir = Path("results/mersenne/neighborhoods")
    analysis_dir = Path("results/mersenne/calibrated_analysis")
    analysis_dir.mkdir(parents=True, exist_ok=True)
    
    run_id = "RUN_RECAL_2026_02_21_NDJSON"
    
    # 1. Configurar Manifest del Protocolo
    attacks_def = [
        AttackDefinition(atk.name, AttackStrength(atk.strength.value), atk.should_break_artifacts)
        for atk in DEFAULT_ATTACKS
    ]
    
    proto = ProtocolConfig(
        i_observable_id="I_VAR_BIT_ENTROPY",
        i_observable_commit="7e4a8b",
        collapse_eps=1e-12,
        attacks=attacks_def
    )
    
    runtime = RuntimeContext(
        run_id=run_id,
        software_version="4.5",
        git_commit="latest",
        hardware_id="LOCAL_HOST_WIN",
        device_kind="CPU",
        precision_mode="int_generic",
        os="Windows"
    )
    
    manifest = DatasetManifest(protocol=proto, runtime=runtime, canary_ps=[1259])
    manifest.finalize()
    
    # Escribir Manifest
    write_manifest(analysis_dir / "manifest.json", manifest)
    
    # 2. Ejecutar Motor para p=1259
    engine = InvarianceEngine(observable=calc_invariance_index)
    scan_file = results_dir / "ghost_hunt_p1279.json"
    
    if not scan_file.exists(): return
    with open(scan_file, "r") as f: data = json.load(f)
    candidate = next((x for x in data if x["p"] == 1259), None)
    
    records_to_save = []
    
    if candidate:
        residue_val = hex_to_int(candidate["residue"])
        
        old_record = InvarianceRecord(
            p=1259,
            label="GL-1259",
            arithmetic_verdict=OldVerdict.COMPOSITE,
            arithmetic_evidence={"LL_residue_hash": candidate.get("residue_hash", "provided")},
            notes=["Recalibración a Schema v1.0"]
        )
        
        engine.evaluate(old_record, residue_val, DEFAULT_ATTACKS)
        
        # Convertir a Schema v1.0
        new_record = map_engine_to_schema(old_record, run_id, manifest)
        records_to_save.append(new_record)
        
        # Mostrar reporte visual (MD)
        report_text = render_report(old_record)
        with open(analysis_dir / "GL_REPORT_p1259.md", "w", encoding="utf-8") as f:
            f.write(report_text)
            
    # 3. Guardar en NDJSON
    ndjson_path = analysis_dir / "mersenne_invariance_v1.ndjson"
    if ndjson_path.exists(): os.remove(ndjson_path) # Reiniciar para el demo
    append_ndjson(ndjson_path, records_to_save)
    
    print(f"✅ Recalibración completada. Dataset: {ndjson_path}")
    print(f"✅ Manifest generado: {analysis_dir / 'manifest.json'}")

if __name__ == "__main__":
    main()
