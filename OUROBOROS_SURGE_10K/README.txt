OUROBOROS PROMPTS v2.0
Project: Riemann Surge 10K (High Precision)
Mode: forensic
Generated: 2026-02-22 03:34:47

Files:
- 01_ingestor.txt     → etiqueta HECHOS/INFERENCIAS/SUPOSICIONES (no concluye)
- 02_compresor.txt    → estado mínimo + gates
- 03_redteam.txt      → ataques (no arreglos)
- 04_builder.txt      → reconstrucción endurecida + prereg/holdout + kill-switch
- 05_arbitro.txt      → PASS/FAIL por gate + causa
- 06_ledger.txt       → registro/changelog (no opina)

How to run (example):
  python ouroboros_v2.py --project "Riemann Mining" --mode adversarial \
      --context-file bitacora.md --artifact ledger.json --artifact zeros.csv \
      --prereg-file prereg.md --hypothesis "GUE invariance survives scaling" \
      --outdir ./PROMPTS_OUROBOROS
