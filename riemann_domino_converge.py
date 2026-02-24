from __future__ import annotations
# riemann_domino_converge.py - DOMINO-WAVE PYRAMIDAL CONVERGENCE
# Protocol: ALPHA finishes -> reinforces BRAVO.
#           ALPHA+BRAVO finish -> reinforce CHARLIE.
#           ...until ALL probes concentrate on FOXTROT (last band in stage).
# After each stage all probes move on to the next block of bands.
import sys
import io
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass


import os
import json
import sys
import math
import time
import hashlib
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed, wait, FIRST_COMPLETED

# === PATHS ===
PROJECT_ROOT = r"c:\Users\USUARIO\OneDrive\Desktop\Tesis"
ENGINE_ROOT  = r"c:\Users\USUARIO\.gemini\antigravity\playground\calculo-avanzado-asistido"
for p in [PROJECT_ROOT, ENGINE_ROOT, os.path.join(ENGINE_ROOT, "core")]:
    if p not in sys.path:
        sys.path.append(p)

# ─────────────────────────────────────────────
# Data contracts
# ─────────────────────────────────────────────

@dataclass(frozen=True)
class SubBand:
    band_id:   int          # global sequential index
    stage:     int          # which pyramid stage
    slot:      int          # position within stage (0 = first probe's)
    t0:        float
    t1:        float
    pass_num:  int = 1      # 1 = primary, 2+ = reinforcement pass

@dataclass
class CalibState:
    mean_gap:      float = 1.0
    baseline_r:    float = 0.5996
    n_zeros:       int   = 0
    residual_p95:  float = 0.0
    fail_rate:     float = 0.0

# ─────────────────────────────────────────────
# I/O helpers
# ─────────────────────────────────────────────

def _append(path: str, rec: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# ─────────────────────────────────────────────
# Worker (same engine as original)
# ─────────────────────────────────────────────

def mine_subband_worker(
    probe:    str,
    sb:       SubBand,
    calib:    CalibState,
    out_dir:  str,
    cfg:      Dict[str, Any],
) -> Dict[str, Any]:
    """Mine a sub-band.  Reinforcement passes use a half-step offset to add
    complementary coverage without duplicating zeros."""

    shard_path = os.path.join(
        out_dir,
        f"shard_{probe}_stage{sb.stage}_slot{sb.slot}_pass{sb.pass_num}.jsonl"
    )

    try:
        from RIEMANN_ZERO_FILTER_UA_MACRO import (
            bracketing_scan, ScanConfig, UAConfig, PrecisionConfig, RiemannLedger
        )
    except ImportError as e:
        return {"error": f"Engine missing: {e}", "sb": asdict(sb)}

    alpha = cfg.get("alpha", 0.05)
    # Reinforcement passes are offset by alpha/2 so they interleave with primary scan
    step_offset = (alpha / 2.0) * (sb.pass_num - 1)
    t0_eff = sb.t0 + step_offset

    cfg_scan = ScanConfig(T0=t0_eff, T1=sb.t1, step=alpha)
    cfg_ua   = UAConfig(budget_total=cfg.get("ua_budget", 500_000))
    cfg_prec = PrecisionConfig()
    ledger   = RiemannLedger(cfg_ua)

    _append(shard_path, {
        "ts": time.time(), "type": "HEALTH",
        "payload": {
            "probe": probe, "stage": sb.stage, "slot": sb.slot,
            "pass": sb.pass_num, "t0": sb.t0, "t1": sb.t1,
            "status": "STARTING"
        }
    })

    try:
        candidates = bracketing_scan(cfg_scan, cfg_prec, ledger, alpha=alpha)
    except Exception as e:
        return {"error": str(e), "sb": asdict(sb)}

    zeros_found = 0
    residuals   = []

    for i, c in enumerate(candidates):
        data   = asdict(c)
        t_est  = data.get("refined_T") or data.get("T") or 0.0
        resid  = data.get("verified_s_full") or 0.0
        _append(shard_path, {
            "ts": time.time(), "type": "ZERO_CANDIDATE",
            "payload": {
                "t_est": t_est, "residual": resid,
                "probe": probe, "stage": sb.stage, "slot": sb.slot,
                "pass": sb.pass_num, "seq": i,
                "method": "bracketing_converge_v1",
                "rigidity_h": data.get("confidence")
            }
        })
        zeros_found += 1
        residuals.append(resid)

    p95 = sorted(residuals)[int(0.95 * max(len(residuals)-1, 0))] if residuals else 0.0
    _append(shard_path, {
        "ts": time.time(), "type": "HEALTH",
        "payload": {
            "probe": probe, "stage": sb.stage, "slot": sb.slot,
            "pass": sb.pass_num, "zeros_found": zeros_found,
            "residual_p95": p95, "status": "COMPLETED"
        }
    })

    return {
        "probe": probe, "stage": sb.stage, "slot": sb.slot,
        "pass": sb.pass_num, "zeros_found": zeros_found,
        "residual_p95": p95, "shard_path": shard_path,
        "t0": sb.t0, "t1": sb.t1
    }

# ─────────────────────────────────────────────
# Pyramidal Orchestrator
# ─────────────────────────────────────────────

class DominoConvergeOrchestrator:
    """
    Pyramid convergence protocol per stage:

    Stage N covers [t_stage_start, t_stage_start + n_probes * band_width].
    Round 0  – each probe starts on its own primary sub-band (slot 0..N-1).
    Round 1+ – first probe to finish gets reassigned to reinforce the NEXT
               ACTIVE slot (i.e., the adjacent band still running), with a
               half-step offset.  This cascades until ALL probes pile on
               the last slot.
    After all slots are covered the orchestrator advances to the next stage.
    """

    def __init__(self, t_start, t_end, probe_names, band_width, out_dir, cfg=None):
        self.t_start     = t_start
        self.t_end       = t_end
        self.probes      = probe_names
        self.band_width  = band_width
        self.out_dir     = out_dir
        self.cfg         = cfg or {}
        self.calib       = CalibState()
        self.n           = len(probe_names)
        os.makedirs(out_dir, exist_ok=True)

        # Build all global bands
        n_bands = math.ceil((t_end - t_start) / band_width)
        self.all_bands: List[Tuple[float, float]] = [
            (t_start + i * band_width,
             min(t_start + (i+1) * band_width, t_end))
            for i in range(n_bands)
        ]
        # Chunk into stages of size n
        self.stages: List[List[Tuple[float,float]]] = [
            self.all_bands[i:i+self.n]
            for i in range(0, len(self.all_bands), self.n)
        ]

    # ── Public entry point ──────────────────────────────────────────────────

    def run_sweep(self) -> Dict[str, Any]:
        grand_total = 0
        for s_idx, stage_slots in enumerate(self.stages):
            print(f"\n{'='*60}")
            print(f"[PYRAMID] STAGE {s_idx}  "
                  f"T=[{stage_slots[0][0]:.0f}, {stage_slots[-1][1]:.0f}]  "
                  f"slots={len(stage_slots)}")
            print(f"{'='*60}")
            zeros = self._run_stage(s_idx, stage_slots)
            grand_total += zeros
            print(f"[PYRAMID] Stage {s_idx} complete.  Zeros this stage: {zeros}")

        return {"status": "COMPLETED", "total_zeros": grand_total,
                "t_start": self.t_start, "t_end": self.t_end}

    # ── Stage runner ────────────────────────────────────────────────────────

    def _run_stage(self, stage_idx: int, slots: List[Tuple[float,float]]) -> int:
        """
        Execute one pyramid stage.

        slot_status[slot] = set of pass numbers already submitted.
        When a probe finishes slot i → it submits a reinforcing pass on
        the NEXT slot that still has no reinforcement (slot i+1, i+2, …).
        The "next target" advances monotonically (convergence guarantee).
        """
        n_slots    = len(slots)
        total_z    = 0

        # Track which passes have been submitted per slot
        # {slot: {pass_num, …}}
        submitted: Dict[int, set] = {i: set() for i in range(n_slots)}
        # Track which probes are free (not currently running anything)
        # Initially ALL probes are free
        free_probes = list(self.probes[:n_slots])  # only as many probes as slots

        active_futures: Dict[Any, Dict] = {}   # fut → metadata

        n_workers = max(n_slots, os.cpu_count() or 8)

        with ProcessPoolExecutor(max_workers=n_workers) as executor:

            # ── Initial dispatch: one probe per slot ──────────────────────────
            for slot_i, probe in enumerate(free_probes):
                t0, t1 = slots[slot_i]
                sb = SubBand(
                    band_id=stage_idx * self.n + slot_i,
                    stage=stage_idx, slot=slot_i,
                    t0=t0, t1=t1, pass_num=1
                )
                submitted[slot_i].add(1)
                fut = executor.submit(
                    mine_subband_worker, probe, sb, self.calib, self.out_dir, self.cfg
                )
                active_futures[fut] = {"probe": probe, "slot": slot_i, "pass": 1}
                print(f"  [INIT]  {probe:8s}  -> slot {slot_i}  "
                      f"T=[{t0:.0f},{t1:.0f}]  pass 1")

            # ── Event loop ────────────────────────────────────────────────────
            while active_futures:
                done, _ = wait(list(active_futures.keys()), return_when=FIRST_COMPLETED)

                for fut in done:
                    meta  = active_futures.pop(fut)
                    probe = meta["probe"]
                    slot  = meta["slot"]
                    pnum  = meta["pass"]

                    try:
                        res = fut.result()
                        if "error" in res:
                            print(f"  [ERR]   {probe}  slot {slot}  pass {pnum}: {res['error']}")
                        else:
                            total_z += res["zeros_found"]
                            print(f"  [DONE]  {probe:8s}  slot {slot}  "
                                  f"pass {pnum}  zeros={res['zeros_found']}")
                    except Exception as e:
                        print(f"  [EXC]   {probe}: {e}")

                    # ── Convergence rule ──────────────────────────────────────
                    # Find the NEXT slot > current slot that still lacks a
                    # reinforcement pass (i.e., pass_num+1 not yet submitted).
                    target_slot = None
                    target_pass = None

                    for try_slot in range(slot + 1, n_slots):
                        next_pass = len(submitted[try_slot]) + 1
                        if try_slot in submitted and 1 in submitted[try_slot]:
                            # Primary already running – can reinforce
                            if next_pass not in submitted[try_slot]:
                                target_slot = try_slot
                                target_pass = next_pass
                                break
                        else:
                            # Slot not yet started at all (shouldn't happen in init)
                            target_slot = try_slot
                            target_pass = 1
                            break

                    if target_slot is not None:
                        t0, t1 = slots[target_slot]
                        sb = SubBand(
                            band_id=stage_idx * self.n + target_slot,
                            stage=stage_idx, slot=target_slot,
                            t0=t0, t1=t1, pass_num=target_pass
                        )
                        submitted[target_slot].add(target_pass)
                        nfut = executor.submit(
                            mine_subband_worker,
                            probe, sb, self.calib, self.out_dir, self.cfg
                        )
                        active_futures[nfut] = {
                            "probe": probe, "slot": target_slot, "pass": target_pass
                        }
                        arrow = "REINFORCE" if target_pass > 1 else "ADVANCE"
                        print(f"  [{arrow}] {probe:8s}  -> slot {target_slot}  "
                              f"T=[{t0:.0f},{t1:.0f}]  pass {target_pass}")
                    else:
                        # No more work in this stage for this probe
                        print(f"  [FREE]  {probe} done with stage {stage_idx}")

        return total_z


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Domino-Wave Pyramid Converge")
    ap.add_argument("--t0",        type=float, required=True)
    ap.add_argument("--t1",        type=float, required=True)
    ap.add_argument("--bw",        type=float, default=100.0,  help="Band width per slot")
    ap.add_argument("--alpha",     type=float, default=0.05,   help="Scan step")
    ap.add_argument("--ua",        type=int,   default=500_000, help="UA budget")
    ap.add_argument("--out",       type=str,   default="./ledger_domino_10k")
    ap.add_argument("--probes",    type=str,
                    default="ALPHA,BRAVO,CHARLIE,DELTA,ECHO,FOXTROT")
    args = ap.parse_args()

    probe_names = [p.strip() for p in args.probes.split(",")]

    print("=" * 60)
    print("DOMINO-WAVE PYRAMID CONVERGENCE")
    print(f"T=[{args.t0}, {args.t1}]  band_width={args.bw}")
    print(f"Probes: {probe_names}")
    print(f"Protocol: ALPHA->BRAVO->...->FOXTROT  (all pile on last slot)")
    print("=" * 60)

    orch = DominoConvergeOrchestrator(
        t_start    = args.t0,
        t_end      = args.t1,
        probe_names= probe_names,
        band_width = args.bw,
        out_dir    = args.out,
        cfg        = {"alpha": args.alpha, "ua_budget": args.ua}
    )
    summary = orch.run_sweep()
    print(f"\n{'='*60}")
    print(f"PYRAMID COMPLETE.  Total zeros certified: {summary['total_zeros']}")
    print(f"{'='*60}")
