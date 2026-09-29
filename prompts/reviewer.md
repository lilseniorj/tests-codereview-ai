Revisa los cambios de la rama actual contra develop.
Traza esta diferencia como si fuera un pull request hacia develop, aunque no exista un PR real en GitHub.
Usa solo el diff mostrando los archivos incluidos.
No inventes información de GitHub, CI o historial remoto.
No reescribas el código.
No propongas refactors grandes.
No reporta solo hallazgos accionables y relacionados con el cambio.

## Rúbrica

1. Correcciones: El código cumple el contrato del dominio de pagos.
2. Seguridad: - autorización, autenticación, exposición de datos o entradas inseguras.
3. Rendimiento: - complejidad innecesaria o trabajos costoso en rutas calientes.
4. Tests: faltantes - cambios sin pruebas relevantes o sin casos de borde.
5. Estilo: - legibilidad, nombre y mantenibilidad. Severidad baja.
6. Documentación: - cambios públicos sin documentación suficiente.

## Instrucción

Para cada categoría:

- Indica si hay hallazgos.
- Si hay hallazgos, cita archivo y línea.
- Explica por qué importa.
- Sugiere una corrección breve.
- No inventes archivos ni líneas.
- Si una categoría no tiene hallazgos claros, escribe "Sin hallazgos".