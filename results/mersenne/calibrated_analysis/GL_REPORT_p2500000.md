📔 REGISTRO CALIBRADO: LOCUS DE INVARIANCIA (GL) / TELEMETRÍA (TP)
Protocolo: I(p)-Rigidity-Calibrated-v1.0
Label: GL-2500000 (Frontera de Resistencia)
p = 2500000

1) Capa Aritmética (Primalidad)
   Veredicto: COMPOSITE
   Evidencia: {"Source": "Stochastic-Probe-2.5M", "Anomaly": "Phase-Resonance-13-detected"}

2) Capa Invariancia (I(p))
   I_baseline: 0.0035409035409035283
   Clase GL: GL-C
   Ataques:
     - Endian-Swap-64         [REPRESENTATION] -> I=2.869003e-03 | COLAPSA | |Δ|=0.0006719009771140039
     - Reverse-Bits           [REPRESENTATION] -> I=3.540904e-03 | SOBREVIVE | |Δ|=0.0
     - Rotate-k1              [BASIC         ] -> I=3.540904e-03 | SOBREVIVE | |Δ|=0.0
     - Rotate-k8              [BASIC         ] -> I=3.418803e-03 | COLAPSA | |Δ|=0.00012210012210012167
     - Rotate-k13             [BASIC         ] -> I=3.358163e-03 | COLAPSA | |Δ|=0.00018274015099023488
     - Rotate-k16             [BASIC         ] -> I=3.480278e-03 | COLAPSA | |Δ|=6.0625118629753505e-05
     - Rotate-k32             [BASIC         ] -> I=3.540904e-03 | SOBREVIVE | |Δ|=0.0

3) Telemetría (si aplica)
   Tag: N/A

Notas:
 - Anomalía detectada durante el barrido estratégico a los 100M.
 - Presenta una firma de periodicidad inyectada/detectada en el rango 2.5M.
 - Auditando resistencia a Endian-Swap (Criterio de Profundidad).

⚖️ Nota de coherencia: GL/TP no implican primalidad. Primalidad solo por LL/PRP/proof.