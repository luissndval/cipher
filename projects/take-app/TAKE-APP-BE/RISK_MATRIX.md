# RISK_MATRIX.md — [NOMBRE_DEL_SERVICIO]
> Última actualización: [FECHA]
> Ver `schemas/risk-schema.md` para criterios de asignación de nivel.

---

## Niveles de riesgo

| Nivel | Criterio | Acción requerida |
|-------|----------|------------------|
| **CRÍTICO** | Afecta datos de usuario, autenticación, pagos, compliance, o puede provocar pérdida de datos irreversible | Aprobación explícita + plan de rollback + notificación al equipo |
| **ALTO** | Afecta flujos de negocio principales, puede causar degradación visible del servicio, o tiene dependencias externas impactadas | Análisis de impacto + aprobación + pruebas de integración |
| **MEDIO** | Cambios internos con impacto limitado, afecta features secundarios, o tiene efecto sólo en casos de uso edge | Revisión de impacto + pruebas unitarias |
| **BAJO** | Cambios de presentación, logs, documentación, o refactoring sin cambio de comportamiento observable | Verificación de que no rompe pruebas existentes |

---

## Componentes del servicio y su nivel de riesgo

| Componente | Nivel | Justificación | Revisar antes de cambiar |
|------------|-------|---------------|--------------------------|
| [Componente 1] | CRÍTICO | [Por qué es crítico] | [Qué revisar: archivos, tests, dependencias] |
| [Componente 2] | ALTO | [Por qué es alto] | [Qué revisar] |
| [Componente 3] | MEDIO | [Por qué es medio] | [Qué revisar] |
| [Componente 4] | BAJO | [Por qué es bajo] | [Qué revisar] |
| [Componente 5] | MEDIO | [Por qué es medio] | [Qué revisar] |

---

## Reglas de escalamiento

### Cuándo escalar inmediatamente al equipo

- Cualquier cambio clasificado como **CRÍTICO** debe ser comunicado al equipo antes de implementar, incluso si el usuario ya aprobó.
- Si un cambio afecta a más de **[N] componentes** simultáneamente, escalar independientemente del nivel individual de cada uno.
- Si hay incertidumbre sobre el nivel de riesgo y no se puede determinar en menos de 15 minutos de análisis, asumir **ALTO** y escalar.

### Procedimiento de rollback por nivel

| Nivel | Procedimiento de rollback |
|-------|---------------------------|
| CRÍTICO | [Pasos específicos de rollback para este servicio] |
| ALTO | [Pasos de rollback] |
| MEDIO | Revertir commit + re-deploy |
| BAJO | Revertir commit |

---

## Historial de incidentes relacionados

> Documentar incidentes pasados ayuda a identificar patrones de riesgo no obvios.

| Fecha | Componente afectado | Causa raíz | Lección aprendida |
|-------|---------------------|------------|-------------------|
| [YYYY-MM-DD] | [Componente] | [Causa] | [Qué no volver a hacer] |
| [YYYY-MM-DD] | [Componente] | [Causa] | [Lección] |
