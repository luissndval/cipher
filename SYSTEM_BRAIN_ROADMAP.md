# System Brain — Roadmap v1

> Cipher como base de memoria.
> El objetivo es un context selector real, no mejores prompts.

---

## Estado de fases

| Fase | Nombre                     | Estado      | Estimación   |
|------|----------------------------|-------------|--------------|
| 0    | Hardening de Cipher        | pendiente   | 2 semanas    |
| 1    | Code Indexer estructural   | pendiente   | 3–4 semanas  |
| 2    | Dependency Graph           | pendiente   | 2–3 semanas  |
| 3    | Context Pack Builder       | pendiente   | 3 semanas    |
| 4    | Task Engine                | pendiente   | 2–3 semanas  |
| 5    | Manifest y Audit System    | pendiente   | 2 semanas    |
| 6    | CI/CD Integration          | pendiente   | 2 semanas    |

**Total estimado:** 16–19 semanas (8–12 si hay piezas reutilizables y 2 personas)

---

## Fase 0 — Hardening de Cipher

**Objetivo:** convertir Cipher en una base estable y coherente como Memory Layer.

### Tareas

- [ ] **F0-1** Ordenar estructura del repo
  - Separar módulos: `core/`, `memory/`, `analysis/`, `agents/`
  - Mover lógica de sesión fuera de `commands/session.py`
  - Definir contratos claros entre módulos

- [ ] **F0-2** Reducir lógica frágil basada en prompts
  - Identificar qué partes del contexto generado por LLM se usan como "verdad estructural"
  - Marcar esas secciones como `DRAFT` hasta que haya validación determinística

- [ ] **F0-3** Mejorar manejo de sesiones
  - Agregar `session_id` único por sesión
  - Guardar metadata de sesión: timestamp, repo, cliente, agente, task

- [ ] **F0-4** Agregar manifests de sesión
  - Cada sesión genera un `session_manifest.json` con:
    - archivos de contexto usados
    - proveedor IA
    - task asociada
    - hash del contexto

- [ ] **F0-5** Tests básicos
  - Tests para `ContextLoader`: detección de repo, resolución de cliente
  - Tests para `resolve_project` con configs válidas e inválidas
  - Tests para `cmd_init` con repos mock

**Resultado:** Cipher opera como Memory Layer estable. Base lista para Fase 1.

---

## Fase 1 — Code Indexer estructural

**Objetivo:** entender el código sin depender del LLM.

### Tareas

- [ ] **F1-1** Diseñar esquema del índice estructural
  - Definir modelo: `File`, `Symbol`, `Import`, `Class`, `Method`, `Module`
  - Definir formato de storage: JSON por repo o SQLite embebido

- [ ] **F1-2** Parser por lenguaje
  - Python: `ast` stdlib
  - TypeScript/JavaScript: `tree-sitter` o `ts-morph`
  - Go: `go/parser`
  - Agregar soporte por lenguaje de forma modular (plugin-style)

- [ ] **F1-3** Extractor de imports y dependencias internas
  - Para cada archivo: qué importa, de dónde
  - Resolver rutas relativas a paths absolutos del repo

- [ ] **F1-4** Comando `cipher index`
  - Genera el índice estructural de un repo
  - Guarda en `.cipher/index/<repo_name>/index.json`
  - Muestra resumen: archivos, símbolos, imports

- [ ] **F1-5** Integración con `cipher init`
  - Al hacer `init`, correr indexación estructural como paso adicional
  - El análisis LLM pasa a ser complementario, no la única fuente

**Resultado:** Structure Layer con conocimiento determinístico del código.

---

## Fase 2 — Dependency Graph

**Objetivo:** calcular impacto de cambios sin depender del LLM.

### Tareas

- [ ] **F2-1** Construir grafo de dependencias por repo
  - Nodos: archivos, módulos, clases, funciones
  - Aristas: import, call, inherit, implement
  - Usar índice de Fase 1 como input

- [ ] **F2-2** Grafo cross-repo (multi-repo)
  - Mapear dependencias entre repos registrados en el mismo cliente
  - Basado en endpoints expuestos/consumidos de `DEPENDENCIES.md` + análisis real

- [ ] **F2-3** Cálculo de impact set
  - Dado un archivo o símbolo, calcular qué otros archivos lo usan (directa o transitivamente)
  - Resultado: lista ordenada por profundidad de impacto

- [ ] **F2-4** Comando `cipher impact <archivo>`
  - Muestra el impact set de un archivo
  - Output: lista de archivos afectados con nivel de impacto

- [ ] **F2-5** Persistencia del grafo
  - Guardar en `.cipher/index/<repo_name>/graph.json`
  - Invalidar y reconstruir al detectar cambios (`git diff`)

**Resultado:** el sistema puede calcular un impact set determinístico.

---

## Fase 3 — Context Pack Builder

**Objetivo:** generar el contexto mínimo útil por tarea.

### Tareas

- [ ] **F3-1** Definir esquema de Context Pack
  - `target_files`: archivos directamente relevantes
  - `dependency_files`: dependencias expandidas
  - `rules`: reglas de negocio y arquitectura aplicables
  - `architecture_snippet`: fragmento del ARCHITECTURE.md relevante
  - `manifest`: metadata del pack (timestamp, budget, repo, task_id)

- [ ] **F3-2** Algoritmo de selección de archivos
  - Input: descripción de tarea + repo
  - Paso 1: búsqueda léxica/semántica en índice para candidatos iniciales
  - Paso 2: expansión de dependencias via grafo (Fase 2)
  - Paso 3: scoring por relevancia + impacto

- [ ] **F3-3** Token budget manager
  - Definir presupuesto de tokens por proveedor (ej: 60k Claude, 400k Gemini)
  - Recortar contexto respetando prioridades: target > dependencias > reglas > arquitectura

- [ ] **F3-4** Generador del pack
  - Output: archivo `context_pack.md` + `context_manifest.json`
  - El pack es el único input que recibe el agente (no el repo completo)

- [ ] **F3-5** Comando `cipher pack <descripción de tarea>`
  - Genera el context pack para una tarea
  - Muestra resumen: archivos incluidos, tokens estimados, budget usado

**Resultado:** Context Selector real. La IA recibe solo lo que necesita.

---

## Fase 4 — Task Engine

**Objetivo:** traducir tickets/work items en acciones IA formalizadas.

### Tareas

- [ ] **F4-1** Definir schema de Task
  - `task_id`, `type` (FEATURE/TASK/ERROR/HOTFIX), `title`, `description`
  - `repo`, `client`, `target_files` (opcional), `context_pack_id`
  - `status`: PENDING / IN_PROGRESS / DONE / FAILED

- [ ] **F4-2** Integración con fuentes de tickets
  - Soporte para input manual (CLI)
  - Soporte para Linear (webhook o API)
  - Soporte para GitHub Issues

- [ ] **F4-3** Task analyzer
  - Dado el título + descripción de la task, identificar:
    - repo objetivo
    - archivos candidatos (búsqueda en índice)
    - tipo de cambio esperado
  - Invocar Context Pack Builder (Fase 3)

- [ ] **F4-4** Generación de intención estructurada
  - Output: `task_intent.json` con:
    - archivos a modificar
    - reglas aplicables
    - restricciones
    - contexto adjunto (context pack)

- [ ] **F4-5** Comando `cipher task <ticket_id o descripción>`
  - Crea una task, genera intent, construye context pack
  - Lanza el agente con toda la información estructurada

**Resultado:** entrada al agente es una task formalizada, no un prompt libre.

---

## Fase 5 — Manifest y Audit System

**Objetivo:** trazabilidad completa de cada cambio generado por IA.

### Tareas

- [ ] **F5-1** Schema de `CONTEXT_MANIFEST.json`
  - `task_id`, `timestamp`, `model`, `brain_version`
  - `files_used`: lista de archivos incluidos en el contexto
  - `dependencies_included`: archivos expandidos desde el grafo
  - `rules_applied`: reglas de negocio usadas
  - `token_budget`: presupuesto total y usado
  - `context_pack_hash`: hash del pack enviado al LLM

- [ ] **F5-2** Generación automática del manifest por sesión
  - Cada `cipher claude` / `cipher task` genera un manifest
  - Se guarda en `.cipher/sessions/<client>/<repo>/<task_id>/CONTEXT_MANIFEST.json`

- [ ] **F5-3** Adjuntar manifest al PR
  - Al crear el PR, incluir el manifest como comentario o archivo adjunto
  - Template: `## Context usado por la IA\n<tabla de archivos y reglas>`

- [ ] **F5-4** Audit log centralizado
  - Archivo `.cipher/audit/audit_log.jsonl`
  - Cada entrada: task, manifest_hash, pr_url, resultado

- [ ] **F5-5** Comando `cipher audit [task_id]`
  - Muestra el historial de cambios generados por IA
  - Puede filtrar por repo, cliente, fecha

**Resultado:** cada PR incluye trazabilidad completa de qué evidencia usó la IA.

---

## Fase 6 — CI/CD Integration

**Objetivo:** cerrar el loop del System Brain dentro de una pipeline CI/CD real.

### Tareas

- [ ] **F6-1** Trigger desde CI (GitHub Actions / GitLab CI)
  - Action que invoca `cipher task` al abrir un issue con label `ai-task`
  - Pasa el issue como input al Task Engine (Fase 4)

- [ ] **F6-2** Pipeline de generación automática
  - CI recibe task → invoca cipher → genera contexto → llama al LLM → produce diff
  - El diff se aplica en un branch automático

- [ ] **F6-3** PR automático con manifest adjunto
  - El CI crea el PR con:
    - título estructurado `[TIPO-ID] título`
    - body con descripción de la tarea
    - `CONTEXT_MANIFEST.json` adjunto como comentario
    - checklist de revisión humana

- [ ] **F6-4** Gate de revisión humana
  - El PR requiere aprobación manual antes de merge
  - CI bloquea auto-merge si el manifest no existe o está incompleto

- [ ] **F6-5** Feedback loop post-merge
  - Al hacer merge, correr `cipher update` automáticamente
  - Actualizar índice estructural y contexto del repo
  - Registrar en audit log: pr_merged, files_changed, impact_actual vs impact_predicted

- [ ] **F6-6** Docker / self-hosted runner
  - Imagen Docker con cipher + dependencias de parsing instaladas
  - Runner configurado para correr en infra propia o GitHub-hosted

**Resultado:** loop completo task → contexto → LLM → diff → PR → audit → índice actualizado.

---

## Principio rector

> No resolver esto con prompts cada vez mejores.
>
> El camino correcto es:
> **estructura determinística + selección de contexto + IA + trazabilidad**
