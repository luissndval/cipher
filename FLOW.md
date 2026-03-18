# cipher — Flujo Operacional

> Sistema de memoria persistente para agentes IA.
> Estructura determinística + selección de contexto + trazabilidad completa.

---

## Arquitectura en capas

```
┌──────────────────────────────────────────────────────────────────┐
│  CLI                                                             │
│  init · index · impact · pack · task · audit · claude · update  │
├──────────────────────────────────────────────────────────────────┤
│  Task Engine          │  Context Pack Builder                    │
│  tasks/               │  pack/                                   │
│  schema · store       │  scorer · budget · builder               │
│  analyzer · sources   │                                          │
├──────────────────────────────────────────────────────────────────┤
│  Dependency Graph     │  Code Indexer                            │
│  graph/               │  index/                                  │
│  schema · resolver    │  parsers: Python · TypeScript · Go       │
│  builder              │  RepoIndexer                             │
├──────────────────────────────────────────────────────────────────┤
│  Audit & Manifest     │  Memory Layer                            │
│  audit/               │  core/ · memory/                         │
│  writer · reader      │  ContextLoader · SessionStore            │
│  pr_comment           │  config · loader                         │
└──────────────────────────────────────────────────────────────────┘
```

---

## Flujo completo

```
Developer                    cipher CLI                  Data / IA
    │                            │                          │
    ├── cipher init ──────────>  │                          │
    │                            ├─ escanea repos .git      │
    │                            ├─ analiza con LLM ──────> │
    │                            │ <── genera contexto .md ─┤
    │                            ├─ guarda clients/         │
    │                            ├─ cipher index (sin LLM)  │
    │                            ├─ → index.json            │
    │                            └─ → graph.json            │
    │                                                        │
    ├── cipher index ─────────>  │                          │
    │                            ├─ parser AST/regex/FSM    │
    │                            ├─ extrae símbolos+imports │
    │                            ├─ → index.json            │
    │                            └─ → graph.json            │
    │                                                        │
    ├── cipher impact <file> ─>  │                          │
    │                            ├─ carga graph.json        │
    │                            ├─ BFS en grafo invertido  │
    │ <── archivos afectados ──  └─ muestra depth + via     │
    │                                                        │
    ├── cipher pack "tarea" ──>  │                          │
    │                            ├─ scorer léxico           │
    │                            ├─ expansión de deps       │
    │                            ├─ trim por budget         │
    │                            ├─ → context_pack.md       │
    │ <── resumen del pack ────  └─ → context_manifest.json │
    │                                                        │
    ├── cipher task "tarea" ──>  │                          │
    │  (o --from-gh / --linear)  ├─ fetch ticket            │
    │                            ├─ detecta tipo BUG/FEAT   │
    │                            ├─ PackBuilder             │
    │                            ├─ TaskAnalyzer → intent   │
    │                            ├─ AuditWriter → manifest  │
    │                            ├─ → audit_log.jsonl       │
    │                            └─ lanza agente ─────────> │
    │                                                        │
    ├── cipher audit ─────────>  │                          │
    │                            ├─ lee audit_log.jsonl     │
    │ <── historial + PR comment └─ filtra/stats            │
    │                                                        │
    └── cipher audit --pr ────>  │                          │
                                 └─ actualiza manifest + log│
```

---

## Comando: `cipher init`

Registra repos y genera contexto con IA (marcado como `⚠️ DRAFT`).
Además corre indexación estructural sin LLM.

```
cipher init [--scan <path>]
    │
    ├─ 1. Escanear directorio → repos .git
    ├─ 2. Elegir proveedor de análisis (Gemini recomendado — 400k ctx)
    ├─ 3. Nombrar cliente
    ├─ 4. Analizar cada repo con LLM
    │      └─ genera: ARCHITECTURE.md · BUSINESS_RULES.md
    │                 DEPENDENCIES.md · RISK_MATRIX.md
    │         todos marcados ⚠️ [DRAFT] — no son verdad estructural
    ├─ 5. Indexación estructural (sin LLM, determinística)
    │      └─ → .cipher/index/<repo>/index.json
    │         → .cipher/index/<repo>/graph.json
    └─ 6. Actualizar .cipher/config.json
```

**Archivos generados:**
```
.cipher/
  config.json
  clients/<cliente>/<repo>/
    ARCHITECTURE.md          ⚠️ DRAFT — generado por LLM
    BUSINESS_RULES.md        ⚠️ DRAFT
    DEPENDENCIES.md          ⚠️ DRAFT
    RISK_MATRIX.md           ⚠️ DRAFT
  index/<repo>/
    index.json               ✓ DETERMINÍSTICO — parser AST/regex
    graph.json               ✓ DETERMINÍSTICO — grafo de imports
```

---

## Comando: `cipher index`

Indexa un repo sin LLM. Extrae símbolos, imports y construye el grafo.

```
cipher index [--repo <path>]
    │
    ├─ Python  → ast.parse() — clases, funciones, métodos, imports
    ├─ TypeScript/JS → regex — interfaces, clases, funciones, require/import
    ├─ Go → FSM línea a línea — structs, interfaces, funcs, import blocks
    │
    ├─ → .cipher/index/<repo>/index.json
    │      {files: [{path, language, symbols, imports, lines}]}
    │
    └─ → .cipher/index/<repo>/graph.json
           {nodes: {path → GraphNode}, edges: [GraphEdge], external_imports}
```

---

## Comando: `cipher impact <archivo>`

Calcula qué archivos se ven afectados si cambia un archivo dado.

```
cipher impact auth/login.py [--repo <nombre>] [--depth <n>]
    │
    ├─ carga graph.json
    ├─ BFS sobre el grafo invertido (dependents)
    ├─ retorna ImpactEntry[] ordenado por (depth, path)
    └─ muestra agrupado por nivel de profundidad
```

**Ejemplo de output:**
```
  depth 1
    users/views.py     (importa directamente auth/login.py)
  depth 2
    api/endpoints.py   via users/views.py
    tests/test_auth.py via users/views.py
```

---

## Comando: `cipher pack <descripción>`

Genera el contexto mínimo necesario para una tarea. Sin LLM.

```
cipher pack "fix login timeout" [--provider claude|gemini] [--repo <nombre>]
    │
    ├─ 1. Scorer léxico (sin LLM)
    │      └─ tokeniza descripción → palabras clave
    │         +2.0 por match en path del archivo
    │         +1.0 por match en nombre de símbolo
    │         +0.5 si archivo muy importado (top 20%, mín. 3 inbound)
    │         +0.3 si tiene símbolos definidos
    │
    ├─ 2. Selección de targets (top archivos por score)
    │
    ├─ 3. Expansión de dependencias via grafo
    │      └─ dependencies_of(target) → rol "dependency"
    │
    ├─ 4. Budget manager
    │      └─ Claude: 60k tokens · Gemini: 400k tokens
    │         90% para archivos · 5% para rules · 5% para architecture
    │         trim por newline si excede budget
    │
    ├─ 5. → .cipher/packs/<repo>/<task_id>/context_pack.md
    └─ 6. → .cipher/packs/<repo>/<task_id>/context_manifest.json
```

---

## Comando: `cipher task <descripción>`

Crea una task formalizada, genera intent, construye pack y lanza el agente.

```
cipher task "descripción"
cipher task --from-gh owner/repo#123
cipher task --from-linear ENG-456
cipher task "descripción" --dry-run
cipher task --list [--status PENDING|IN_PROGRESS|DONE|FAILED]
    │
    ├─ 1. Obtener ticket
    │      ├─ ManualSource: "título: descripción"
    │      ├─ GitHubIssueSource: GitHub REST API (GITHUB_TOKEN)
    │      └─ LinearSource: GraphQL API (LINEAR_API_KEY)
    │
    ├─ 2. Crear Task
    │      └─ detecta tipo: HOTFIX > BUG > FEATURE > TASK
    │         → .cipher/tasks/<client>/<repo>/<task_id>/task.json
    │
    ├─ 3. Construir Context Pack (ver cipher pack)
    │      └─ → .cipher/packs/<repo>/<task_id>/context_pack.md
    │
    ├─ 4. Generar ContextManifest (F5 — Audit)
    │      └─ → .cipher/sessions/<client>/<repo>/<task_id>/CONTEXT_MANIFEST.json
    │         → .cipher/audit/audit_log.jsonl (append)
    │
    ├─ 5. Generar TaskIntent
    │      └─ files_to_modify · files_to_read · constraints
    │         → .cipher/tasks/<client>/<repo>/<task_id>/task_intent.json
    │
    └─ 6. Lanzar agente con context_pack.md + task_intent.json
```

**Detección de tipo:**
```
texto contiene                     → tipo
─────────────────────────────────────────
hotfix / critical / urgent / p0    → HOTFIX
bug / fix / error / crash / falla  → BUG
add / new / implement / feature    → FEATURE
(default)                          → TASK
```

---

## Comando: `cipher audit`

Historial de trazabilidad de sesiones IA.

```
cipher audit                         lista todas las entradas
cipher audit <task_id>               detalle + PR comment preview
cipher audit --repo <nombre>         filtrar por repo
cipher audit --client <nombre>       filtrar por cliente
cipher audit --since 2024-03         filtrar desde fecha
cipher audit --result done|failed    filtrar por resultado
cipher audit --stats                 estadísticas globales
cipher audit --pr <task_id> <url>    registrar PR en el manifest
```

**PR Comment generado automáticamente:**
```markdown
## 🤖 Context usado por la IA

**Task:** `t001`  |  **Modelo:** `claude`  |  **Brain v0.5.0**
**Tokens:** 5,000 / 60,000 (8%) █░░░░░░░░░

### Archivos incluidos
| Archivo           | Rol         | Tokens |
|-------------------|-------------|--------|
| `auth/login.py`   | 🎯 target   | ~300   |
| `auth/models.py`  | 🔗 dependency | ~100 |

<details><summary>Reproducibilidad</summary>
**Context pack hash:** `deadbeef...`
</details>
```

---

## Estructura de archivos completa

```
.cipher/
  config.json                        ← clientes + repos registrados
  config.local.json                  ← API keys (gitignored)

  index/<repo>/
    index.json                       ← símbolos + imports (determinístico)
    graph.json                       ← grafo de dependencias

  packs/<repo>/<task_id>_<slug>/
    context_pack.md                  ← contexto recortado por budget
    context_manifest.json            ← metadata del pack (hash, tokens)

  tasks/<client>/<repo>/<task_id>/
    task.json                        ← PENDING→IN_PROGRESS→DONE|FAILED
    task_intent.json                 ← files_to_modify · constraints

  sessions/<client>/<repo>/<task_id>/
    CONTEXT_MANIFEST.json            ← qué vio la IA (F5 — trazabilidad)

  audit/
    audit_log.jsonl                  ← historial append-only

  clients/<client>/
    BUSINESS_RULES.md                ← ⚠️ DRAFT (LLM, nivel cliente)
    ARCHITECTURE.md                  ← ⚠️ DRAFT
    <repo>/
      ARCHITECTURE.md                ← ⚠️ DRAFT (LLM, nivel repo)
      BUSINESS_RULES.md              ← ⚠️ DRAFT
      DEPENDENCIES.md                ← ⚠️ DRAFT
      RISK_MATRIX.md                 ← ⚠️ DRAFT
```

---

## Comandos disponibles

| Comando | Descripción | Usa LLM |
|---------|-------------|---------|
| `cipher init` | Registra repos y genera contexto | Sí (análisis inicial) |
| `cipher index` | Indexa código: símbolos + imports + grafo | No |
| `cipher impact <file>` | Impact set de un archivo (BFS) | No |
| `cipher pack <desc>` | Context pack mínimo para una tarea | No |
| `cipher task <desc>` | Task formalizada → intent → pack → agente | Solo al lanzar agente |
| `cipher task --from-gh` | Task desde GitHub Issue | No (fetch) |
| `cipher task --from-linear` | Task desde Linear ticket | No (fetch) |
| `cipher audit` | Historial de sesiones IA | No |
| `cipher claude` | Sesión directa con contexto ensamblado | Solo agente |
| `cipher update` | Actualiza contexto post-cambio | Sí |
| `cipher status` | Estado del contexto actual | No |

---

## Principio rector

> No resolver esto con prompts cada vez mejores.
>
> **estructura determinística → selección de contexto → IA → trazabilidad**
