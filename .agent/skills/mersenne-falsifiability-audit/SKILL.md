---
# ==========================================
# HEADER OPERATIVO (Leído por el CIE Router)
# ==========================================
sigil_id: mersenne-falsifiability-audit
version: 2.1.0
type: computation-delegation

triggers:
  - keywords: ["mersenne", "falsifiability", "ghost locus", "stress-test", "rigidity", "preregistration"]
  - entities: ["M-prime", "ghost_hunter_lab.py"]
  - explicit_tag: "@sigil:mersenne-audit"

context_injection:
  - file: "protocols/MERSENNE_RIGOR.md"
  - local_tools_required: 
      - "tools/ghost_hunter_lab.py"
      - "tools/mersenne_ghost_adapter.py"
  - variables: ["GIMPS_SYNC_STATE", "H_THRESHOLD_DEFAULT"]

constraints:
  - no_hallucinate_math: "DO NOT calculate primality or ghost rigidity native to the LLM. You MUST delegate to ghost_hunter_lab.py."
  - preregistration_lock: "Execution MUST abort if no valid prereg.json is found in the working directory."

delegates_to: 
  - system: "Local Python Environment"
    target: "ghost_hunter_lab.py"

output_schema:
  type: "audit_report_markdown"
  expected_path: "results/mersenne/falsifiability/audit_{timestamp}.md"
  required_fields: 
    - "Hypothesis ID (from parsed prereg.json)"
    - "Test 1: Rotation Status (Pass/Fail/Collapse)"
    - "Test 2: Swap Status (Pass/Fail/Collapse)"
    - "Test 3: Permutation Status (Pass/Fail/Collapse)"
    - "Raw Delegation Output Dump (json from script stdout)"
    - "Timestamp of execution"
    - "PreReg hash for traceability"
---

# ==========================================
# INSTRUCCIONES DE EJECUCIÓN (Leído por el LLM tras el routing)
# ==========================================

Estás operando bajo el sigilo `mersenne-falsifiability-audit`. Tu tarea NO es resolver matemáticas del milenio, sino **orquestar la validación de un candidato numérico** usando scripts locales.

## Flujo de Ejecución Obligatorio:
1. **Validar Input (Preregistration):** Busca el archivo `prereg.json` en el directorio actual. Si no existe o le faltan métricas de éxito predefinidas, DETENTE y pídelo al usuario.
2. **Delegación Computacional:** Construye el comando de terminal para llamar a `tools/ghost_hunter_lab.py` pasando el candidato numérico. Las operaciones pesadas (rotaciones, métrica H) ocurren en el procesador local, NO en tu red neuronal.
3. **Observación y Parsers:** Lee el `stdout` del script de Python. Compara los resultados contra el baseline documentado en `prereg.json`. Si el exit code es distinto de 0, reporta fallo de infraestructura y NO adivines los valores matemáticos.
4. **Formateo del Output (Schema):** Genera el archivo en ruta `results/mersenne/falsifiability/` cumpliendo estrictamente con el `output_schema` definido por CIE. Usa un alert block de GitHub `> [!WARNING]` si alguna de las 3 pruebas vectoriales causó colapso en la rigidez estructural. No opines sobre el resultado; reporta los deltas matemáticos del script.
