
# Mersenne Recalibration Pack

Este paquete actualiza la "Granja Antigravity" para el descubrimiento determinista
de números primos de Mersenne.

## Flujo de Trabajo
1. **P0 (Boot)**: Verifica la integridad de la ALU y el plan FFT.
2. **P1 (Search)**: Ejecuta pruebas PRP (Probabilistic) de alto rendimiento.
3. **P2 (Verify)**: Certificación Lucas-Lehmer (Determinista).

## Gobernanza Semáforo
- **RED**: Error de redondeo > 0.40. Abortar misión inmediatamente.
- **YELLOW**: Residuo generado pero no verificado.
- **GREEN**: Residuo verificado mediante doble-check independiente.

---
*Protocolo Mersenne-Gahenax (2026)*
