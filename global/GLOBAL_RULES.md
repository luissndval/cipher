# GLOBAL_RULES.md
> Estas reglas aplican a **todos** los repositorios que usen brain-agent, independientemente del contexto de proyecto.
> Prioridad: GLOBAL_RULES > BUSINESS_RULES > IMPACT_RULES > TASK_FLOW

---

## Protocolo obligatorio antes de modificar código

Antes de realizar cualquier modificación de código, el agente DEBE:

1. **Leer el contexto activo completo** — Revisar `.claude/ACTIVE_CONTEXT.md` en su totalidad antes de proponer o ejecutar cualquier cambio. Si el archivo no existe, ejecutar `detect-context.sh` primero.

2. **Declarar el alcance del cambio** — Listar explícitamente qué archivos serán modificados, cuáles serán leídos como referencia, y cuáles no serán tocados. Nunca modificar más de lo declarado.

3. **Confirmar antes de actuar** — Presentar la propuesta de cambio completa al usuario siguiendo el formato definido en `AGENT.md` y esperar confirmación explícita antes de implementar. No asumir que "proceder" está implícito.

---

## Prohibiciones absolutas

El agente NUNCA debe:

1. **Modificar configuración de infraestructura** (variables de entorno de producción, archivos de despliegue, secretos, certificados) sin aprobación explícita y documentada del usuario.

2. **Eliminar o renombrar archivos** sin listarlos en la propuesta y obtener confirmación. La eliminación es irreversible en muchos contextos.

3. **Modificar archivos fuera del alcance declarado** — Si durante la implementación se detecta que se necesita modificar un archivo no declarado, DETENER y re-proponer con el alcance actualizado.

4. **Ignorar las BUSINESS_RULES del proyecto activo** — Las reglas de negocio son restricciones, no sugerencias. Si una implementación técnica viola una BUSINESS_RULE, la implementación es incorrecta.

5. **Ejecutar comandos destructivos** (DROP TABLE, DELETE sin WHERE, rm -rf, git push --force) sin que el usuario los haya escrito o aprobado explícitamente en la sesión actual.

---

## Comportamiento ante ambigüedad

Cuando el contexto o los requisitos no son claros, el agente DEBE:

1. **Preguntar antes de asumir** — Formular una pregunta específica y concreta. No elegir una interpretación arbitraria y proceder. La pregunta debe incluir las opciones identificadas para que el usuario elija.

2. **Escalar cuando el impacto es incierto** — Si no se puede determinar con certeza el nivel de riesgo de un cambio (porque falta contexto de RISK_MATRIX o DEPENDENCIES), tratarlo como nivel ALTO por defecto y notificarlo al usuario.

3. **Documentar el supuesto si el usuario pide continuar** — Si el usuario decide no responder la pregunta y pide proceder, registrar el supuesto adoptado en la propuesta de cambio antes de implementar.

---

## Prioridad de contexto

| Capa | Archivo | Prioridad | Descripción |
|------|---------|-----------|-------------|
| 1 — Global | `GLOBAL_RULES.md` | MÁXIMA | Reglas universales. Nunca son sobreescritas. |
| 2 — Global | `AGENT.md` | ALTA | Comportamiento del agente y límites de autonomía. |
| 3 — Proyecto | `BUSINESS_RULES.md` | ALTA | Restricciones de negocio del servicio específico. |
| 4 — Tarea | `IMPACT_RULES.md` | MEDIA | Evaluación de impacto de cambios concretos. |
| 5 — Tarea | `TASK_FLOW.md` | MEDIA | Flujo de trabajo paso a paso. |
| 6 — Tarea | `TEST_STRATEGY.md` | MEDIA | Cobertura mínima requerida antes de dar por terminado. |

En caso de conflicto entre capas, la capa de mayor prioridad prevalece. El agente debe señalar el conflicto al usuario si detecta uno.
