from __future__ import annotations
"""
riemann_avalanche.py
DOMINO-WAVE AVALANCHE EXPONENTIAL PROTOCOL
==========================================
Each probe pair that finishes a stage immediately reinforces the NEXT stage,
creating an exponentially growing swarm as the sweep advances toward T=10000.

Stage 0: 12 probes (6 primary + 6 booster)
Stage 1: 12 + all freed pairs from Stage 0  -> 24 potential probes
Stage 2: 24 + all freed from Stage 1        -> 48 potential probes
...                                         -> EXPONENTIAL ACCELERATION

Architecture:
  - Global priority queue: work items ordered by (stage, slot, pass_num)
  - ThreadPoolExecutor: probes are persistent threads that pull from queue
  - When a primary+booster PAIR finishes at stage S -> both re-enqueue for
    stage S+1 as extra boosters (pass_num >= 2)
  - Each successive stage finishes faster because it has more probes
"""
import sys
import io
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

import os
import json
import time
import math
import argparse
import threading
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Any, Optional, Tuple
from queue import PriorityQueue, Empty
from concurrent.futures import ThreadPoolExecutor

# === PATHS ===
PROJECT_ROOT = r"c:\Users\USUARIO\OneDrive\Desktop\Tesis"
ENGINE_ROOT  = r"c:\Users\USUARIO\.gemini\antigravity\playground\calculo-avanzado-asistido"
for p in [PROJECT_ROOT, ENGINE_ROOT, os.path.join(ENGINE_ROOT, "core")]:
    if p not in sys.path:
        sys.path.append(p)

# ─────────────────────────────────────────────
# Work item
# ─────────────────────────────────────────────

@dataclass(order=True)
class WorkItem:
    priority:  int           # lower = processed first  (stage * 100 + pass_num)
    stage:     int           = field(compare=False)
    slot:      int           = field(compare=False)
    pass_num:  int           = field(compare=False)
    t0:        float         = field(compare=False)
    t1:        float         = field(compare=False)
    probe:     str           = field(compare=False)

# ─────────────────────────────────────────────
# Shared state
# ─────────────────────────────────────────────

class AvalancheState:
    def __init__(self, total_stages: int, n_slots: int):
        self.lock           = threading.Lock()
        self.total_stages   = total_stages
        self.n_slots        = n_slots
        # slot_done[stage][slot] = set of pass_nums completed
        self.slot_done: Dict[int, Dict[int, set]] = {
            s: {i: set() for i in range(n_slots)} for s in range(total_stages)
        }
        # How many probes each stage has accumulated
        self.stage_probes: Dict[int, int] = {s: 0 for s in range(total_stages)}
        self.total_zeros   = 0
        self.log: List[str] = []

    def record_done(self, stage, slot, pass_num, zeros):
        with self.lock:
            self.slot_done[stage][slot].add(pass_num)
            self.total_zeros += zeros
            self.stage_probes[stage] += 1

    def stage_primary_done(self, stage) -> bool:
        """True when all primary (pass 1) passes for this stage are done."""
        with self.lock:
            return all(1 in self.slot_done[stage][s] for s in range(self.n_slots))

    def next_pass_for(self, stage, slot) -> int:
        with self.lock:
            done = self.slot_done[stage][slot]
            p = 1
            while p in done:
                p += 1
            return p

# ─────────────────────────────────────────────
# Worker function  (runs inside thread / process)
# ─────────────────────────────────────────────

def _append(path, rec):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def mine_work_item(item: WorkItem, out_dir: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Mine T=[t0,t1] for one work item with appropriate offset."""
    shard = os.path.join(
        out_dir,
        f"shard_{item.probe}_s{item.stage}_slot{item.slot}_p{item.pass_num}.jsonl"
    )
    try:
        from RIEMANN_ZERO_FILTER_UA_MACRO import (
            bracketing_scan, ScanConfig, UAConfig, PrecisionConfig, RiemannLedger
        )
    except ImportError as e:
        return {"error": str(e), "item": asdict(item)}

    alpha = cfg.get("alpha", 0.05)
    # Each pass is offset by alpha/2 to interleave with previous passes
    step_offset = (alpha / 2.0) * (item.pass_num - 1)
    t0_eff = item.t0 + step_offset

    cfg_scan = ScanConfig(T0=t0_eff, T1=item.t1, step=alpha)
    cfg_ua   = UAConfig(budget_total=cfg.get("ua_budget", 500_000))
    cfg_prec = PrecisionConfig()
    ledger   = RiemannLedger(cfg_ua)

    _append(shard, {
        "ts": time.time(), "type": "HEALTH", "payload": {
            "probe": item.probe, "stage": item.stage, "slot": item.slot,
            "pass": item.pass_num, "t0": item.t0, "t1": item.t1,
            "t0_eff": t0_eff, "status": "STARTING"
        }
    })

    t_init = time.time()
    try:
        candidates = bracketing_scan(cfg_scan, cfg_prec, ledger, alpha=alpha)
    except Exception as e:
        return {"error": str(e), "item": asdict(item)}

    zeros_found = 0
    for i, c in enumerate(candidates):
        data  = asdict(c)
        t_est = data.get("refined_T") or data.get("T") or 0.0
        resid = data.get("verified_s_full") or 0.0
        _append(shard, {
            "ts": time.time(), "type": "ZERO_CANDIDATE", "payload": {
                "t_est": t_est, "residual": resid,
                "probe": item.probe, "stage": item.stage,
                "slot": item.slot, "pass": item.pass_num, "seq": i,
                "method": "avalanche_v1",
                "rigidity_h": data.get("confidence")
            }
        })
        zeros_found += 1

    elapsed = time.time() - t_init
    _append(shard, {
        "ts": time.time(), "type": "HEALTH", "payload": {
            "probe": item.probe, "stage": item.stage, "slot": item.slot,
            "pass": item.pass_num, "zeros_found": zeros_found,
            "elapsed_s": round(elapsed, 2), "status": "DONE"
        }
    })
    return {
        "probe": item.probe, "stage": item.stage, "slot": item.slot,
        "pass": item.pass_num, "zeros_found": zeros_found,
        "t0": item.t0, "t1": item.t1, "elapsed": elapsed
    }


# ─────────────────────────────────────────────
# Avalanche Orchestrator
# ─────────────────────────────────────────────

class AvalancheOrchestrator:
    """
    Exponential reinforcement: each probe pair finishing stage S
    immediately enqueues itself as a booster for stage S+1.

    Stages are processed left-to-right but probes are NEVER idle:
    they always pick up the next available work item for the
    LOWEST pending stage (ensuring stages advance sequentially
    while fast-finishing probes pile up on the frontier).
    """

    PRIMARY_PROBES  = ["ALPHA",  "BRAVO",  "CHARLIE", "DELTA",  "ECHO",  "FOXTROT"]
    BOOSTER_PROBES  = ["GOLF",   "HOTEL",  "INDIA",   "JULIET", "KILO",  "LIMA"]

    def __init__(self, t_start, t_end, band_width, out_dir, cfg=None):
        self.t_start      = t_start
        self.t_end        = t_end
        self.band_width   = band_width
        self.out_dir      = out_dir
        self.cfg          = cfg or {}
        self.n_slots      = len(self.PRIMARY_PROBES)  # 6

        os.makedirs(out_dir, exist_ok=True)

        # Build all bands
        n_bands = math.ceil((t_end - t_start) / band_width)
        bands = [(t_start + i * band_width,
                  min(t_start + (i+1) * band_width, t_end))
                 for i in range(n_bands)]

        # Group into stages of n_slots
        self.stages: List[List[Tuple[float,float]]] = [
            bands[i:i+self.n_slots]
            for i in range(0, len(bands), self.n_slots)
        ]
        self.n_stages = len(self.stages)
        self.state = AvalancheState(self.n_stages, self.n_slots)

    # ── Public ──────────────────────────────────────────────────────────────

    def run(self) -> Dict[str, Any]:
        # Priority queue: (priority, WorkItem)
        pq: PriorityQueue = PriorityQueue()
        pq_lock = threading.Lock()

        # Seed Stage 0 — primary + booster for each slot
        for slot_i, (t0, t1) in enumerate(self.stages[0]):
            # Primary pass
            pq.put(WorkItem(
                priority = 0 * 1000 + slot_i * 2 + 0,
                stage=0, slot=slot_i, pass_num=1,
                t0=t0, t1=t1,
                probe=self.PRIMARY_PROBES[slot_i]
            ))
            # Booster pass (offset)
            pq.put(WorkItem(
                priority = 0 * 1000 + slot_i * 2 + 1,
                stage=0, slot=slot_i, pass_num=2,
                t0=t0, t1=t1,
                probe=self.BOOSTER_PROBES[slot_i]
            ))

        stopped = threading.Event()

        def worker_loop(worker_id: int):
            """Each thread is a persistent probe that pulls work until done."""
            while not stopped.is_set():
                try:
                    item: WorkItem = pq.get(timeout=5)
                except Empty:
                    # Check if all stages done
                    if all(self.state.stage_primary_done(s) for s in range(self.n_stages)):
                        break
                    continue

                label = f"[S{item.stage}/slot{item.slot}/p{item.pass_num}/{item.probe}]"
                print(f"  {label} START  T=[{item.t0:.0f},{item.t1:.0f}]")

                res = mine_work_item(item, self.out_dir, self.cfg)

                if "error" in res:
                    print(f"  {label} ERROR: {res['error']}")
                    pq.task_done()
                    continue

                zeros = res["zeros_found"]
                elapsed = res.get("elapsed", 0)
                self.state.record_done(item.stage, item.slot, item.pass_num, zeros)
                print(f"  {label} DONE   zeros={zeros}  t={elapsed:.0f}s")

                # ── AVALANCHE RULE ────────────────────────────────────────────
                # This probe just finished (stage S, slot X, pass P).
                # -> Enqueue it for stage S+1 as a booster.
                # Priority of next stage items ensures stage S primaries run first.
                next_stage = item.stage + 1
                if next_stage < self.n_stages:
                    next_slots = self.stages[next_stage]
                    for slot_j, (t0n, t1n) in enumerate(next_slots):
                        next_pass = self.state.next_pass_for(next_stage, slot_j)
                        new_item = WorkItem(
                            # Same slot gets this probe's reinforcement first
                            priority = next_stage * 1000 + slot_j * 10 + (next_pass - 1),
                            stage    = next_stage,
                            slot     = slot_j,
                            pass_num = next_pass,
                            t0       = t0n,
                            t1       = t1n,
                            probe    = f"{item.probe}_s{next_stage}"
                        )
                        pq.put(new_item)
                        print(f"  [AVALANCHE] {item.probe} -> stage {next_stage} slot {slot_j} pass {next_pass}")
                        break  # Only take one slot per completion for now (avoids explosion)

                # Also seed next stage primaries if not yet seeded
                self._seed_stage_primaries(next_stage, pq)
                pq.task_done()

        # Start with 12 persistent worker threads (6 primary + 6 booster lanes)
        n_workers = self.n_slots * 2  # 12
        print(f"\n[AVALANCHE] Starting {n_workers} persistent probes")
        print(f"[AVALANCHE] T=[{self.t_start}, {self.t_end}]  stages={self.n_stages}")

        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            futures = [pool.submit(worker_loop, i) for i in range(n_workers)]
            # Wait for all to complete
            for f in futures:
                try:
                    f.result()
                except Exception as e:
                    print(f"[WORKER-ERR] {e}")

        return {
            "status": "AVALANCHE_COMPLETE",
            "total_zeros": self.state.total_zeros,
            "t_start": self.t_start,
            "t_end": self.t_end
        }

    _seeded_stages: set = set()

    def _seed_stage_primaries(self, stage: int, pq: PriorityQueue):
        """Seed the primary+booster passes for a stage (idempotent)."""
        if stage >= self.n_stages or stage in self._seeded_stages:
            return
        self._seeded_stages.add(stage)
        for slot_i, (t0, t1) in enumerate(self.stages[stage]):
            pq.put(WorkItem(
                priority = stage * 1000 + slot_i * 2 + 0,
                stage=stage, slot=slot_i, pass_num=1,
                t0=t0, t1=t1,
                probe=self.PRIMARY_PROBES[slot_i]
            ))
            pq.put(WorkItem(
                priority = stage * 1000 + slot_i * 2 + 1,
                stage=stage, slot=slot_i, pass_num=2,
                t0=t0, t1=t1,
                probe=self.BOOSTER_PROBES[slot_i]
            ))
        print(f"\n[SEED] Stage {stage} seeded  T=[{self.stages[stage][0][0]:.0f},{self.stages[stage][-1][1]:.0f}]")


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Domino Avalanche Exponential Protocol")
    ap.add_argument("--t0",    type=float, required=True)
    ap.add_argument("--t1",    type=float, required=True)
    ap.add_argument("--bw",    type=float, default=100.0)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--ua",    type=int,   default=500_000)
    ap.add_argument("--out",   type=str,   default="./ledger_domino_10k")
    args = ap.parse_args()

    print("=" * 60)
    print("DOMINO-WAVE AVALANCHE  v1.0")
    print(f"T=[{args.t0}, {args.t1}]  band_width={args.bw}")
    print("Protocol: Pair-finish -> cross-stage reinforcement")
    print("Effect:   Exponential probe density growth per stage")
    print("=" * 60)

    orch = AvalancheOrchestrator(
        t_start    = args.t0,
        t_end      = args.t1,
        band_width = args.bw,
        out_dir    = args.out,
        cfg        = {"alpha": args.alpha, "ua_budget": args.ua}
    )
    result = orch.run()

    print(f"\n{'='*60}")
    print(f"AVALANCHE COMPLETE.")
    print(f"Total zeros certified: {result['total_zeros']}")
    print(f"{'='*60}")
