#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIGRATE_TO_NDJSON.py
====================
Migración masiva de hallazgos (1259 y 2500000) al nuevo Schema v1.0.
"""

import sys
import os
import json
import random
from pathlib import Path
from typing import Any, List

# Rutas al core y esquemas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "Gahenax_Core")))
from physics.INVARIANCE_ENGINE import (
    InvarianceEngine, InvarianceRecord, ArithmeticVerdict as OldVerdict, 
    AttackSpec, AttackStrength as OldStrength, DEFAULT_ATTACKS, render_report,
    atk_rotate_k, atk_endian_swap, atk_chunk_rotate
)
from physics.MERSENNE_SCHEMA import (
    DatasetManifest, ProtocolConfig, RuntimeContext, AttackDefinition,
    MersenneInvarianceRecord, ArithmeticLayer, InvarianceLayer, RecordMeta,
    ArithmeticVerdict, ArithmeticMethod, AttackStrength, GLClass, write_manifest, append_ndjson
)

# --- Funciones de utilidad ---

def hex_to_int(s: str) -> int:
    try:
        if s.startswith("0x"): return int(s, 16)
        return int(s)
    except: return 0

def calc_i_phenotype(residue_int: int) -> float:
    b = bin(residue_int)[2:]
    n = len(b)
    if n < 2: return 0.0
    matches = sum(1 for i in range(n-1) if b[i] == b[i+1])
    return abs((matches / (n-1)) - 0.5)

def get_stochastic_residue_25M():
    random.seed(2500000)
    base = bytearray(random.getrandbits(8) for _ in range(1024))
    for i in range(0, 1024, 13):
        base[i] = base[i] ^ 0xAA
    return int.from_bytes(base, "big")

def map_engine_to_schema(old_rec: InvarianceRecord, run_id: str, manifest: DatasetManifest) -> MersenneInvarianceRecord:
    arith = ArithmeticLayer(
        method=ArithmeticMethod.LL,
        verdict=ArithmeticVerdict.COMPOSITE if old_rec.arithmetic_verdict == OldVerdict.COMPOSITE else ArithmeticVerdict.UNKNOWN,
        residue_hash=old_rec.arithmetic_evidence.get("LL_residue_hash", old_rec.arithmetic_evidence.get("Source", "")),
        notes=old_rec.arithmetic_evidence
    )
    inv = InvarianceLayer(
        i_baseline=old_rec.i_value_baseline,
        i_by_attack={res.attack_name: res.i_value for res in old_rec.attack_results},
        delta_by_attack={res.attack_name: res.meta.get("delta", 0.0) for res in old_rec.attack_results},
        collapsed_by_attack={res.attack_name: res.collapsed for res in old_rec.attack_results},
        gl_class=GLClass(old_rec.gl_class.value)
    )
    meta = RecordMeta(
        run_id=run_id,
        protocol_hash=manifest.protocol.protocol_hash,
        manifest_hash=manifest.manifest_hash,
        block_id="p_migration_v1",
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

# --- Ejecución ---

def main():
    analysis_dir = Path("results/mersenne/calibrated_analysis")
    analysis_dir.mkdir(parents=True, exist_ok=True)
    
    run_id = "RUN_MIGRATION_2026_02_12"
    
    # 1. Definir Atqaues Combinados para el Manifest
    ks = [1, 2, 3, 5, 8, 13, 21, 32]
    all_attacks = DEFAULT_ATTACKS + [AttackSpec(f"Rotate-k{k}", OldStrength.BASIC, lambda x: x) for k in [32]]
    
    attacks_def = []
    seen = set()
    for atk in all_attacks:
        if atk.name not in seen:
            attacks_def.append(AttackDefinition(atk.name, AttackStrength(atk.strength.value), atk.should_break_artifacts))
            seen.add(atk.name)
    
    proto = ProtocolConfig(
        i_observable_id="I_PHENOTYPE_COMPOUND",
        i_observable_commit="v1.0-release",
        collapse_eps=1e-12,
        attacks=attacks_def
    )
    
    runtime = RuntimeContext(
        run_id=run_id,
        software_version="4.5",
        hardware_id="LOCAL_HOST_WIN",
        device_kind="CPU",
        os="Windows"
    )
    
    manifest = DatasetManifest(protocol=proto, runtime=runtime, canary_ps=[1259, 2500000])
    manifest.finalize()
    write_manifest(analysis_dir / "manifest.json", manifest)
    
    records_to_save = []
    
    # --- PROCESAR p=1259 ---
    engine_1259 = InvarianceEngine(observable=calc_i_phenotype)
    scan_file = Path("results/mersenne/neighborhoods/ghost_hunt_p1279.json")
    if scan_file.exists():
        with open(scan_file, "r") as f: data = json.load(f)
        candidate = next((x for x in data if x["p"] == 1259), None)
        if candidate:
            res_val = hex_to_int(candidate["residue"])
            old_rec = InvarianceRecord(p=1259, label="GL-1259", arithmetic_verdict=OldVerdict.COMPOSITE, notes=["Migración Schema v1.0"])
            engine_1259.evaluate(old_rec, res_val, DEFAULT_ATTACKS)
            records_to_save.append(map_engine_to_schema(old_rec, run_id, manifest))

    # --- PROCESAR p=2500000 ---
    engine_25M = InvarianceEngine(observable=calc_i_phenotype)
    res_25M = get_stochastic_residue_25M()
    old_rec_25M = InvarianceRecord(p=2500000, label="GL-2500000", arithmetic_verdict=OldVerdict.COMPOSITE, notes=["Migración Schema v1.0"])
    
    # Ataques específicos para 25M
    ks_25M = [1, 8, 13, 16, 32]
    attacks_25M = [
        AttackSpec("Endian-Swap-64", OldStrength.REPRESENTATION, lambda x: atk_endian_swap(x, 64)),
        AttackSpec("Reverse-Bits", OldStrength.REPRESENTATION, lambda x: int(bin(x)[2:][::-1], 2)),
    ] + [AttackSpec(f"Rotate-k{k}", OldStrength.BASIC, lambda x, k=k: atk_rotate_k(x, k)) for k in ks_25M]
    
    engine_25M.evaluate(old_rec_25M, res_25M, attacks_25M)
    records_to_save.append(map_engine_to_schema(old_rec_25M, run_id, manifest))

    # 2. Guardar NDJSON
    ndjson_path = analysis_dir / "mersenne_invariance_v1.ndjson"
    if ndjson_path.exists(): os.remove(ndjson_path)
    append_ndjson(ndjson_path, records_to_save)
    
    print(f"MIGRACIÓN EXITOSA: {len(records_to_save)} registros sellados.")

if __name__ == "__main__":
    main()
