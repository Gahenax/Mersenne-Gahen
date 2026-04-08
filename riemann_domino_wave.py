# riemann_domino_wave.py
from __future__ import annotations

import os
import json
import time
import math
import hashlib
import random
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed, wait, FIRST_COMPLETED

# === CORE ENGINE PATHS ===
PROJECT_ROOT = r"c:\Users\USUARIO\OneDrive\Desktop\Tesis"
ENGINE_ROOT = r"c:\Users\USUARIO\.gemini\antigravity\playground\calculo-avanzado-asistido"
import sys
for p in [PROJECT_ROOT, ENGINE_ROOT, os.path.join(ENGINE_ROOT, "core")]:
    if p not in sys.path:
        sys.path.append(p)

# -----------------------------
# Contracts (schemas)
# -----------------------------

@dataclass(frozen=True)
class Band:
    band_id: int
    t0: float
    t1: float

@dataclass
class CalibState:
    mean_gap: float = 1.0 
    baseline_r: float = 0.5996 
    n_zeros: int = 0
    residual_p95: float = 0.0
    fail_rate: float = 0.0
    version: str = "wave_v1.0"

@dataclass(frozen=True)
class ZeroCandidate:
    t_est: float
    bracket: Tuple[float, float]
    method: str
    residual: float
    band_id: int
    probe: str
    seq: int
    rigidity_h: Optional[float] = None

@dataclass(frozen=True)
class LedgerEvent:
    ts: float
    type: str  
    payload: Dict[str, Any]

# -----------------------------
# I/O utils
# -----------------------------

def _atomic_append_jsonl(path: str, event: LedgerEvent) -> None:
    line = json.dumps(asdict(event), ensure_ascii=False)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    if not os.path.exists(path): return "none"
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

# -----------------------------
# Worker
# -----------------------------

def mine_band_worker(
    probe: str,
    band: Band,
    calib_in: CalibState,
    out_dir: str,
    cfg: Dict[str, Any],
) -> Dict[str, Any]:
    shard_path = os.path.join(out_dir, f"shard_{probe}_band{band.band_id}.jsonl")
    
    try:
        from RIEMANN_ZERO_FILTER_UA_MACRO import bracketing_scan, ScanConfig, UAConfig, PrecisionConfig, RiemannLedger
    except ImportError as e:
        return {"error": f"Engine not found: {e}", "band_id": band.band_id}

    alpha = cfg.get("alpha", 0.05)
    cfg_scan = ScanConfig(T0=band.t0, T1=band.t1, step=alpha)
    cfg_ua = UAConfig(budget_total=cfg.get("ua_budget", 500000))
    cfg_prec = PrecisionConfig()
    ledger_engine = RiemannLedger(cfg_ua)
    
    _atomic_append_jsonl(shard_path, LedgerEvent(
        ts=time.time(),
        type="HEALTH",
        payload={"probe": probe, "band_id": band.band_id, "status": "STARTING_SWEEP"}
    ))

    try:
        candidates = bracketing_scan(cfg_scan, cfg_prec, ledger_engine, alpha=alpha)
    except Exception as e:
        return {"error": str(e), "band_id": band.band_id}
    
    zeros_found = 0
    residuals = []
    
    for i, c in enumerate(candidates):
        data = asdict(c)
        t_est = data.get("refined_T") or data.get("T") or 0.0
        residual = data.get("verified_s_full") or 0.0
        
        cand = ZeroCandidate(
            t_est=t_est,
            bracket=data.get("bracket_hint", (0, 0)),
            method="bracketing_scan_v1",
            residual=residual,
            band_id=band.band_id,
            probe=probe,
            seq=i,
            rigidity_h=data.get("confidence")
        )
        
        _atomic_append_jsonl(shard_path, LedgerEvent(ts=time.time(), type="ZERO_CANDIDATE", payload=asdict(cand)))
        zeros_found += 1
        residuals.append(residual)

    p95_res = sorted(residuals)[int(0.95*(len(residuals)-1))] if residuals else 0.0
    return {
        "probe": probe, "band_id": band.band_id, "zeros_found": zeros_found,
        "residual_p95": p95_res, "shard_path": shard_path
    }

# -----------------------------
# Orchestrator
# -----------------------------

class RiemannDominoOrchestrator:
    def __init__(self, t_start, t_end, probe_names, band_width, out_dir, cfg=None):
        self.t_start = t_start
        self.t_end = t_end
        self.probe_names = probe_names
        self.band_width = band_width
        self.out_dir = out_dir
        self.cfg = cfg or {}
        os.makedirs(out_dir, exist_ok=True)
        self.bands = [Band(i, t_start + i*band_width, min(t_start + (i+1)*band_width, t_end)) 
                      for i in range(math.ceil((t_end-t_start)/band_width))]
        self.calib = CalibState()

    def run_sweep(self) -> Dict[str, Any]:
        num_workers = os.cpu_count() or 8
        try:
            import psutil
            p = psutil.Process(os.getpid())
            p.nice(psutil.HIGH_PRIORITY_CLASS)
        except: pass
            
        pending_bands = list(self.bands)
        active_futures = {}
        completed_count = 0
        total_zeros = 0
        
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            for probe in self.probe_names:
                if not pending_bands: break
                band = pending_bands.pop(0)
                fut = executor.submit(mine_band_worker, probe, band, self.calib, self.out_dir, self.cfg)
                active_futures[fut] = (probe, band)
            
            while active_futures:
                done, _ = wait(list(active_futures.keys()), return_when=FIRST_COMPLETED)
                for fut in done:
                    probe, old_band = active_futures.pop(fut)
                    try:
                        res = fut.result()
                        if "error" not in res:
                            total_zeros += res["zeros_found"]
                            completed_count += 1
                            print(f"[DOMINO] {probe} done band {old_band.band_id}. Zeros: {res['zeros_found']}")
                    except Exception as e:
                        print(f"[ERROR] {probe} failed: {e}")
                    
                    if pending_bands:
                        new_band = pending_bands.pop(0)
                        nfut = executor.submit(mine_band_worker, probe, new_band, self.calib, self.out_dir, self.cfg)
                        active_futures[nfut] = (probe, new_band)

        return {"status": "SUCCESS", "total_zeros": total_zeros}
