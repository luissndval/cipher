# IMPACT_RULES.md — [NOMBRE_DEL_SERVICIO]
> Reglas para evaluar el impacto de un cambio antes de implementarlo.
> Última actualización: [FECHA]

---

## Reglas de evaluación de impacto

### IR-001 — Identificar el componente afectado
Antes de cualquier cambio, identificar a cuál componente de la `RISK_MATRIX.md` pertenece el área a modificar.
Si el componente no está en la matriz, clasificar como **ALTO** hasta determinar su nivel real.

### IR-002 — Evaluar propagación hacia dependencias de salida
Revisar `DEPENDENCIES.md` → sección "Dependencias de salida".
Preguntar: ¿El cambio modifica el contrato, los campos críticos, o el SLA de alguna dependencia de salida?
Si la respuesta es **sí** para cualquiera de los tres, incrementar el nivel de riesgo en un grado.

### IR-003 — Evaluar impacto en consumidores de entrada
Revisar `DEPENDENCIES.md` → sección "Dependencias de entrada".
Preguntar: ¿El cambio modifica la interfaz que expone este servicio (endpoints, schemas, eventos emitidos)?
Si modifica la interfaz, todos los consumidores de entrada deben ser notificados y probados.

### IR-004 — Verificar invariantes de negocio
Revisar `BUSINESS_RULES.md` → sección "Invariantes del sistema".
El cambio propuesto debe mantener todos los invariantes. Si viola alguno, el cambio no puede implementarse tal como está.

### IR-005 — Evaluar reversibilidad
Clasificar el cambio en una de estas categorías:
- **Reversible en segundos:** cambio de configuración, feature flag
- **Reversible en minutos:** revertir deploy
- **Reversible con esfuerzo:** migración de datos con script de rollback
- **Irreversible:** eliminación de datos, cambios de schema sin backward compatibility

Para cambios **irreversibles**, el nivel de riesgo mínimo es **ALTO**, independientemente del componente.

### IR-006 — Detectar cambios en cadena
Si el cambio requiere modificar más de 3 archivos, o si toca más de 1 componente de la RISK_MATRIX,
evaluar si existe efecto cascada. Documentar la cadena completa en la propuesta antes de implementar.

---

## Checklist de 5 preguntas (obligatorio antes de implementar)

Responder estas 5 preguntas en la propuesta de cambio:

1. **¿Qué componente de la RISK_MATRIX está afectado?** — [Respuesta]
2. **¿El cambio modifica alguna interfaz externa (API, eventos, schema)?** — [Sí/No + detalle]
3. **¿Alguna BUSINESS_RULE o invariante podría ser violada?** — [Sí/No + detalle]
4. **¿Cómo se revierte si algo falla?** — [Procedimiento concreto]
5. **¿Qué prueba confirmaría que el cambio funciona correctamente?** — [Prueba específica]

---

## Áreas de revisión por tipo de cambio

| Tipo de cambio | Archivos a revisar siempre | Riesgo mínimo |
|----------------|---------------------------|---------------|
| Cambio en lógica de negocio | BUSINESS_RULES.md, RISK_MATRIX.md | MEDIO |
| Cambio en API/endpoints | DEPENDENCIES.md (entrada), RISK_MATRIX.md | ALTO |
| Cambio en eventos emitidos | DEPENDENCIES.md (eventos), consumidores | ALTO |
| Cambio en schema de DB | DEPENDENCIES.md, RISK_MATRIX.md | ALTO |
| Cambio en configuración | RISK_MATRIX.md | MEDIO |
| Cambio en autenticación/autorización | BUSINESS_RULES.md, RISK_MATRIX.md | CRÍTICO |
| Refactoring sin cambio de comportamiento | TEST_STRATEGY.md (verificar cobertura) | BAJO |
| Actualización de dependencias externas | DEPENDENCIES.md, TEST_STRATEGY.md | MEDIO-ALTO |
