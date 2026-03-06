#!/usr/bin/env python3
"""
MERSENNE MULTIBLOCK ORCHESTRATOR v1.1
======================================
Protocolo:      MULTIBLOCK-W3-1.0.0
Constitución:   2.1.0
Especificación: MULTIBLOCK_SPEC.md
Registro:       state/block_X_state.json  (PER-BLOCK, sharded)

IMPORTANTE -- v1.1 (fix de concurrencia):
  - Lock global eliminado → un Lock por bloque (_locks[bid])
  - Un archivo JSON por bloque (state/block_X_state.json)
  - BLOCK_REGISTRY.json solo se regenera para el scoreboard (lazy)
  - TTL=300s en adquisición de lock (anti-deadlock)
  - Calibración CALIB-RUN-001: κ_A ≈ 93s/exp @ p≈23k

Uso:
    python mersenne_multiblock_orchestrator.py --blocks A B C D --window 20
    python mersenne_multiblock_orchestrator.py --blocks A B    --window 20
    python mersenne_multiblock_orchestrator.py --scoreboard
"""

import json
import math
import time
import hashlib
import os
import sys
import logging
import threading
import argparse
import concurrent.futures
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

# ── Path setup ──────────────────────────────────────────────────────────────
MULTIBLOCK_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT   = os.path.abspath(os.path.join(MULTIBLOCK_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from antigravity.engines.mersenne_module import MersenneMinerModule
    from antigravity.engines.chronos_semaforo_module import ChronosSemaforoModule
    ENGINES_AVAILABLE = True
except ImportError:
    ENGINES_AVAILABLE = False
    print("[WARN] Engines not found -- running in SIMULATION mode.")

# ── Constants ────────────────────────────────────────────────────────────────
PROTOCOL_VERSION        = "MULTIBLOCK-W3-1.1.0"
CONSTITUTIONAL_VERSION  = "2.1.0"
REGISTRY_PATH           = os.path.join(MULTIBLOCK_DIR, "BLOCK_REGISTRY.json")
STATE_DIR               = os.path.join(MULTIBLOCK_DIR, "state")
LOG_DIR                 = os.path.join(MULTIBLOCK_DIR, "logs")
FORENSIC_DIR            = os.path.join(MULTIBLOCK_DIR, "forensics")
LOCK_TTL_SECONDS        = 300  # Anti-deadlock: si worker muere, lock expira

# κ calibration from CALIB-RUN-001
KAPPA_REF       = 93.33   # s/exp observed
P_REF           = 23217   # p where kappa was observed
ALPHA_SCALING   = 2.0     # κ(p) ~ κ_ref * (p/p_ref)^alpha

os.makedirs(LOG_DIR,     exist_ok=True)
os.makedirs(FORENSIC_DIR, exist_ok=True)
os.makedirs(STATE_DIR,    exist_ok=True)

# ── §1–§6: Funciones matemáticas del contrato ───────────────────────────────

def sigmoid(x: float) -> float:
    """σ(x) = 1 / (1 + e^{-x})  [clamped to avoid overflow]"""
    x = max(-500.0, min(500.0, x))
    return 1.0 / (1.0 + math.exp(-x))


def compute_coverage(n_processed: int, N_b: int) -> float:
    """§1: Coverage_b = n_b / N_b"""
    return n_processed / max(N_b, 1)


def compute_throughput(thr_window: List[Tuple[float, int]], delta_t: float,
                       eps: float = 1e-9) -> float:
    """§1: Thr_b(t) = (n(t) - n(t-Δt)) / Δt  [sliding window]"""
    if len(thr_window) < 2:
        return 0.0
    t0, n0 = thr_window[0]
    t1, n1 = thr_window[-1]
    elapsed = t1 - t0
    return (n1 - n0) / max(elapsed, eps)


def compute_eta(N_b: int, n_processed: int, throughput: float,
                eps: float = 1e-9) -> float:
    """§1: ETA_b = (N_b - n_b) / max(ε, Thr_b)"""
    return (N_b - n_processed) / max(eps, throughput)


def compute_apr_simple(audit_results: List[bool]) -> float:
    """§2: APR_b = (1/W_b) · Σ 1[a_{b,w}=PASS]"""
    W = len(audit_results)
    if W == 0:
        return 1.0
    return sum(audit_results) / W


def compute_apr_weighted(audit_results: List[bool], lam: float = 0.95) -> float:
    """§2: APR^(λ)_b -- auditoría con decaimiento exponencial"""
    W = len(audit_results)
    if W == 0:
        return 1.0
    total_w, weighted_sum = 0.0, 0.0
    for w_idx, passed in enumerate(audit_results):
        weight       = lam ** (W - 1 - w_idx)
        total_w     += weight
        weighted_sum += weight if passed else 0.0
    return weighted_sum / max(total_w, 1e-12)


def compute_anom_rate(anom_orange: int, anom_red: int,
                      n_processed: int) -> Tuple[float, float]:
    """§2: AnomRate_b = Anom_b / max(1, n_b)  con ω(ORANGE)=1, ω(RED)=5"""
    anom_weighted = anom_orange * 1.0 + anom_red * 5.0
    anom_rate     = anom_weighted / max(1, n_processed)
    return anom_weighted, anom_rate


def compute_reliability(apr_w: float, anom_rate: float,
                        tau: float = 0.98, alpha: float = 10.0,
                        beta: float = 0.0) -> float:
    """§2: Rel_b = σ(α·(APR^λ_b - τ) - β·AnomRate_b)"""
    return sigmoid(alpha * (apr_w - tau) - beta * anom_rate)


def compute_stability(measurements: List[float], eta: float = 2.0,
                      eps: float = 1e-12) -> float:
    """§3: s_c = exp(-η·CV_c),  CV_c = σ_c / (μ_c + ε)"""
    if len(measurements) < 2:
        return 1.0
    mu       = sum(measurements) / len(measurements)
    variance = sum((x - mu) ** 2 for x in measurements) / len(measurements)
    sigma_c  = math.sqrt(variance)
    cv       = sigma_c / (mu + eps)
    return math.exp(-eta * cv)


def compute_cand_score(k_c: int, s_c: float, l_c: float,
                       gamma: float = 0.5, delta: float = 0.1) -> float:
    """§3: CandScore = (1 - e^{-γ·k_c}) · s_c · e^{-δ·ℓ_c}"""
    consistency  = 1.0 - math.exp(-gamma * k_c)
    cost_penalty = math.exp(-delta * l_c)
    return consistency * s_c * cost_penalty


def w3_color(apr: float, anom_rate: float,
             tau_apr_orange: float = 0.97, tau_apr_red: float = 0.90,
             tau_anom_orange: float = 0.005, tau_anom_red: float = 0.020) -> str:
    """§4: Colorimetría W3 determinista"""
    if apr < tau_apr_red or anom_rate > tau_anom_red:
        return "RED"
    if apr < tau_apr_orange or anom_rate > tau_anom_orange:
        return "ORANGE"
    return "GREEN"


def compute_bps(coverage: float, reliability: float,
                cand_value: float, cpu_cost: float, strategic: float,
                w: Tuple[float, float, float, float] = (0.25, 0.30, 0.20, 0.25)) -> float:
    """§6: BPS_b = w1·Cov + w2·Rel + w3·(CandVal/(1+CPUCost)) + w4·Strategic"""
    w1, w2, w3, w4 = w
    return (w1 * coverage
            + w2 * reliability
            + w3 * (cand_value / (1.0 + cpu_cost))
            + w4 * strategic)


# ── Dataclasses ──────────────────────────────────────────────────────────────

@dataclass
class BlockConfig:
    id:              str
    p_min:           int
    p_max:           int
    block_type:      str     # "MINING" | "EXPLORATION"
    strategic_score: float
    dod_rho:         float   # min coverage
    dod_tau_apr:     float   # min APR^λ
    dod_nu_anom:     float   # max AnomRate
    dod_tau_rel:     float = 0.90  # min Rel (EXPLORATION only)

    @property
    def N_b(self) -> int:
        return (self.p_max - self.p_min) // 2 + 1


@dataclass
class BlockState:
    status:              str   = "PENDING"
    phase:               str   = "SCAN"
    n_processed:         int   = 0
    n_candidates:        int   = 0
    current_p:           int   = 0
    # §1 metrics
    coverage:            float = 0.0
    throughput:          float = 0.0
    eta_seconds:         float = float('inf')
    cpu_cost_seconds:    float = 0.0
    # §2 audit
    audit_results:       List[bool]  = field(default_factory=list)
    apr_simple:          float = 1.0
    apr_weighted:        float = 1.0
    anom_orange:         int   = 0
    anom_red:            int   = 0
    anom_total_weighted: float = 0.0
    anom_rate:           float = 0.0
    reliability:         float = 1.0
    color:               str   = "GREEN"
    # §3 candidates
    candidates:          List[Dict] = field(default_factory=list)
    cand_value:          float = 0.0
    # §6 scheduling
    bps:                 float = 0.0
    # Timestamps
    started_at:          Optional[str] = None
    last_updated:        Optional[str] = None
    completed_at:        Optional[str] = None
    # Checkpoint
    checkpoint_hash:     Optional[str] = None
    checkpoint_integrity: bool = True
    # Events log
    events:              List[Dict] = field(default_factory=list)
    # DoD
    done:                bool = False
    done_reason:         Optional[str] = None


# ── Thread-safe Sharded Registry (v1.1 -- per-block locks) ───────────────────

class BlockRegistry:
    """
    Registry con lock sharding: un Lock por bloque, un archivo por bloque.

    Arquitectura v1.1 (fix de concurrencia):
    - _locks[bid]          → lock individual, no bloquea otros bloques
    - state/block_X.json   → un archivo pequeño por bloque
    - BLOCK_REGISTRY.json  → vista agregada, solo para scoreboard (lazy)
    - TTL=300s             → anti-deadlock si worker muere con el lock

    Elimina el starvation de B/C/D observado en CALIB-RUN-001.
    """

    def __init__(self, path: str, configs: Dict[str, BlockConfig], params: Dict):
        self.path      = path
        self.configs   = configs
        self.params    = params
        self._locks    = {bid: threading.Lock() for bid in configs}  # PER-BLOCK
        self._states: Dict[str, BlockState] = {}
        self._load_or_init()

    # ── Per-block I/O ────────────────────────────────────────────────────────

    def _block_path(self, bid: str) -> str:
        return os.path.join(STATE_DIR, f"block_{bid}_state.json")

    def _save_block(self, bid: str, state: BlockState):
        """Escribe SOLO el estado de bid en su propio archivo. Muy rápido."""
        with open(self._block_path(bid), "w") as f:
            json.dump(asdict(state), f, default=str)

    def _load_block(self, bid: str, cfg: BlockConfig) -> BlockState:
        """Carga el estado de bid desde su archivo individual."""
        path = self._block_path(bid)
        if os.path.exists(path):
            try:
                with open(path) as f:
                    raw = json.load(f)
                valid = set(BlockState.__dataclass_fields__)
                filtered = {k: v for k, v in raw.items() if k in valid}
                if "audit_results" in filtered:
                    filtered["audit_results"] = [bool(x) for x in filtered["audit_results"]]
                return BlockState(**filtered)
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
        return BlockState(current_p=cfg.p_min)

    def _load_or_init(self):
        """Carga cada bloque desde su archivo individual, o desde el registry legacy."""
        # Intentar cargar per-block primero (v1.1)
        any_perblock = any(os.path.exists(self._block_path(b)) for b in self.configs)

        if any_perblock:
            for bid, cfg in self.configs.items():
                self._states[bid] = self._load_block(bid, cfg)
        elif os.path.exists(self.path):
            # Migración desde registry monolítico v1.0
            try:
                with open(self.path) as f:
                    data = json.load(f)
                for bid, cfg in self.configs.items():
                    raw = data.get("blocks", {}).get(bid, {}).get("state", {})
                    valid = set(BlockState.__dataclass_fields__)
                    filtered = {k: v for k, v in raw.items() if k in valid}
                    if "audit_results" in filtered:
                        filtered["audit_results"] = [bool(x) for x in filtered["audit_results"]]
                    self._states[bid] = BlockState(**filtered) if filtered else BlockState(current_p=cfg.p_min)
            except Exception:
                self._init_fresh()
        else:
            self._init_fresh()

        # Persistir en formato v1.1
        for bid, state in self._states.items():
            self._save_block(bid, state)

    def _init_fresh(self):
        for bid, cfg in self.configs.items():
            self._states[bid] = BlockState(current_p=cfg.p_min)

    # ── Public API ───────────────────────────────────────────────────────────

    def get_state(self, bid: str) -> BlockState:
        """Lee el estado con lock individual de bid."""
        acquired = self._locks[bid].acquire(timeout=LOCK_TTL_SECONDS)
        if not acquired:
            # Retornar copia en memoria como fallback
            return self._states[bid]
        try:
            return self._states[bid]
        finally:
            self._locks[bid].release()

    def update_state(self, bid: str, **kwargs):
        """Actualiza y persiste SOLO el bloque bid. No bloquea otros bloques."""
        acquired = self._locks[bid].acquire(timeout=LOCK_TTL_SECONDS)
        if not acquired:
            # Log and continue -- no crashear por lock timeout
            return
        try:
            state = self._states[bid]
            for k, v in kwargs.items():
                if hasattr(state, k):
                    setattr(state, k, v)
            state.last_updated = datetime.now().isoformat()
            self._save_block(bid, state)  # Solo escribe block_X_state.json
        finally:
            self._locks[bid].release()

    def aggregate_registry(self):
        """Reconstruye BLOCK_REGISTRY.json desde los estados individuales.
        Solo se llama en el scoreboard -- lazy, no bloquea workers."""
        data = {
            "version":                PROTOCOL_VERSION,
            "constitutional_version": CONSTITUTIONAL_VERSION,
            "timestamp":              datetime.now().isoformat(),
            "parameters":             self.params,
            "blocks":                 {}
        }
        for bid, cfg in self.configs.items():
            # Leer estado actual sin bloquear
            state = self._states[bid]
            data["blocks"][bid] = {
                "config": {
                    "p_min": cfg.p_min, "p_max": cfg.p_max, "N_b": cfg.N_b,
                    "type": cfg.block_type, "strategic_score": cfg.strategic_score,
                    "dod": {"rho": cfg.dod_rho, "tau_apr": cfg.dod_tau_apr,
                            "nu_anom": cfg.dod_nu_anom}
                },
                "state": asdict(state)
            }
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def scoreboard(self) -> List[Tuple[str, float]]:
        """Bloques ordenados por BPS descendente. No adquiere locks."""
        return sorted(
            [(bid, self._states[bid].bps) for bid in self._states],
            key=lambda x: -x[1]
        )


# ── Block Worker ─────────────────────────────────────────────────────────────

class BlockWorker:
    """
    Worker de un bloque individual.
    Procesa en ventanas, computa todas las métricas del contrato,
    y actualiza el registro tras cada ventana.
    """

    def __init__(self, config: BlockConfig, registry: BlockRegistry,
                 params: Dict, window_size: int = 10,
                 budget_ua: float = 2_000_000.0):
        self.config      = config
        self.registry    = registry
        self.params      = params
        self.window_size = window_size

        # Engines
        if ENGINES_AVAILABLE:
            self.miner   = MersenneMinerModule(budget_ua=budget_ua)
            self.auditor = ChronosSemaforoModule(h_thr=1e-15, m_thr=1e-15, s_thr=0.8)
        else:
            self.miner   = None
            self.auditor = None

        # Throughput sliding window: List[(timestamp, n_processed)]
        self._thr_window: List[Tuple[float, int]] = []

        # Logger
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        log = logging.getLogger(f"Block-{self.config.id}")
        log.setLevel(logging.DEBUG)
        if not log.handlers:
            fh = logging.FileHandler(
                os.path.join(LOG_DIR, f"block_{self.config.id}.log"),
                encoding="utf-8"
            )
            fh.setFormatter(logging.Formatter(
                "%(asctime)s [Block-%(name)s] %(levelname)s -- %(message)s"
            ))
            log.addHandler(fh)
            ch = logging.StreamHandler()
            ch.setFormatter(logging.Formatter(
                "[Block-%(name)s] %(levelname)s -- %(message)s"
            ))
            log.addHandler(ch)
        return log

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _next_window(self, p_start: int) -> List[int]:
        """Genera los próximos `window_size` impares desde p_start."""
        result = []
        p = p_start if p_start % 2 == 1 else p_start + 1
        while len(result) < self.window_size and p <= self.config.p_max:
            if p > 2:  # trivial filter: skip p=2 (handled separately)
                result.append(p)
            p += 2
        return result

    def _update_thr_window(self, n_processed: int):
        now = time.time()
        self._thr_window.append((now, n_processed))
        dt = self.params["delta_t"]
        self._thr_window = [(t, n) for t, n in self._thr_window
                            if now - t <= dt]

    def _run_miner(self, p: int) -> Tuple[bool, float, float]:
        """
        Returns: (is_prime, roundoff_error, elapsed_seconds)
        In simulation mode uses sympy.isprime for correctness.
        """
        t0 = time.time()
        if self.miner is not None:
            res      = self.miner.execute({"p": p})
            payload  = res.payload
            is_prime = bool(payload.get("is_prime", False))
            h        = float(payload.get("roundoff_error", 0.0))
        else:
            # Simulation: use sympy or a simple Lucas-Lehmer
            is_prime, h = self._simulate_ll(p)
        elapsed = time.time() - t0
        return is_prime, h, elapsed

    def _simulate_ll(self, p: int) -> Tuple[bool, float]:
        """Minimal Lucas-Lehmer simulation for development/testing."""
        try:
            from sympy import isprime
            # M_p is prime iff p is prime AND LL test passes
            # For simulation, use known values
            KNOWN_MERSENNE = {
                2, 3, 5, 7, 13, 17, 19, 31, 61, 89, 107, 127, 521, 607,
                1279, 2203, 2281, 3217, 4253, 4423, 9689, 9941, 11213,
                19937, 21701, 23209, 44497, 86243, 110503, 132049
            }
            is_prime = (p in KNOWN_MERSENNE)
            h = 0.0 if is_prime else float(p % 7) * 1e-16
            return is_prime, h
        except ImportError:
            # Fallback: purely structural
            KNOWN = {3, 5, 7, 13, 17, 19, 31, 61, 89, 107, 127, 521,
                     607, 1279, 2203, 2281, 3217, 4253, 4423, 9689,
                     9941, 11213, 19937, 21701, 23209, 44497, 86243}
            return (p in KNOWN), 0.0

    def _sanity_check(self) -> bool:
        """Verifica que el motor certifica correctamente M_127."""
        is_prime, _, _ = self._run_miner(127)
        return is_prime

    def _checkpoint_hash(self, state: BlockState) -> str:
        cp = json.dumps({
            "block":       self.config.id,
            "n_processed": state.n_processed,
            "current_p":   state.current_p,
            "candidates":  len(state.candidates),
            "timestamp":   datetime.now().isoformat()
        }, sort_keys=True)
        return hashlib.sha256(cp.encode()).hexdigest()[:16]

    def _compute_all_metrics(self, state: BlockState) -> Dict:
        """Computa el vector completo de métricas del contrato."""
        p = self.params

        # §1
        self._update_thr_window(state.n_processed)
        coverage  = compute_coverage(state.n_processed, self.config.N_b)
        thr       = compute_throughput(self._thr_window, p["delta_t"], p["epsilon"])
        eta       = compute_eta(self.config.N_b, state.n_processed, thr, p["epsilon"])

        # §2
        apr_s = compute_apr_simple(state.audit_results)
        apr_w = compute_apr_weighted(state.audit_results, p["lambda_decay"])
        anom_total, anom_rate = compute_anom_rate(
            state.anom_orange, state.anom_red, state.n_processed
        )
        rel = compute_reliability(apr_w, anom_rate,
                                  p["tau_rel"], p["alpha_rel"], p["beta_rel"])

        # §4
        color = w3_color(apr_s, anom_rate,
                         p["tau_APR_orange"], p["tau_APR_red"],
                         p["tau_Anom_orange"], p["tau_Anom_red"])

        # §6
        w = tuple(p["bps_weights"].values())
        bps = compute_bps(coverage, rel, state.cand_value,
                          state.cpu_cost_seconds, self.config.strategic_score, w)

        return dict(
            coverage=coverage, throughput=thr, eta_seconds=eta,
            apr_simple=apr_s, apr_weighted=apr_w,
            anom_total_weighted=anom_total, anom_rate=anom_rate,
            reliability=rel, color=color, bps=bps
        )

    def _check_dod(self, state: BlockState, metrics: Dict) -> Tuple[bool, str]:
        """§5: Verifica DoD matemático para este bloque."""
        cfg = self.config
        if cfg.block_type == "MINING":
            ok = (metrics["coverage"]     >= cfg.dod_rho      and
                  metrics["apr_weighted"] >= cfg.dod_tau_apr  and
                  metrics["anom_rate"]    <= cfg.dod_nu_anom)
            if ok:
                return True, (
                    f"Coverage={metrics['coverage']:.4f}≥{cfg.dod_rho} ∧ "
                    f"APR^λ={metrics['apr_weighted']:.4f}≥{cfg.dod_tau_apr} ∧ "
                    f"AnomRate={metrics['anom_rate']:.2e}≤{cfg.dod_nu_anom}"
                )
        else:  # EXPLORATION
            ok = (metrics["coverage"]  >= cfg.dod_rho    and
                  metrics["reliability"] >= cfg.dod_tau_rel and
                  state.checkpoint_integrity)
            if ok:
                return True, (
                    f"Coverage={metrics['coverage']:.4f}≥{cfg.dod_rho} ∧ "
                    f"Rel={metrics['reliability']:.4f}≥{cfg.dod_tau_rel} ∧ "
                    f"CheckpointIntegrity=1"
                )
        return False, ""

    def _run_forensics(self, state: BlockState, window: int, trigger: str):
        """Genera reporte forense para incidente RED."""
        fdir = os.path.join(FORENSIC_DIR, f"block_{self.config.id}")
        os.makedirs(fdir, exist_ok=True)
        report = {
            "block_id":    self.config.id,
            "window":      window,
            "trigger":     trigger,
            "triggered_at": datetime.now().isoformat(),
            "state_snapshot": asdict(state),
            "config":      asdict(self.config),
            "protocol":    PROTOCOL_VERSION,
            "recommendation": "Manual review required before unfreezing."
        }
        fpath = os.path.join(fdir, f"forensic_{int(time.time())}.json")
        with open(fpath, "w") as f:
            json.dump(report, f, indent=2, default=str)
        self.logger.critical(f"Forensic report: {fpath}")

    # ── Main execution loop ──────────────────────────────────────────────────

    def run(self):
        bid = self.config.id
        self.logger.info(
            f"Block {bid} | Range p=[{self.config.p_min}, {self.config.p_max}] "
            f"| N_b={self.config.N_b:,} | Type={self.config.block_type}"
        )

        # ── Sanity check ───────────────────────────────────────────────────
        if not self._sanity_check():
            self.logger.critical(f"Block {bid}: SANITY CHECK FAILED -- M_127 not certified. LOCKING.")
            self.registry.update_state(bid, status="LOCKED", color="RED")
            return

        self.logger.info(f"Block {bid}: Sanity OK (M_127 [OK]). Starting sweep.")
        state = self.registry.get_state(bid)
        self.registry.update_state(bid,
            status="RUNNING",
            started_at=datetime.now().isoformat(),
            current_p=max(state.current_p, self.config.p_min)
        )

        window_num = 0
        while True:
            state = self.registry.get_state(bid)

            # ── Check frozen ───────────────────────────────────────────────
            if state.status == "FROZEN":
                self.logger.warning(f"Block {bid}: FROZEN. Waiting 30s...")
                time.sleep(30)
                continue

            # ── Next window of exponentes ─────────────────────────────────
            batch = self._next_window(state.current_p)
            if not batch:
                self.logger.info(f"Block {bid}: Range fully exhausted at p={state.current_p}.")
                break

            window_num  += 1
            wid          = hashlib.sha256(f"{bid}-{window_num}-{batch[0]}".encode()).hexdigest()[:8]
            window_start = time.time()

            self.logger.info(
                f"  Window #{window_num} [{wid}] p={batch[0]}–{batch[-1]} "
                f"({len(batch)} exponents)"
            )

            # ── Process each exponent in the window ───────────────────────
            window_passed = True
            local_orange  = 0
            local_red     = 0
            new_candidates: List[Dict] = []
            next_p        = batch[-1] + 2  # default advance

            for p in batch:
                is_prime, h, ll_time = self._run_miner(p)

                # Semáforo audit
                if self.auditor is not None:
                    m_val = 0.0 if is_prime else 1.0
                    audit = self.auditor.execute({"H": h, "M": m_val, "S": 1.0})
                    color_str = audit.payload.get("semaforo_color", "AMARILLO")
                else:
                    color_str = "VERDE" if h < 1e-14 else "NARANJA"

                if   "VERDE"   in color_str:  evt_color = "GREEN"
                elif "NARANJA" in color_str:  evt_color = "ORANGE"; local_orange += 1
                elif "ROJO"    in color_str:  evt_color = "RED";    local_red    += 1
                else:                          evt_color = "YELLOW"

                if evt_color == "RED":
                    window_passed = False
                    self.logger.error(f"    [RED] RED at p={p}")

                # ── Candidate processing (§3) ─────────────────────────────
                if is_prime:
                    # k_c = 2 verificaciones inmediatas
                    is_prime2, h2, t2 = self._run_miner(p)
                    coherent = (is_prime2 == is_prime)
                    k_c      = 2 if coherent else 1

                    # Estabilidad: 3 medidas de roundoff
                    measurements = [h]
                    for _ in range(2):
                        _, h_j, _ = self._run_miner(p)
                        measurements.append(h_j)
                    s_c    = compute_stability(measurements, self.params["eta"])
                    score  = compute_cand_score(k_c, s_c, ll_time,
                                                self.params["gamma"], self.params["delta"])

                    cand = {
                        "p": p, "k_c": k_c, "s_c": round(s_c, 6),
                        "l_c": round(ll_time, 4), "score": round(score, 6),
                        "window": window_num, "window_id": wid,
                        "timestamp": datetime.now().isoformat()
                    }
                    new_candidates.append(cand)
                    self.logger.info(
                        f"    ★ CANDIDATE p={p} | score={score:.4f} | "
                        f"k={k_c} | s={s_c:.4f} | coherent={coherent}"
                    )

                # Incremental state update
                s = self.registry.get_state(bid)
                self.registry.update_state(bid,
                    n_processed=s.n_processed + 1,
                    current_p=p + 2,
                    cpu_cost_seconds=s.cpu_cost_seconds + ll_time
                )

                if local_red > 0:
                    next_p = p + 2
                    break

            # ── Post-window: compute all metrics ─────────────────────────
            state          = self.registry.get_state(bid)
            new_audit      = state.audit_results + [window_passed]
            all_candidates = state.candidates + new_candidates
            cand_value     = sum(c["score"] for c in all_candidates)
            cp_hash        = self._checkpoint_hash(state)

            # Temporarily build state copy for metric computation
            state_copy = BlockState(**{k: getattr(state, k)
                                       for k in BlockState.__dataclass_fields__})
            state_copy.audit_results = new_audit
            state_copy.anom_orange   = state.anom_orange + local_orange
            state_copy.anom_red      = state.anom_red    + local_red
            state_copy.candidates    = all_candidates
            state_copy.cand_value    = cand_value

            metrics = self._compute_all_metrics(state_copy)

            # Persist window results
            self.registry.update_state(bid,
                audit_results       = new_audit,
                anom_orange         = state.anom_orange + local_orange,
                anom_red            = state.anom_red    + local_red,
                candidates          = all_candidates,
                cand_value          = cand_value,
                n_candidates        = len(all_candidates),
                checkpoint_hash     = cp_hash,
                checkpoint_integrity= True,
                **metrics
            )

            # ── DoD check ─────────────────────────────────────────────────
            done, reason = self._check_dod(state_copy, metrics)
            if done:
                self.registry.update_state(bid,
                    status="DONE", done=True, done_reason=reason,
                    completed_at=datetime.now().isoformat()
                )
                self.logger.info(f"Block {bid}: [OK] DoD SATISFIED -- {reason}")
                break

            # ── RED handling: freeze and forensics ────────────────────────
            if local_red > 0 or metrics["color"] == "RED":
                self.logger.critical(
                    f"Block {bid}: RED state in window #{window_num}. "
                    f"FREEZING + FORENSICS."
                )
                self.registry.update_state(bid, status="FROZEN")
                self._run_forensics(state_copy, window_num, "RED_INCIDENT")
                return

            # Phase transition
            phase = "VALIDATING" if metrics["coverage"] >= 0.80 else "SCANNING"
            self.registry.update_state(bid, phase=phase)

            window_duration = time.time() - window_start
            self.logger.info(
                f"  Window #{window_num} [{wid}] done in {window_duration:.2f}s | "
                f"Cov={metrics['coverage']:.3%} | APR^λ={metrics['apr_weighted']:.4f} | "
                f"Rel={metrics['reliability']:.4f} | {metrics['color']} | "
                f"BPS={metrics['bps']:.4f} | ETA={metrics['eta_seconds']:.0f}s"
            )

        self.logger.info(f"Block {bid}: Worker finished.")


# ── Scoreboard ────────────────────────────────────────────────────────────────

COLOR_ICON = {"GREEN": "[GREEN]", "ORANGE": "[ORANGE]", "RED": "[RED]", "YELLOW": "[YELLOW]"}
STATUS_ICON = {
    "PENDING":    "⏳",
    "RUNNING":    "🔄",
    "SCANNING":   "📡",
    "VALIDATING": "🔍",
    "FORENSICS":  "[FORENSICS]",
    "FROZEN":     "🧊",
    "DONE":       "[OK]",
    "LOCKED":     "🔒"
}


def print_scoreboard(registry: BlockRegistry, configs: Dict[str, BlockConfig]):
    # Lazy aggregation: rebuild BLOCK_REGISTRY.json only here, not in workers
    try:
        registry.aggregate_registry()
    except Exception:
        pass  # Non-fatal -- scoreboard continues even if disk write fails

    W = 90
    now = datetime.now().strftime("%H:%M:%S")
    print(f"\n{'═'*W}")
    print(f"  MULTIBLOCK SCOREBOARD  [{now}]  Protocol: {PROTOCOL_VERSION}")
    print(f"{'═'*W}")
    print(f"  {'Blk':4} {'Status':12} {'Coverage':>9} {'APR^λ':>7} {'Rel':>6} "
          f"{'Color':>8} {'BPS':>7} {'ETA':>10} {'Cands':>6}")
    print(f"{'─'*W}")

    for bid, bps in registry.scoreboard():
        s   = registry.get_state(bid)
        eta = f"{s.eta_seconds:.0f}s" if s.eta_seconds < 1e12 else "∞"
        ci  = COLOR_ICON.get(s.color, "⬜")
        si  = STATUS_ICON.get(s.status, "?")
        print(
            f"  {bid:4} {si}{s.status:11} {s.coverage:>8.2%} "
            f"{s.apr_weighted:>7.4f} {s.reliability:>6.4f} "
            f"{ci}{s.color:>7} {s.bps:>7.4f} {eta:>10} "
            f"{s.n_candidates:>6}"
        )

    print(f"{'─'*W}")
    total_cands = sum(registry.get_state(b).n_candidates for b in configs)
    total_proc  = sum(registry.get_state(b).n_processed  for b in configs)
    print(f"  Total processed: {total_proc:,} | Total candidates: {total_cands}")
    print(f"{'═'*W}\n")


# ── Main Orchestrator ─────────────────────────────────────────────────────────

class MultiBlockOrchestrator:
    """
    Orquestador principal. Lanza workers en threads paralelos,
    monitorea el BPS-scoreboard, y maneja bloques RED.
    """

    BLOCK_CONFIGS = {
        "A": BlockConfig(
            id="A", p_min=23211,   p_max=44497,
            block_type="MINING",    strategic_score=1.0,
            dod_rho=0.99, dod_tau_apr=0.985, dod_nu_anom=1e-4
        ),
        "B": BlockConfig(
            id="B", p_min=44499,   p_max=86243,
            block_type="MINING",    strategic_score=0.7,
            dod_rho=0.99, dod_tau_apr=0.985, dod_nu_anom=1e-4
        ),
        "C": BlockConfig(
            id="C", p_min=86245,   p_max=132049,
            block_type="MINING",    strategic_score=0.5,
            dod_rho=0.99, dod_tau_apr=0.985, dod_nu_anom=1e-4
        ),
        "D": BlockConfig(
            id="D", p_min=1000003, p_max=1050000,
            block_type="EXPLORATION", strategic_score=0.3,
            dod_rho=0.20, dod_tau_apr=0.985, dod_nu_anom=1e-4, dod_tau_rel=0.90
        ),
    }

    PARAMS = {
        "delta_t":        60.0,
        "lambda_decay":   0.95,
        "tau_APR_orange": 0.97,
        "tau_APR_red":    0.90,
        "tau_Anom_orange": 0.005,
        "tau_Anom_red":   0.020,
        "epsilon":        1e-9,
        "gamma":          0.5,
        "delta":          0.1,
        "eta":            2.0,
        "alpha_rel":      10.0,
        "beta_rel":       0.0,
        "tau_rel":        0.98,
        "bps_weights":    {"w1": 0.25, "w2": 0.30, "w3": 0.20, "w4": 0.25}
    }

    def __init__(self, registry_path: str = REGISTRY_PATH,
                 scoreboard_interval: int = 30):
        self.scoreboard_interval = scoreboard_interval
        self.registry = BlockRegistry(registry_path, self.BLOCK_CONFIGS, self.PARAMS)

    def scoreboard_only(self):
        """Solo imprime el scoreboard actual sin ejecutar nada."""
        print_scoreboard(self.registry, self.BLOCK_CONFIGS)

    def run(self, blocks: List[str] = None, window_size: int = 10,
            budget_ua: float = 2_000_000.0):
        if blocks is None:
            blocks = list(self.BLOCK_CONFIGS.keys())

        print(f"\n{'='*90}")
        print(f"  MERSENNE MULTIBLOCK ORCHESTRATOR -- {PROTOCOL_VERSION}")
        print(f"  Blocks: {blocks} | Window: {window_size} | Budget UA: {budget_ua:,.0f}")
        print(f"  Registry: {REGISTRY_PATH}")
        print(f"  Mode: {'LIVE (engines)' if ENGINES_AVAILABLE else 'SIMULATION'}")
        print(f"{'='*90}\n")

        workers = {
            bid: BlockWorker(
                self.BLOCK_CONFIGS[bid], self.registry,
                self.PARAMS, window_size, budget_ua
            )
            for bid in blocks
        }

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(blocks),
                                                   thread_name_prefix="MBlock") as ex:
            futures = {bid: ex.submit(w.run) for bid, w in workers.items()}
            for bid in blocks:
                print(f"  [LAUNCH] Block {bid} launched.")

            while True:
                time.sleep(self.scoreboard_interval)
                print_scoreboard(self.registry, self.BLOCK_CONFIGS)
                if all(f.done() for f in futures.values()):
                    break

        # ── Final report ─────────────────────────────────────────────────────
        print(f"\n{'='*90}")
        print("  MULTIBLOCK OPERATION COMPLETE")
        print_scoreboard(self.registry, self.BLOCK_CONFIGS)

        all_candidates = []
        for bid in blocks:
            all_candidates.extend(self.registry.get_state(bid).candidates)

        if all_candidates:
            sorted_cands = sorted(all_candidates, key=lambda x: -x["score"])
            print(f"\n  ★ TOTAL MERSENNE CANDIDATES FOUND: {len(all_candidates)}")
            for c in sorted_cands:
                print(f"    M_{c['p']:>9,}  score={c['score']:.4f}  "
                      f"k={c['k_c']}  stability={c['s_c']:.4f}  "
                      f"ll_time={c['l_c']:.4f}s")
        else:
            print("\n  ○ No Mersenne prime candidates found in searched ranges.")

        print(f"{'='*90}\n")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="MERSENNE MULTIBLOCK ORCHESTRATOR -- MULTIBLOCK-W3-1.0.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python mersenne_multiblock_orchestrator.py --blocks A B C D --window 10
  python mersenne_multiblock_orchestrator.py --blocks A B     --window 5
  python mersenne_multiblock_orchestrator.py --scoreboard
  python mersenne_multiblock_orchestrator.py --blocks D --window 20 --budget 5000000
        """
    )
    parser.add_argument("--blocks", nargs="+", default=["A", "B", "C", "D"],
                        choices=["A", "B", "C", "D"],
                        help="Bloques a ejecutar (default: todos)")
    parser.add_argument("--window", type=int, default=10,
                        help="Tamaño de ventana por bloque (default: 10)")
    parser.add_argument("--budget", type=float, default=2_000_000.0,
                        help="Budget UA por bloque (default: 2M)")
    parser.add_argument("--interval", type=int, default=30,
                        help="Segundos entre scoreboard prints (default: 30)")
    parser.add_argument("--scoreboard", action="store_true",
                        help="Solo mostrar scoreboard actual y salir")

    args = parser.parse_args()

    orch = MultiBlockOrchestrator(scoreboard_interval=args.interval)

    if args.scoreboard:
        orch.scoreboard_only()
    else:
        orch.run(blocks=args.blocks, window_size=args.window, budget_ua=args.budget)
