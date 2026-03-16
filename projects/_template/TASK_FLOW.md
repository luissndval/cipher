# TASK_FLOW.md — [NOMBRE_DEL_SERVICIO]
> Flujo de trabajo obligatorio para cualquier tarea de modificación de código.
> Última actualización: [FECHA]

---

## Pasos obligatorios (en orden)

### Paso 1 — Leer contexto activo
Verificar que `.claude/ACTIVE_CONTEXT.md` existe y fue generado recientemente (menos de 24 horas).
Si no existe o está desactualizado, ejecutar `bash brain-agent/scripts/detect-context.sh` antes de continuar.
**Salida esperada:** Confirmación de que el contexto del proyecto correcto está cargado.

---

### Paso 2 — Describir el cambio solicitado
Reformular el cambio solicitado por el usuario con palabras propias, incluyendo:
- Qué comportamiento tiene el sistema actualmente
- Qué comportamiento tendrá después del cambio
- Qué desencadenó la necesidad de este cambio (si se conoce)
**Salida esperada:** Descripción clara en 3-5 oraciones que el usuario puede validar antes de continuar.

---

### Paso 3 — Identificar archivos involucrados
Listar:
- Archivos que serán **modificados**
- Archivos que serán **leídos** como referencia
- Archivos que **no serán tocados** (especialmente si podrían parecer relacionados)
**Salida esperada:** Lista explícita de archivos con su rol en el cambio.

---

### Paso 4 — Evaluar impacto (usar IMPACT_RULES.md)
Responder las 5 preguntas del checklist de `IMPACT_RULES.md`.
Determinar el nivel de riesgo usando `RISK_MATRIX.md`.
**Salida esperada:** Nivel de riesgo declarado con justificación.

---

### Paso 5 — Revisar DEPENDENCIES.md
Verificar que el cambio no afecta contratos con dependencias externas.
Si afecta: documentar qué dependencias necesitan ser notificadas o actualizadas.
**Salida esperada:** Confirmación de "sin impacto en dependencias" o lista de dependencias afectadas.

---

### Paso 6 — Consultar RISK_MATRIX.md
Confirmar el nivel de riesgo del componente específico.
Si el nivel es CRÍTICO o ALTO: aplicar las reglas de escalamiento de RISK_MATRIX.md.
**Salida esperada:** Nivel confirmado y acciones requeridas según ese nivel.

---

### Paso 7 — Proponer cambio
Usar el formato de propuesta definido en `AGENT.md`.
Incluir todos los campos: cambio, archivos afectados, nivel de riesgo, dependencias, pruebas.
Esperar confirmación explícita antes de continuar.
**Salida esperada:** Aprobación del usuario.

---

### Paso 8 — Implementar y documentar
Implementar sólo lo declarado en la propuesta aprobada.
Si durante la implementación se descubre que se necesita modificar algo no declarado:
  → DETENER la implementación
  → Volver al Paso 7 con la propuesta actualizada
Al finalizar, reportar: qué se hizo, qué pruebas se ejecutaron, resultado de las pruebas.
**Salida esperada:** Cambio implementado + reporte de pruebas ejecutadas.

---

## Casos especiales

### Si el usuario pide un cambio "rápido" o "pequeño"
No saltear pasos. Aplicar el flujo completo pero de forma eficiente.
Los cambios "pequeños" son históricamente los que causan más incidentes por falta de análisis.

### Si hay urgencia (incidente en producción)
1. Documentar brevemente el incidente y el cambio propuesto (Pasos 2-3 en formato reducido).
2. Evaluar riesgo rápidamente (Paso 4) — si hay duda, consultar al equipo.
3. Proponer y obtener aprobación (Paso 7) — puede ser verbal/chat pero debe quedar registrado.
4. Implementar (Paso 8).
5. Completar la documentación completa post-incidente.

### Si no está claro cuál es el cambio correcto
Volver al usuario con preguntas específicas antes de entrar al flujo.
No iniciar análisis sobre un cambio que no está claramente definido.

---

## Tiempos esperados por paso (referencia)

| Paso | Tiempo típico | Señal de alerta |
|------|--------------|-----------------|
| 1 — Leer contexto | < 2 min | Si tarda más, el contexto puede estar corrupto |
| 2 — Describir cambio | 2-5 min | Si no se puede describir en 5 min, el cambio no está bien definido |
| 3 — Identificar archivos | 5-10 min | Si hay más de 10 archivos, considerar dividir la tarea |
| 4 — Evaluar impacto | 5-15 min | Si no se puede determinar el nivel, escalar |
| 5-6 — Deps y Riesgo | 5-10 min | — |
| 7 — Proponer | 5 min | — |
| 8 — Implementar | [Variable] | Si se descubren cambios no declarados, volver al Paso 7 |
