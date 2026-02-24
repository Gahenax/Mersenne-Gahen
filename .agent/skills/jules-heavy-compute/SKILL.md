---
name: jules-heavy-compute
description: Protocol for delegating high-compute experiments (Mersenne, Riemann, Hodge-PCP) to the Jules distributed lab.
---

# Jules Heavy Compute Skill

Jules acts as the **External Execution Layer (L2-External)** for the Gahenax Kernel. It is designed for tasks that exceed the local machine's UA budget or thermal capacity.

## 🛠️ Core Capabilities
1. **Work Order Generation**: Packaging scripts, parameters, and current checkpoints into a `jules_order_<id>.tar.gz`.
2. **Deep Capture Integration**: High-frequency spectral analysis (Deep Capture 2.0) for Riemann zeros.
3. **Mersenne Warp Delegation**: Distributing Lucas-Lehmer tests for large exponents (>2M).

## 📜 Jules-Kernel Protocol (JXP)
- **Handshake**: Every delegation must start with a `calibration_hint` (local performance metric $\kappa$).
- **Evidence Loopback**: Results from Jules MUST be accompanied by a `node_fingerprint` and a `residue_hash`.
- **Integrity Gate**: Results returning from Jules pass through the same `Semaforo` as local results before being committed to the Ledger.

## 🚀 Key Folders
- `jules_orders/`: Outbound work orders.
- `artifacts/jules_logs/`: Inbound telemetry and debug logs from the remote lab.

## 📊 Operational Status
- **CONNECTED**: Ready to receive work orders.
- **PROCESSING**: Jules is executing a remote task.
- **COMPLETED**: Result pending validation & local ledger commit.

---
*Skill injected via Antigravity Oracle protocol.*
