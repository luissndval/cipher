# cipher — Flujo Operacional

> Qué hace cada comando, en qué orden, y dónde vive cada archivo.

---

## Visión general

```
Developer                    cipher CLI                     Agente IA
    │                            │                             │
    │── cipher init ──────────────>│                             │
    │                            │── escanea repos             │
    │                            │── lee código fuente         │
    │                            │── llama a la IA ───────────>│
    │                            │<── genera contexto ─────────│
    │                            │── guarda en clients/        │
    │<── confirma registros ─────│                             │
    │                            │                             │
    │── cipher claude ────────────>│                             │
    │                            │── resuelve cliente          │
    │                            │── muestra repos             │
    │<── seleccioná repo ────────│                             │
    │── elige repo ─────────────>│                             │
    │<── tipo de work item? ─────│                             │
    │── FEATURE / nro / título ->│                             │
    │                            │── genera branch name        │
    │                            │── crea task-agent.md        │
    │                            │── escribe CLAUDE.md temp    │
    │                            │── lanza agente ────────────>│
    │                            │                      trabaja │
    │                            │               crea branch   │
    │                            │              implementa...  │
    │                            │               commit+push   │
    │                            │               crea PR       │
    │<── sesión finalizada ──────│<────────────────────────────│
    │                            │── elimina CLAUDE.md         │
    │                            │                             │
    │── cipher update ────────────>│                             │
    │                            │── lee git diff              │
    │                            │── analiza con IA ──────────>│
    │                            │<── propone cambios ─────────│
    │<── confirmar cambios? ─────│                             │
    │── confirma ───────────────>│                             │
    │                            │── actualiza archivos .md    │
    │                            │── genera ALERT.md si aplica │
```

---

## Comando: `cipher init`

**Propósito:** registrar un cliente nuevo y generar su contexto con IA.

```
cipher init
    │
    ├─ 1. Escanear directorio actual
    │      └─ busca subdirectorios con .git
    │         muestra lista y pregunta cuáles registrar
    │
    ├─ 2. Elegir agente de análisis
    │      └─ Claude / Gemini / OpenAI
    │         verifica que el provider esté configurado
    │         si no, pide API key y la guarda en config.local.json
    │
    ├─ 3. Nombrar el cliente
    │      └─ nombre del cliente/empresa (ej: "acme-corp")
    │
    ├─ 4. Analizar cada repo con IA
    │      └─ lee estructura de directorios (4 niveles)
    │         lee archivos de código fuente relevantes
    │         envía todo al agente en un único request
    │         parsea respuesta con delimitadores <<<FILE:nombre>>>
    │
    ├─ 5. Guardar archivos de contexto
    │      └─ clients/<cliente>/<repo>/
    │             ARCHITECTURE.md
    │             BUSINESS_RULES.md
    │             DEPENDENCIES.md
    │             RISK_MATRIX.md
    │
    └─ 6. Actualizar config
           └─ .cipher/config.json  ← agrega cliente y repos con paths
```

**Archivos tocados:**
| Archivo | Acción |
|---------|--------|
| `clients/<cliente>/<repo>/*.md` | Creados por IA |
| `.cipher/config.json` | Actualizado con el nuevo cliente |
| `.cipher/config.local.json` | Actualizado con API key (si se configura) |

---

## Comando: `cipher claude` / `cipher gemini` / `cipher codex`

**Propósito:** abrir una sesión de desarrollo con contexto completo y ticket activo.

```
cipher claude
    │
    ├─ 1. Resolver cliente
    │      └─ detecta repo actual via git rev-parse
    │         busca match en .cipher/config.json
    │         si no encuentra: ofrece cipher init
    │
    ├─ 2. Seleccionar repo de trabajo
    │      └─ muestra todos los repos del cliente
    │         desarrollador elige en cuál trabajar
    │         (si hay solo uno, lo usa directamente)
    │
    ├─ 3. Cargar contexto
    │      └─ si existe .cipher/sessions/<cliente>/<repo>/ACTIVE_CONTEXT.md
    │             lo usa directamente
    │         si no existe
    │             ensambla desde capas (global + cliente + proyecto)
    │             guarda en sessions/
    │
    ├─ 4. Crear ticket
    │      └─ pregunta tipo: FEATURE / TASK / ERROR / HOTFIX
    │         pide número, título y descripción
    │         genera nombre de branch: TIPO-NUMERO-TITULO-EN-MAYUSCULAS
    │         crea task-agent.md con instrucciones paso a paso
    │
    ├─ 5. Inyectar contexto
    │      └─ [Claude]  escribe CLAUDE.md temporal en el repo
    │         [Gemini]  carga contexto como system prompt en memoria
    │         [Codex]   escribe codex-context.md temporal
    │         [Aider]   escribe CONVENTIONS.md temporal
    │
    ├─ 6. Lanzar agente
    │      └─ abre el CLI/sesión del agente elegido
    │         pasa prompt inicial: "empezá por crear la branch..."
    │
    └─ 7. Al salir (finally)
           └─ elimina CLAUDE.md del repo cliente
              (o restaura contenido anterior si ya existía)
```

**Instrucciones que recibe el agente:**
1. Crear la branch `TIPO-NUMERO-TITULO`
2. Implementar la tarea
3. `git add -p` → `git commit` → `git push -u origin <branch>`
4. `gh pr create` con título y descripción pre-armados
5. `cipher update` para cerrar la sesión

**Archivos tocados:**
| Archivo | Acción |
|---------|--------|
| `.cipher/sessions/<cliente>/<repo>/ACTIVE_CONTEXT.md` | Creado/leído |
| `.cipher/sessions/<cliente>/<repo>/task-agent.md` | Creado |
| `<repo>/CLAUDE.md` | Creado temporalmente, eliminado al salir |

---

## Ensamblado de contexto (capas)

```
ACTIVE_CONTEXT.md
│
├─ CAPA GLOBAL  ──────────────────────────────────────── aplica a todos
│   ├─ global/CONVENTIONS.md    (estándares de código)
│   ├─ global/WORKFLOW.md       (GitFlow, proceso de PRs)
│   └─ global/AGENT.md          (comportamiento del agente)
│
├─ CAPA CLIENTE  ─────────────────────────────────────── aplica al cliente
│   ├─ clients/<cliente>/BUSINESS_RULES.md
│   └─ clients/<cliente>/ARCHITECTURE.md
│
└─ CAPA PROYECTO  ────────────────────────────────────── específico del repo
    ├─ clients/<cliente>/<repo>/BUSINESS_RULES.md
    ├─ clients/<cliente>/<repo>/DEPENDENCIES.md
    ├─ clients/<cliente>/<repo>/RISK_MATRIX.md
    ├─ clients/<cliente>/<repo>/IMPACT_RULES.md
    ├─ clients/<cliente>/<repo>/TASK_FLOW.md
    └─ clients/<cliente>/<repo>/TEST_STRATEGY.md
```

Modo `summary`: primeras 30 líneas de cada archivo (~900 tokens total).
Los paths completos se incluyen como referencias; el agente los carga on-demand.

---

## Formato de branch

El nombre se genera a partir del tipo, número y título del ticket:

```
FEATURE-142-AGREGAR-LOGIN-CON-GOOGLE
TASK-89-REFACTORIZAR-MODULO-PAGOS
ERROR-301-FIX-NULL-POINTER-EN-CHECKOUT
HOTFIX-7-PARCHE-CRITICO-SESION-EXPIRADA
```

Regla: `{TIPO}-{NUMERO}-{TITULO-SLUGIFICADO-EN-MAYUSCULAS}`
- Solo letras, números y guiones
- Sin caracteres especiales ni espacios
- Todo en mayúsculas

---

## Comando: `cipher update`

**Propósito:** actualizar el contexto después de terminar trabajo.

```
cipher update
    │
    ├─ 1. Obtener git diff del repo actual
    │      └─ git diff HEAD (staged + unstaged)
    │
    ├─ 2. Leer task activo
    │      └─ .cipher/sessions/<cliente>/<repo>/task-agent.md
    │
    ├─ 3. Analizar con IA
    │      └─ envía diff + task al agente
    │         pide: summary, impact_level, affected_files,
    │               cross_repo_impact, context_updates
    │
    ├─ 4. Aplicar cambios sugeridos
    │      └─ muestra propuesta al desarrollador
    │         confirma antes de sobrescribir
    │         actualiza archivos .md correspondientes
    │
    └─ 5. Impacto cruzado
           └─ si hay repos afectados
                 "¿Genero ALERT.md en <repo>? [S/n]"
                 escribe .cipher/ALERT.md en el repo afectado
```

---

## Comando: `cipher status`

**Propósito:** ver el estado actual del proyecto en cipher.

```
cipher status
    │
    ├─ muestra: cliente, proyecto, repo detectado
    ├─ indica si existe ACTIVE_CONTEXT.md y su fecha
    ├─ lista archivos de contexto y si están desactualizados
    └─ muestra alertas pendientes en repos del cliente
```

---

## Aislamiento de archivos

cipher nunca deja archivos permanentes en los repos de los clientes.

```
cipher/                              ← TODO vive acá
  .cipher/
    config.json                    ← registro de clientes
    config.local.json              ← API keys (gitignored)
    sessions/
      <cliente>/
        <repo>/
          ACTIVE_CONTEXT.md        ← contexto generado
          task-agent.md            ← ticket activo

<repo-cliente>/                    ← solo archivos temporales
  CLAUDE.md                        ← existe SOLO durante la sesión
                                      se elimina en el finally block
```

---

## Providers y modelos

| Agente | Provider | Modelo por defecto | Contexto máx. |
|--------|----------|--------------------|---------------|
| `cipher claude` | Anthropic | `claude-sonnet-4-6` | ~60k chars |
| `cipher gemini` | Google | `gemini-2.5-flash` | ~400k chars |
| `cipher codex` | OpenAI | `gpt-4o` | ~60k chars |
| `cipher aider` | Ext. (aider CLI) | según keys disponibles | — |

Los modelos se pueden sobreescribir en `.cipher/config.local.json`:
```json
{ "anthropic": { "model": "claude-opus-4-6" } }
```

---

## Diagrama de archivos por operación

```
Operación          Archivos leídos                  Archivos escritos
─────────────────────────────────────────────────────────────────────
cipher init          <repos>/**/*.{py,ts,js,...}       clients/<c>/<r>/*.md
                                                     .cipher/config.json

cipher claude        .cipher/config.json                 sessions/<c>/<r>/ACTIVE_CONTEXT.md
                   global/*.md                       sessions/<c>/<r>/task-agent.md
                   clients/<c>/<r>/*.md              <repo>/CLAUDE.md  (temporal)

cipher update        sessions/<c>/<r>/task-agent.md    clients/<c>/<r>/*.md
                   git diff HEAD                     <repo-afectado>/.cipher/ALERT.md

cipher status        sessions/<c>/<r>/ACTIVE_CONTEXT.md  —
                   .cipher/config.json
```
