# AGENT.md
> Define el modo de operación del agente de IA dentro de cualquier repositorio que use brain-agent.
> Este archivo complementa GLOBAL_RULES.md y no lo sobreescribe.

---

## Modo de operación

El agente opera bajo los siguientes principios fundamentales:

1. **Transparencia total** — Cada acción propuesta debe ser visible, explicada y justificada antes de ejecutarse. El agente no realiza cambios "en background". Todo lo que hace debe poder ser auditado por el usuario en el mismo hilo de conversación.

2. **Mínimo privilegio** — El agente solicita sólo el acceso necesario para la tarea actual. No explora directorios fuera del alcance de la tarea, no lee archivos de configuración sensibles a menos que sean estrictamente necesarios, y no retiene información sensible entre sesiones.

3. **Reversibilidad preferida** — Ante dos implementaciones equivalentes, el agente elige la que sea más fácil de revertir. Si la implementación no es reversible (e.g., migraciones de base de datos), lo señala explícitamente y propone una estrategia de rollback.

---

## Límites de autonomía por tipo de cambio

| Tipo de cambio | Puede ejecutar sin confirmación | Requiere análisis previo | Requiere aprobación explícita |
|----------------|----------------------------------|--------------------------|-------------------------------|
| Leer archivos de código fuente | ✓ Sí | — | — |
| Proponer cambios (sin implementar) | ✓ Sí | ✓ Siempre | — |
| Editar lógica de negocio | — | ✓ Siempre | ✓ Sí |
| Editar configuración de servicio | — | ✓ Siempre | ✓ Sí |
| Crear nuevos archivos | — | ✓ Siempre | ✓ Sí |
| Eliminar archivos | — | ✓ Siempre | ✓ Sí (con listado explícito) |
| Ejecutar scripts de migración | — | ✓ Siempre | ✓ Sí + plan de rollback |
| Modificar CI/CD o Dockerfiles | — | ✓ Siempre | ✓ Sí |
| Modificar variables de entorno | — | ✓ Siempre | ✓ Sí (verificar por ambiente) |
| Comandos destructivos (DROP, rm -rf) | — | ✓ Siempre | ✓ Sí (escritos por usuario) |

---

## Protocolo de comunicación con el usuario

1. **Idioma del usuario** — Responder siempre en el idioma en que el usuario escribe. Si el usuario alterna idiomas, seguir el idioma de la última pregunta. Los archivos de contexto pueden estar en español; eso no impone el idioma de respuesta.

2. **Concisión con completitud** — Las propuestas de cambio deben ser completas (incluir todos los campos del formato) pero concisas. No agregar texto decorativo ni disculpas innecesarias. Ir directo al punto.

3. **Un bloqueo a la vez** — Si hay múltiples preguntas o puntos de ambigüedad, identificarlos todos pero preguntar al usuario por el más crítico primero. No bombardear con 5 preguntas simultáneas.

---

## Formato de propuesta de cambio

Toda propuesta de cambio DEBE usar este formato antes de implementar:

```
## Propuesta de cambio

**Cambio solicitado:**
[Descripción clara de qué se va a hacer y por qué]

**Archivos afectados:**
- `ruta/al/archivo.ext` — [qué se modifica]
- `ruta/al/otro.ext` — [qué se modifica]

**Archivos NO modificados (leídos como referencia):**
- `ruta/referencia.ext`

**Nivel de riesgo:** [CRÍTICO / ALTO / MEDIO / BAJO] — [justificación en 1 línea]

**Dependencias impactadas:**
- [Servicio o componente] — [cómo se ve afectado]
- (ninguna) si no aplica

**Pruebas mínimas recomendadas:**
- [ ] [Prueba específica 1]
- [ ] [Prueba específica 2]
- [ ] [Prueba de regresión si aplica]

**¿Procedo?** Esperando confirmación antes de implementar.
```

El usuario puede responder "sí", "procede", "ok", "go", o equivalente para dar luz verde. Cualquier otra respuesta se interpreta como una modificación a la propuesta.

---

## Protocolo de ejecución de tareas (CURRENT_TASK)

### 1. Al iniciar la sesión

1. **Leer `CURRENT_TASK.md`** en la raíz del repo.
   - Si no existe: indicar al desarrollador que lo cree y no proceder hasta tenerlo.
   - Si existe pero tiene campos vacíos críticos (Título, Descripción, Alcance declarado): preguntar esos campos antes de continuar. Hacer una pregunta a la vez, empezando por la más bloqueante.

2. **Crear la rama** antes de tocar cualquier archivo:
   ```
   git checkout -b <tipo>/<ticket>-<descripcion-breve>
   ```
   Formato: `tipo` = feat | fix | hotfix | refactor. `descripcion-breve` en kebab-case, máximo 4 palabras.
   Ejemplo: `feat/TAKE-123-delivery-zone-id`
   Confirmar con el desarrollador antes de hacer checkout.

3. **Actualizar estado** en `CURRENT_TASK.md`: `pending` → `in_progress`.

---

### 2. Durante la implementación

- **Ceñirse al alcance declarado**. Si se detecta que se necesita modificar un archivo fuera del Alcance declarado, DETENER y preguntar antes de continuar.
- **Comentarios en el código**: agregar comentarios inline en cualquier lógica no obvia. Formato sugerido:
  ```
  # TASK: <ticket> — <por qué se hace este cambio, no qué hace>
  ```
  No comentar código auto-explicativo. Solo comentar decisiones de diseño, workarounds o reglas de negocio incrustadas.
- **Verificar criterios de aceptación** antes de declarar la tarea como completa.

---

### 3. Protocolo de cierre (ejecutado por el agente, no por el dev)

Al verificar que los criterios de aceptación están cumplidos, el agente ejecuta automáticamente los siguientes pasos. Propone todo al dev y espera una sola confirmación antes de escribir.

#### Paso 1 — Leer el diff real de la rama
```bash
git log main..HEAD --oneline
git diff main...HEAD --name-only
git diff main...HEAD --stat
```
Si la rama base no es `main`, usar `master` o la rama por defecto detectada.

#### Paso 2 — Inferir qué cambió estructuralmente

Con el diff, determinar:

| ¿Qué buscar en el diff? | ¿Qué actualizar en brain-contexts? |
|-------------------------|-------------------------------------|
| Archivo de dependencias modificado (`package.json`, `requirements.txt`, etc.) | `DEPENDENCIES.md` |
| Endpoint agregado/modificado/eliminado | `INTEGRATION_MAP.md` + alerta si lo consumen otros repos |
| Schema/tipo compartido modificado | `INTEGRATION_MAP.md` + alerta |
| Nuevo módulo o cambio de arquitectura | `TECHNICAL_STATE.md` |
| TODO/FIXME nuevo o deuda técnica introducida | `RISK_MATRIX.md` |
| Variable de entorno nueva o removida | `INTEGRATION_MAP.md` |

#### Paso 3 — Construir propuesta y confirmar con el dev

Presentar al dev:
- Entrada de CHANGELOG.md que se va a agregar
- Lista de archivos de brain-contexts que se van a actualizar y qué cambia en cada uno
- Alertas cross-repo que se van a crear (si aplica)

Esperar confirmación. Con un "sí" proceder con todos los pasos siguientes.

#### Paso 4 — Ejecutar actualizaciones en brain-contexts

Usar los paths del bloque `## META` del ACTIVE_CONTEXT.

1. **Actualizar `CHANGELOG.md`** — agregar entrada al inicio (debajo del encabezado):

   ```markdown
   ## [TICKET] YYYY-MM-DD — Título de la tarea

   **Rama:** tipo/TICKET-descripcion
   **Archivos modificados:** lista separada por comas
   **Resumen:** qué cambió funcionalmente en 1-2 oraciones
   **Impacto cross-repo:** nombre-repo (alerta generada) | ninguno

   ---
   ```

2. **Archivar `CURRENT_TASK.md`** del repo → `PROJECT_DIR/history/TICKET.md`

3. **Resetear `CURRENT_TASK.md`** del repo al template limpio
   (copiar desde `BRAIN_CONTEXTS/projects/_template/CURRENT_TASK.md`)

4. **Actualizar archivos estructurales** según lo detectado en el Paso 2.
   Editar solo las secciones relevantes, no reescribir el archivo completo.

5. **Escribir alertas de impacto** si corresponde:
   `BRAIN_CONTEXTS/output/alerts/<repo-afectado>.md`

   ```markdown
   ## Alerta: <repo-afectado>

   **Generada por:** <repo-origen> — <rama>
   **Ticket:** <ticket>
   **Fecha:** <fecha>
   **Qué cambió:** descripción del contrato modificado
   **Archivos origen:** lista
   **Qué revisar:** instrucción concreta de qué ajustar en el repo afectado

   ---
   ```

6. **Commit en brain-contexts:**
   ```bash
   git -C <BRAIN_CONTEXTS> add projects/<client>/<repo>/CHANGELOG.md \
     projects/<client>/<repo>/history/TICKET.md \
     [otros archivos actualizados] \
     output/alerts/
   git -C <BRAIN_CONTEXTS> commit -m "chore(<repo>): update context post <TICKET>"
   ```

---

### 4. Resolución de alertas

- Cuando el dev va al repo afectado y corre `brain claude`, el agente ve `output/alerts/<repo>.md` en el contexto (sección `## ALERTAS DE IMPACTO PENDIENTES`).
- El agente trata la alerta como la tarea implícita de la sesión si no hay `CURRENT_TASK.md` activo.
- Una vez resuelto el cambio, el agente elimina la entrada del archivo de alertas (o el archivo completo si era la única).
- El agente confirma con el dev antes de eliminar y hace commit en brain-contexts.
