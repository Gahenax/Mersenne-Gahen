"""
booster_probe.py
Sonda auxiliar de refuerzo para el Domino Pyramid.
Mina el mismo rango de una sonda primaria pero con step_offset = alpha/2,
intercalando el escaneo para encontrar ceros complementarios.
"""
from __future__ import annotations
import sys, io, os, json, time, math, argparse
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

PROJECT_ROOT = r"c:\Users\USUARIO\OneDrive\Desktop\Tesis"
ENGINE_ROOT  = r"c:\Users\USUARIO\.gemini\antigravity\playground\calculo-avanzado-asistido"
for p in [PROJECT_ROOT, ENGINE_ROOT, os.path.join(ENGINE_ROOT, "core")]:
    if p not in sys.path:
        sys.path.append(p)

from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class SubBand:
    band_id: int
    stage: int
    slot: int
    t0: float
    t1: float
    pass_num: int = 1

def _append(path, rec):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def run_booster(probe_name, t0, t1, stage, slot, pass_num, alpha, out_dir, ua_budget):
    """Mine T=[t0, t1] with step_offset = alpha/2 * (pass_num-1)."""

    os.makedirs(out_dir, exist_ok=True)
    shard = os.path.join(
        out_dir,
        f"shard_{probe_name}_stage{stage}_slot{slot}_pass{pass_num}.jsonl"
    )

    try:
        from RIEMANN_ZERO_FILTER_UA_MACRO import (
            bracketing_scan, ScanConfig, UAConfig, PrecisionConfig, RiemannLedger
        )
    except ImportError as e:
        print(f"[BOOSTER-ERR] Engine not found: {e}")
        return

    step_offset = (alpha / 2.0) * (pass_num - 1)
    t0_eff = t0 + step_offset

    cfg_scan = ScanConfig(T0=t0_eff, T1=t1, step=alpha)
    cfg_ua   = UAConfig(budget_total=ua_budget)
    cfg_prec = PrecisionConfig()
    ledger   = RiemannLedger(cfg_ua)

    _append(shard, {
        "ts": time.time(), "type": "HEALTH",
        "payload": {
            "probe": probe_name, "stage": stage, "slot": slot,
            "pass": pass_num, "t0": t0, "t1": t1,
            "t0_eff": t0_eff, "step_offset": step_offset,
            "status": "BOOSTER_STARTING"
        }
    })
    print(f"[BOOSTER] {probe_name} -> T=[{t0_eff:.3f}, {t1}]  offset={step_offset:.4f}  shard={os.path.basename(shard)}")

    t_init = time.time()
    try:
        candidates = bracketing_scan(cfg_scan, cfg_prec, ledger, alpha=alpha)
    except Exception as e:
        print(f"[BOOSTER-ERR] {probe_name}: {e}")
        return

    zeros_found = 0
    for i, c in enumerate(candidates):
        data  = asdict(c)
        t_est = data.get("refined_T") or data.get("T") or 0.0
        resid = data.get("verified_s_full") or 0.0
        _append(shard, {
            "ts": time.time(), "type": "ZERO_CANDIDATE",
            "payload": {
                "t_est": t_est, "residual": resid,
                "probe": probe_name, "stage": stage, "slot": slot,
                "pass": pass_num, "seq": i,
                "method": "booster_v1",
                "rigidity_h": data.get("confidence")
            }
        })
        zeros_found += 1

    elapsed = time.time() - t_init
    _append(shard, {
        "ts": time.time(), "type": "HEALTH",
        "payload": {
            "probe": probe_name, "stage": stage, "slot": slot,
            "pass": pass_num, "zeros_found": zeros_found,
            "elapsed_s": round(elapsed, 2), "status": "BOOSTER_DONE"
        }
    })
    print(f"[BOOSTER] {probe_name} DONE. Zeros: {zeros_found}  ({elapsed:.0f}s)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Auxiliary booster probe")
    ap.add_argument("--name",    type=str,   required=True, help="Probe name, e.g. GOLF")
    ap.add_argument("--t0",      type=float, required=True)
    ap.add_argument("--t1",      type=float, required=True)
    ap.add_argument("--stage",   type=int,   default=0)
    ap.add_argument("--slot",    type=int,   default=0)
    ap.add_argument("--pass_num",type=int,   default=2, help="Pass number (>=2 = offset scan)")
    ap.add_argument("--alpha",   type=float, default=0.05)
    ap.add_argument("--ua",      type=int,   default=500_000)
    ap.add_argument("--out",     type=str,   default="./ledger_domino_10k")
    args = ap.parse_args()

    run_booster(
        probe_name=args.name,
        t0=args.t0,
        t1=args.t1,
        stage=args.stage,
        slot=args.slot,
        pass_num=args.pass_num,
        alpha=args.alpha,
        ua_budget=args.ua,
        out_dir=args.out,
    )
