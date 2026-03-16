# TASK_FLOW — notification-worker
> Este flujo es OBLIGATORIO. El agente no puede saltar pasos.

## Pasos obligatorios (en orden estricto)

### Paso 1 — Leer contexto activo
**Acción:** Leer `ACTIVE_CONTEXT.md` completo.
**Criterio de éxito:** Puedo responder: ¿qué canales maneja el worker? ¿cuáles son sus proveedores externos? ¿cuáles son las reglas de reintento y suscripción?

### Paso 2 — Describir el cambio solicitado
**Acción:** Parafrasear con palabras propias qué cambio se pide y cuál es el objetivo funcional. Identificar si el cambio afecta la entrega de mensajes, los schemas de eventos, o la lógica de suscripción.
**Criterio de éxito:** El usuario confirma que la interpretación es correcta.

### Paso 3 — Identificar archivos y módulos afectados
**Acción:** Listar exactamente qué archivos serán modificados. Para notification-worker, prestar atención especial a: consumer, dispatcher, providers (sendgrid/twilio/firebase), UnsubscribeGuard, retry logic, event emitters.
**Criterio de éxito:** Lista completa con justificación por archivo.

### Paso 4 — Evaluar impacto con IMPACT_RULES.md
**Acción:** Aplicar cada regla IR-001 a IR-010 al cambio propuesto. En particular, verificar IR-004 si el cambio toca `UnsubscribeGuard`.
**Criterio de éxito:** Cada regla evaluada y documentado el resultado (aplica / no aplica / requiere acción).

### Paso 5 — Revisar DEPENDENCIES.md si hay interfaces afectadas
**Acción:** Si el cambio toca Kafka (entrada/salida), un proveedor externo, o `user-preferences-service`, identificar todos los consumidores y productores impactados. Verificar advertencias WARN-001 a WARN-005.
**Criterio de éxito:** Lista explícita de dependencias potencialmente impactadas.

### Paso 6 — Consultar RISK_MATRIX.md
**Acción:** Identificar el nivel de riesgo del componente a modificar. Si es CRÍTICO, confirmar qué equipos deben ser notificados antes de deployar.
**Criterio de éxito:** Nivel de riesgo declarado, acciones de mitigación definidas, equipos a notificar identificados.

### Paso 7 — Proponer el cambio con análisis incluido
**Acción:** Presentar la propuesta usando el formato definido en `AGENT.md`.
**Criterio de éxito:** Propuesta aprobada por el usuario antes de ejecutar.

### Paso 8 — Implementar y documentar
**Acción:** Aplicar cambios aprobados. Listar pruebas mínimas al finalizar según `TEST_STRATEGY.md`. Si el cambio afecta un schema Kafka, documentar la versión y la estrategia de migración.
**Criterio de éxito:** Cambios aplicados, pruebas listadas, schemas actualizados si aplica.

## Casos especiales

- **Si el cambio es trivial (typo, comentario, variable local sin impacto en lógica):** Pasos 1, 2, 3 y 8 son suficientes.
- **Si el cambio es urgente/hotfix en producción:** No se pueden saltar los pasos 4, 5 y 6. Solo se puede omitir la espera de confirmación si el usuario lo indica explícitamente. Documentar la decisión.
- **Si el cambio afecta `UnsubscribeGuard`:** Siempre requerir aprobación explícita del usuario + revisión de compliance, incluso en hotfix.
- **Si el cambio agrega un nuevo proveedor externo:** Crear una entrada en DEPENDENCIES.md antes de implementar. Definir timeout, retry y manejo de error para el nuevo proveedor.
- **Si cambia un schema Avro:** No merge sin versión registrada en Avro registry y plan de compatibilidad (backward/forward/full).
