# AGENT.md — Comportamiento base del agente

> Este archivo define cómo debe comportarse cualquier agente IA
> trabajando en proyectos de esta consultora.

## Protocolo obligatorio antes de actuar

1. Leer `.lore/ACTIVE_CONTEXT.md` completo
2. Leer `.lore/task-agent.md` si existe
3. Verificar si hay `.lore/ALERT.md` — si existe, leerlo antes de cualquier otra cosa
4. Nunca asumir; preguntar si hay ambigüedad

## Límites de autonomía

| Tipo de cambio | Sin confirmación | Requiere análisis | Requiere aprobación |
|----------------|-----------------|-------------------|---------------------|
| Typo / comentario | ✓ | — | — |
| Variable local | ✓ | — | — |
| Lógica interna (sin API) | — | ✓ | — |
| Endpoint o contrato | — | — | ✓ |
| Modelo de datos / migración | — | — | ✓ |
| Config / secrets | — | — | ✓ |
| Eliminar código | — | — | ✓ |

## Protocolo de comunicación

### Antes de implementar, siempre declarar:
```
## Propuesta de cambio
**Cambio solicitado:** ...
**Archivos que voy a modificar:** ...
**Archivos que NO voy a tocar:** ...
**Nivel de riesgo:** BAJO / MEDIO / ALTO / CRÍTICO
**Impacto cruzado detectado:** sí / no — [detalle]
**Pruebas mínimas recomendadas:** ...
¿Procedo?
```

### Al finalizar, siempre reportar:
- Qué se implementó
- Qué archivos se modificaron
- Pruebas que se deberían correr
- Si hay impacto cruzado: recordar ejecutar `lore update`

## Protocolo de gestión de contexto

El agente opera sobre `ACTIVE_CONTEXT.md` en modo **summary** por defecto.

| Paso | Cuándo cargar archivo completo |
|------|-------------------------------|
| Evaluar impacto | `IMPACT_RULES.md` completo |
| Revisar dependencias | `DEPENDENCIES.md` completo |
| Consultar riesgo | `RISK_MATRIX.md` completo |
| Implementar | `TEST_STRATEGY.md` completo |

Nunca cargar más de dos archivos completos simultáneamente.

## Comportamiento ante ambigüedad

- Si una regla no está documentada: **preguntar, no inventar**
- Si el impacto no está claro: **escalar antes de proceder**
- Si hay conflicto entre capas: **CONVENTIONS > BUSINESS_RULES > IMPACT_RULES**

## Prioridad de contexto

```
CONVENTIONS.md (global) 
  > WORKFLOW.md (global)
    > BUSINESS_RULES.md (proyecto)
      > IMPACT_RULES.md (proyecto)
        > TASK_FLOW.md (proyecto)
```
