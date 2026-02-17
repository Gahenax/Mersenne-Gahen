# MAIN.md — Certificación Determinista de Primos de Mersenne

## 1. Resultado Central (Verdad Certificada)
Se demuestra la capacidad de certificación determinista de números primos de Mersenne ($M_p = 2^p - 1$) mediante el motor Antigravity Recalibrated (Protocolo Jules v3.1). Se han validado con estatus **GREEN** (Lucas-Lehmer residue = 0, Roundoff < 0.40) los exponentes hasta $p=2281$.

## 2. Inventario de Exponentes Certificados
Los siguientes exponentes han sido verificados bajo régimen de integridad dura:
- **Rango Bajo**: $p=127, 521$.
- **Rango Medio**: $p=1279, 2203, 2281$.

## 3. Conclusión de Rigor
La integridad del sistema está garantizada por un gate de error de redondeo inamovible. Todo residuo reportado como cero ha sido sometido a una auditoría de hardware previa (P0-BOOT) para descartar fallos silenciosos en la ALU.
