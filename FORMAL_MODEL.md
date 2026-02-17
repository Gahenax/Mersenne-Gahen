# FORMAL_MODEL.md — Modelo Axiomático de Verdad Determinista

## 1. Definiciones de Estado

Sea $M_p = 2^p - 1$ un candidato de Mersenne. Definimos el **Indicador de Primacidad Determinista** $\Psi(p)$ y el **Indicador de Integridad del Instrumento** $\Omega(p)$ como:

$$\Psi(p) := \mathbb{1}\{S_{p-2} \equiv 0 \pmod{M_p}\}$$
$$\Omega(p) := \mathbb{1}\{\text{Roundoff}(p) \leq 0.40\}$$

Donde $S_n$ es la secuencia de Lucas-Lehmer: $S_0 = 4, S_n = S_{n-1}^2 - 2$.

## 2. Axioma de Certificación (Status GREEN)

Un exponente $p$ es movido al estado **GREEN** si y solo si:
$$\Psi(p) = 1 \land \Omega(p) = 1$$

## 3. Teorema de la Alucinación Evitada (Status RED)

Si el instrumento detecta $\Omega(p) = 0$, el veredicto de primacidad $\Psi(p)$ queda invalidado instantáneamente:
$$\Omega(p) = 0 \implies \text{Status} := \text{RED}$$

Este modelo garantiza que ningún primo "descubierto" bajo condiciones de inestabilidad de hardware sea aceptado como verdad en el Ledger.
