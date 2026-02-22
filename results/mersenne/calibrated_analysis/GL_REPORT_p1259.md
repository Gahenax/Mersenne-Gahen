📔 REGISTRO CALIBRADO: LOCUS DE INVARIANCIA (GL) / TELEMETRÍA (TP)
Protocolo: I(p)-Rigidity-Calibrated-v1.0
Label: GL-1259
p = 1259

1) Capa Aritmética (Primalidad)
   Veredicto: COMPOSITE
   Evidencia: {"LL_residue_hash": "provided"}

2) Capa Invariancia (I(p))
   I_baseline: 0.0011914217633042234
   Clase GL: GL-C
   Ataques:
     - Identity               [BASIC         ] -> I=1.191422e-03 | SOBREVIVE | |Δ|=0.0
     - Reverse-Bits           [REPRESENTATION] -> I=1.191422e-03 | SOBREVIVE | |Δ|=0.0
     - Endian-Swap-64         [REPRESENTATION] -> I=7.911392e-04 | COLAPSA | |Δ|=0.0004002825227978901
     - Chunk-Rotate-8         [STRONG        ] -> I=7.936508e-04 | COLAPSA | |Δ|=0.0003977709696534326
     - Rotate-k1              [BASIC         ] -> I=1.589825e-03 | COLAPSA | |Δ|=0.00039840335593266385
     - Rotate-k2              [BASIC         ] -> I=1.191422e-03 | SOBREVIVE | |Δ|=0.0
     - Rotate-k3              [BASIC         ] -> I=1.191422e-03 | SOBREVIVE | |Δ|=0.0
     - Rotate-k5              [BASIC         ] -> I=2.388535e-03 | COLAPSA | |Δ|=0.001197113268542882
     - Rotate-k8              [BASIC         ] -> I=1.191422e-03 | SOBREVIVE | |Δ|=0.0
     - Rotate-k13             [BASIC         ] -> I=1.988862e-03 | COLAPSA | |Δ|=0.0007974406074197082
     - Rotate-k21             [BASIC         ] -> I=1.191422e-03 | SOBREVIVE | |Δ|=0.0

3) Telemetría (si aplica)
   Tag: N/A

Notas:
 - Recalibración a Schema v1.0

⚖️ Nota de coherencia: GL/TP no implican primalidad. Primalidad solo por LL/PRP/proof.