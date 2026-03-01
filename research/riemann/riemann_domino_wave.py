from __future__ import annotations

import sys
import os
# Setup relative src config loading for subdirectories
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import src.config

# riemann_domino_wave.py

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
PROJECT_ROOT = str(src.config.PROJECT_ROOT)
ENGINE_ROOT = str(src.config.ENGINE_ROOT)
# Additionally, load the external legacy repo scripts where RIEMANN_ZERO_FILTER_UA_MACRO.py lives
EXTERNAL_ENGINE = os.path.abspath(os.path.join(PROJECT_ROOT, "..", "calculo-avanzado-asistido", "src", "backend", "scripts"))

import sys
for p in [PROJECT_ROOT, ENGINE_ROOT, os.path.join(ENGINE_ROOT, "core"), EXTERNAL_ENGINE]:
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
    mean_gap: float = 1.0 # Standard GUE gap after unfolding
    baseline_r: float = 0.5996 # GUE baseline
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
    type: str  # "ZERO_CANDIDATE" | "VERIFY_PASS" | "VERIFY_FAIL" | "ANOMALY" | "HEALTH"
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
# Worker (Tripwire & Miner)
# -----------------------------

def mine_band_worker(
    probe: str,
    band: Band,
    calib_in: CalibState,
    out_dir: str,
    cfg: Dict[str, Any],
) -> Dict[str, Any]:
    """
    CPU-bound worker using the Riemann-Gahenax engine.
    """
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
        payload={
            "probe": probe, "band_id": band.band_id,
            "t0": band.t0, "t1": band.t1,
            "status": "STARTING_SWEEP",
            "alpha": alpha
        }
    ))

    start_time = time.time()
    try:
        candidates = bracketing_scan(cfg_scan, cfg_prec, ledger_engine, alpha=alpha)
    except Exception as e:
        _atomic_append_jsonl(shard_path, LedgerEvent(
            ts=time.time(),
            type="HEALTH",
            payload={"probe": probe, "band_id": band.band_id, "status": "CRASHED", "error": str(e)}
        ))
        return {"error": str(e), "band_id": band.band_id}
    
    end_time = time.time()
    
    zeros_found = 0
    residuals = []
    
    for i, c in enumerate(candidates):
        data = asdict(c)
        t_est = data.get("refined_T") or data.get("T") or data.get("t") or 0.0
        residual = data.get("verified_s_full") or data.get("residual") or 0.0
        
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
        
        _atomic_append_jsonl(shard_path, LedgerEvent(
            ts=time.time(),
            type="ZERO_CANDIDATE",
            payload=asdict(cand)
        ))
        zeros_found += 1
        residuals.append(residual)

    p95_res = sorted(residuals)[int(0.95*(len(residuals)-1))] if residuals else 0.0
    
    _atomic_append_jsonl(shard_path, LedgerEvent(
        ts=time.time(),
        type="HEALTH",
        payload={
            "probe": probe, "band_id": band.band_id,
            "zeros_found": zeros_found,
            "duration": end_time - start_time,
            "status": "COMPLETED"
        }
    ))

    return {
        "probe": probe,
        "band_id": band.band_id,
        "zeros_found": zeros_found,
        "residual_p95": p95_res,
        "shard_path": shard_path,
        "shard_sha256": _sha256_file(shard_path),
        "calib_out": {
            "n_zeros": calib_in.n_zeros + zeros_found,
            "residual_p95": max(calib_in.residual_p95, p95_res)
        }
    }

# -----------------------------
# Orchestrator
# -----------------------------

class RiemannDominoOrchestrator:
    def __init__(
        self,
        t_start: float,
        t_end: float,
        probe_names: List[str],
        band_width: float,
        out_dir: str,
        cfg: Optional[Dict[str, Any]] = None,
    ):
        self.t_start = t_start
        self.t_end = t_end
        self.probe_names = probe_names
        self.band_width = band_width
        self.out_dir = out_dir
        self.cfg = cfg or {}
        os.makedirs(out_dir, exist_ok=True)

        self.bands = self.partition_t_line(t_start, t_end, band_width)
        self.calib = CalibState()

    def partition_t_line(self, t0, t1, width) -> List[Band]:
        bands = []
        curr = t0
        idx = 0
        while curr < t1:
            nxt = min(curr + width, t1)
            bands.append(Band(band_id=idx, t0=curr, t1=nxt))
            curr = nxt
            idx += 1
        return bands

    def run_sweep(self) -> Dict[str, Any]:
        num_workers = os.cpu_count() or 8
        print(f"[SYSTEM] Unlocking all {num_workers} logical cores.")
        try:
            if os.name == 'nt':
                import psutil
                process = psutil.Process(os.getpid())
                process.nice(psutil.HIGH_PRIORITY_CLASS)
                print("[SYSTEM] Priority set to HIGH.")
        except:
            print("[SYSTEM] High priority request skipped.")
            
        print(f"[ORCHESTRATOR] Starting Domino Sweep with {num_workers} workers.")
        
        pending_bands = list(self.bands)
        active_futures = {}
        completed_results = []
        
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            # First wave
            for probe in self.probe_names:
                if not pending_bands: break
                band = pending_bands.pop(0)
                fut = executor.submit(mine_band_worker, probe, band, self.calib, self.out_dir, self.cfg)
                active_futures[fut] = (probe, band)
            
            # Domino cascading
            while active_futures:
                done, _ = wait(list(active_futures.keys()), return_when=FIRST_COMPLETED)
                for fut in done:
                    probe, old_band = active_futures.pop(fut)
                    try:
                        res = fut.result()
                        if "error" in res:
                             print(f"[ERROR] {probe} in band {old_band.band_id}: {res['error']}")
                        else:
                            completed_results.append(res)
                            # Wave propagation (Transfer of context)
                            self.calib.n_zeros += res.get("zeros_found", 0)
                            self.calib.residual_p95 = max(self.calib.residual_p95, res.get("residual_p95", 0))
                            print(f"[DOMINO] {probe} completed {old_band.band_id}. Zeros: {res.get('zeros_found')}. Context Updated.")
                    except Exception as e:
                        print(f"[CRITICAL] {probe} failed band {old_band.band_id}: {e}")
                    
                    # Next in line
                    if pending_bands:
                        new_band = pending_bands.pop(0)
                        nfut = executor.submit(mine_band_worker, probe, new_band, self.calib, self.out_dir, self.cfg)
                        active_futures[nfut] = (probe, new_band)

        return {"status": "SUCCESS", "bands_processed": len(completed_results), "total_zeros": self.calib.n_zeros}

if __name__ == "__main__":
    # Test Run
    orch = RiemannDominoOrchestrator(
        t_start=5000.0,
        t_end=5005.0,
        probe_names=["ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOXTROT", "GOLF", "HOTEL"],
        band_width=2.5,
        out_dir="./ledger_domino_riemann",
        cfg={"alpha": 0.5}
    )
    summary = orch.run_sweep()
    print(f"DONE. Sweep complete: {summary}")
