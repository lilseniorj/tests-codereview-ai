# FAILURE-MODES.md - Modos de falla de `amounts.py`

Catálogo de modos de falla de [`src/payments_svc/amounts.py`](src/payments_svc/amounts.py), agrupados por frontera, equivalencia, null/vacío y contrato de negocio.

El comportamiento actual se verificó ejecutando el código, y también se revisó cómo lo usan `api.py`, `refunds.py` y `scripts/smoke_test.py`. La implementación actual **no** se toma como especificación. Un contrato se marca como **confirmado** solo cuando se deduce del propio código: docstrings de las excepciones, el `except` de la API o el nombre de la función. El resto queda **pendiente de decisión**.

## Frontera

### F-01
- **Categoria:** Frontera
- **Riesgo:** Alto
- **Entrada que lo desestima:** `Decimal("0.001")`, `Decimal("1E-30")`, `Decimal("10.001")`
- **Comportamiento actual observado en el código:** Se aceptan montos con menos de un centavo. `calculate_fee(0.001, "USD")` devuelve `0.30`, y `parse_amount` no limita la cantidad de decimales.
- **Contrato esperado recomendado:** Rechazar montos con más de 2 decimales (o más de los que admita la moneda) con `AmountError`, en vez de redondearlos en silencio.
- **Estado del contrato:** pendiente de decisión
- **Por que importa para pagos:** Un monto que no se puede liquidar genera una comisión real, y el importe guardado no coincide con lo que se cobra (ver B-03).

### F-02
- **Categoria:** Frontera
- **Riesgo:** Medio
- **Entrada que lo desestima:** `Decimal("0")`, `Decimal("0.00")`, `Decimal("-0")`
- **Comportamiento actual observado en el código:** Un pago de 0 es válido y su comisión es `0.00`: no se aplica la comisión mínima. `-0` también pasa, porque `-0 < 0` es falso. El smoke test lo marca como "sentinel", y `refunds.py` sí rechaza el reembolso de 0 ("must be greater than zero").
- **Contrato esperado recomendado:** Probablemente rechazar pagos de 0 para ser coherente con los reembolsos. Si se aceptan, hay que decidir si la comisión mínima aplica también en ese caso.
- **Estado del contrato:** pendiente de decisión
- **Por que importa para pagos:** Un pago de 0 crea transacciones vacías (sirven para probar tarjetas o ensucian la conciliación), y el dominio queda incoherente entre pagos y reembolsos.

### F-03
- **Categoria:** Frontera
- **Riesgo:** Medio
- **Entrada que lo desestima:** `Decimal("100000.00")` frente a `Decimal("100000.01")`, y `total_with_fee(Decimal("100000"), "USD")`
- **Comportamiento actual observado en el código:** El límite es inclusivo y se aplica al monto, no al total. Un monto de 100000.00 da un total de `102900.00`, por encima de `MAX_AMOUNT`.
- **Contrato esperado recomendado:** Definir si el máximo es inclusivo y si limita el monto neto o el total cobrado.
- **Estado del contrato:** pendiente de decisión
- **Por que importa para pagos:** Los límites suelen venir del procesador o de la regulación. Si se aplican al valor equivocado, se aprueban cobros que después serán rechazados.

### F-04
- **Categoria:** Frontera
- **Riesgo:** Medio
- **Entrada que lo desestima:** `calculate_fee(Decimal("1000.20"), "EUR")`, cuya comisión sin redondear es 25.005
- **Comportamiento actual observado en el código:** Usa `ROUND_HALF_EVEN` y da `25.00`. Con `ROUND_HALF_UP` daría `25.01`.
- **Contrato esperado recomendado:** El modo de redondeo debe salir del contrato con el procesador o de la normativa, no del valor por defecto elegido en el código.
- **Estado del contrato:** pendiente de decisión
- **Por que importa para pagos:** Una diferencia de un centavo en muchas transacciones produce descuadres sistemáticos en la conciliación.

## Equivalencia

### E-01
- **Categoria:** Equivalencia
- **Riesgo:** Medio
- **Entrada que lo desestima:** `"1_000"`, `"١٢"`, `"１２"`, `"1e3"`, `" 12 "`
- **Comportamiento actual observado en el código:** Todas se aceptan: guiones bajos, dígitos no ASCII, notación científica y espacios Unicode. `"1e3"` se guarda como `1E+3`, y `api.py` lo devuelve tal cual en la respuesta (`amount="1E+3"`).
- **Contrato esperado recomendado:** Aceptar solo un formato estricto, por ejemplo `^\d+(\.\d{1,2})?$`.
- **Estado del contrato:** pendiente de decisión
- **Por que importa para pagos:** Si el parser es permisivo, un mismo importe puede tener varias representaciones. Eso complica la idempotencia, la auditoría y la comparación con otros sistemas.

### E-02
- **Categoria:** Equivalencia
- **Riesgo:** Medio
- **Entrada que lo desestima:** `parse_amount(0.1 + 0.2)`
- **Comportamiento actual observado en el código:** Devuelve `Decimal("0.30000000000000004")`. La firma acepta `float` de forma explícita.
- **Contrato esperado recomendado:** No aceptar `float` en la frontera monetaria, o cuantizarlo antes y documentarlo.
- **Estado del contrato:** pendiente de decisión
- **Por que importa para pagos:** El error binario del float se cuela en montos que parecen exactos y termina cayendo en F-01.

### E-03
- **Categoria:** Equivalencia
- **Riesgo:** Alto
- **Entrada que lo desestima:** `validate_amount(Decimal("NaN"))`, que ocurre en la práctica al enviar `POST /refunds` con `original_amount="NaN"`
- **Comportamiento actual observado en el código:** Lanza `decimal.InvalidOperation` y no `AmountError`. `api.py` crea los `Decimal` de reembolso sin pasar por `parse_amount` y solo captura `AmountError`, así que la petición termina en un error 500.
- **Contrato esperado recomendado:** `validate_amount` debe rechazar los valores no finitos con `AmountError`.
- **Estado del contrato:** confirmado (el docstring de `AmountError` dice que se lanza cuando un monto no se puede usar)
- **Por que importa para pagos:** Una entrada inválida provoca un error 500 en vez de un 4xx, y `validate_amount` no protege por sí sola a quien la llama.

### E-04
- **Categoria:** Equivalencia
- **Riesgo:** Bajo
- **Entrada que lo desestima:** `normalize_currency(123)`, `calculate_fee(1.5, "USD")`
- **Comportamiento actual observado en el código:** Lanzan `AttributeError` y `TypeError`. Además, `validate_amount(1.5)` pasa sin error, pero `calculate_fee(1.5, ...)` falla.
- **Contrato esperado recomendado:** Un tipo inválido debe producir `CurrencyError` o `AmountError`.
- **Estado del contrato:** confirmado para la moneda (según el docstring de `CurrencyError`, "missing or unsupported"). Pendiente para el monto `float` (depende de E-02).
- **Por que importa para pagos:** Las excepciones que no son de dominio se escapan de los `except` de la API y generan errores 500.

### E-05
- **Categoria:** Equivalencia
- **Riesgo:** Bajo
- **Entrada que lo desestima:** `"usd"`, `" eur "`, `"usd\n"`
- **Comportamiento actual observado en el código:** Se normalizan a código ISO en mayúsculas y se aceptan.
- **Contrato esperado recomendado:** Probablemente es intencional. Falta decidir si la API debe exigir el formato canónico.
- **Estado del contrato:** pendiente de decisión
- **Por que importa para pagos:** El impacto es bajo, pero la API repite la moneda normalizando por su cuenta (`api.py:61`), y esa lógica duplicada puede divergir.

## Null / vacío

### N-01
- **Categoria:** Null/vacío
- **Riesgo:** Medio
- **Entrada que lo desestima:** `validate_amount(None)`
- **Comportamiento actual observado en el código:** Lanza `TypeError`. `parse_amount(None)` y `normalize_currency(None)` sí lanzan su error de dominio.
- **Contrato esperado recomendado:** `AmountError("amount is required")`, igual que en `parse_amount`.
- **Estado del contrato:** confirmado
- **Por que importa para pagos:** `refunds.py` llama a `validate_amount` directamente, así que un `None` que venga de otro módulo se convierte en un error 500.

### N-02
- **Categoria:** Null/vacío
- **Riesgo:** Bajo
- **Entrada que lo desestima:** `parse_amount("")`, `parse_amount("   ")`
- **Comportamiento actual observado en el código:** Devuelve "amount must be numeric". En cambio, una moneda vacía devuelve "currency is required".
- **Contrato esperado recomendado:** Tratar la cadena vacía como ausente ("amount is required"), igual que la moneda.
- **Estado del contrato:** pendiente de decisión
- **Por que importa para pagos:** No es un error de cálculo. Es un mensaje incoherente para quien integra la API.

## Contrato de negocio

### B-01
- **Categoria:** Contrato de negocio
- **Riesgo:** Alto
- **Entrada que lo desestima:** `calculate_fee(Decimal("0.01"), "USD")` da `0.30`, y `calculate_fee(Decimal("1"), "COP")` da `900.00`
- **Comportamiento actual observado en el código:** La comisión mínima se aplica sin un monto mínimo de pago, así que la comisión puede ser mucho mayor que el monto.
- **Contrato esperado recomendado:** Definir un monto mínimo por moneda o un tope relativo para la comisión.
- **Estado del contrato:** pendiente de decisión
- **Por que importa para pagos:** Se cobran comisiones abusivas sobre micropagos. Eso trae reclamos y riesgo regulatorio.

### B-02
- **Categoria:** Contrato de negocio
- **Riesgo:** Alto
- **Entrada que lo desestima:** `calculate_fee(Decimal("100000"), "USD")` frente a `calculate_fee(Decimal("100000"), "COP")`
- **Comportamiento actual observado en el código:** `MAX_AMOUNT` vale 100000 para todas las monedas: son unos 25 USD en COP y 100 000 USD en USD.
- **Contrato esperado recomendado:** Un máximo por moneda, como ya existe `MINIMUM_FEES`.
- **Estado del contrato:** pendiente de decisión
- **Por que importa para pagos:** En COP se bloquean pagos legítimos, y en USD el límite quizá no protege nada.

### B-03
- **Categoria:** Contrato de negocio
- **Riesgo:** Alto
- **Entrada que lo desestima:** `Decimal("19.999")` en USD
- **Comportamiento actual observado en el código:** La comisión es `0.58` y el total es `20.58`, mientras que monto más comisión da `20.579`. La API devuelve los tres valores, y no cuadran.
- **Contrato esperado recomendado:** Que siempre se cumpla `total == amount + fee`. Resolver F-01 lo garantiza.
- **Estado del contrato:** confirmado como invariante (lo dicen el nombre `total_with_fee` y la respuesta de la API). Cómo lograrlo depende de F-01.
- **Por que importa para pagos:** Se cobra un importe que no coincide con el desglose mostrado al cliente, y eso rompe la conciliación.

### B-04
- **Categoria:** Contrato de negocio
- **Riesgo:** Medio
- **Entrada que lo desestima:** `calculate_fee(Decimal("50000.50"), "COP")`
- **Comportamiento actual observado en el código:** Todas las monedas se cuantizan a centavos (`CENT`), también COP.
- **Contrato esperado recomendado:** Usar la precisión de cada moneda según lo que admita el procesador. En la práctica, COP suele operar sin decimales.
- **Estado del contrato:** pendiente de decisión
- **Por que importa para pagos:** Se envían al procesador montos que quizá rechace o redondee de otra forma.

## Por dónde empezar

- **Corregir ya:** E-03, N-01 y E-04. Su contrato está confirmado y hoy producen errores 500.
- **Decidir antes que el resto:** F-01, B-01 y B-02. De F-01 dependen B-03 y E-02.
- **Pueden esperar:** E-05 y N-02, que no afectan al dinero.
