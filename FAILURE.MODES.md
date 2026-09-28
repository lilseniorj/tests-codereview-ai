#  FAILURE-MODES.md - Catalogo de fallos de IA en payments-svc

## Categoría: Generacion de tests
- [n1] Para Amount == 0 en calculate_free/total_with_fee, la IA documento el comportamiento actual del codigo (sin fee) como si fuera el contrato de negocio, sin cuestionar si deberia aplicar el fee minimo en cualquiera otro monto.