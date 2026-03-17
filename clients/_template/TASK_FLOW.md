# TASK_FLOW — [NOMBRE_DEL_SERVICIO]
> Este flujo es OBLIGATORIO. El agente no puede saltar pasos.

## Pasos obligatorios

### Paso 1 — Leer contexto
Leer `.lore/ACTIVE_CONTEXT.md` y `.lore/task-agent.md` completos.
Verificar si existe `.lore/ALERT.md`.

### Paso 2 — Describir el cambio
Parafrasear con palabras propias qué cambio se pide y cuál es el objetivo.
El usuario debe confirmar que la interpretación es correcta.

### Paso 3 — Identificar archivos afectados
Listar exactamente qué archivos serán modificados y por qué.

### Paso 4 — Evaluar impacto (IMPACT_RULES.md)
Aplicar cada regla IR-00X al cambio propuesto.

### Paso 5 — Revisar dependencias si hay interfaces afectadas
Identificar todos los consumidores potencialmente impactados.

### Paso 6 — Consultar nivel de riesgo (RISK_MATRIX.md)
Declarar nivel de riesgo y acciones de mitigación.

### Paso 7 — Proponer el cambio
Presentar propuesta usando el formato definido en AGENT.md.
Esperar aprobación antes de ejecutar.

### Paso 8 — Implementar y documentar
Aplicar cambios aprobados.
Listar pruebas mínimas al finalizar.
Recordar ejecutar `lore update` si el cambio es significativo.

## Casos especiales
- **Cambio trivial (typo, comentario):** Pasos 1, 2, 3 y 8 son suficientes.
- **Hotfix urgente:** No se pueden saltar pasos 4, 5 y 6.
