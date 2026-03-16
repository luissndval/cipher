# brain-contexts

Sistema de contexto estructurado para agentes IA. En lugar de explicarle tu proyecto al agente cada vez, lo documentas aquí una sola vez y se inyecta automáticamente como system prompt.

Soporta **Claude Code**, **Gemini CLI** y **Aider**.

---

## Instalación

```bash
git clone git@github.com:luissndval/brain-contexts.git
bash brain-contexts/scripts/install.sh
```

Luego recarga tu terminal:

```bash
source ~/.bashrc   # bash
source ~/.zshrc    # zsh
# Windows: abre una nueva terminal
```

Verifica que funciona:

```bash
brain --help 2>/dev/null || brain
```

---

## Setup de un nuevo proyecto

### 1. Registra tu repo en `context-map.json`

```json
{
  "mappings": {
    "nombre-de-tu-repo": "nombre-de-tu-repo"
  }
}
```

> El nombre del repo es el que devuelve `basename $(git rev-parse --show-toplevel)`.
> Múltiples repos pueden apuntar a la misma carpeta de contexto.

### 2. Crea la carpeta de contexto

```bash
cp -r projects/_template projects/nombre-de-tu-repo
```

### 3. Llena los archivos de contexto

| Archivo | Qué documenta |
|---|---|
| `BUSINESS_RULES.md` | Reglas de negocio, restricciones del dominio |
| `DEPENDENCIES.md` | Dependencias clave, versiones, notas de integración |
| `TECHNICAL_STATE.md` | Estado técnico actual, deuda técnica conocida |
| `RISK_MATRIX.md` | Riesgos conocidos y mitigaciones |
| `TASK_FLOW.md` | Cómo se trabajan las tareas en este proyecto |
| `TEST_STRATEGY.md` | Estrategia de testing, qué se prueba y cómo |
| `IMPACT_RULES.md` | Zonas de alto impacto, qué no tocar sin revisión |

> No necesitas llenar todos. El agente usa lo que encuentre.

---

## Uso diario

Ve a tu proyecto y ejecuta:

```bash
cd ~/Projects/mi-repo

brain              # solo genera ACTIVE_CONTEXT.md (imprime la ruta)
brain claude       # genera contexto + lanza Claude Code
brain gemini       # genera contexto + lanza Gemini CLI
brain aider        # genera contexto + lanza Aider
```

### ¿Qué genera?

El script combina tres capas en un solo archivo `output/ACTIVE_CONTEXT.md`:

```
CAPA GLOBAL       → global/GLOBAL_RULES.md, AGENT.md, FALLBACK_CONTEXT.md
CAPA PROYECTO     → projects/mi-repo/BUSINESS_RULES.md, DEPENDENCIES.md, etc.
CAPA TÉCNICA      → projects/mi-repo/TECHNICAL_STATE.md
CAPA TAREA        → projects/mi-repo/IMPACT_RULES.md, TASK_FLOW.md, TEST_STRATEGY.md
```

Ese archivo se pasa como system prompt al agente elegido.

---

## Estructura del repo

```
brain-contexts/
├── detect-context.sh       # script principal
├── context-map.json        # mapeo repo → carpeta de contexto
├── global/                 # reglas que aplican a todos los proyectos
│   ├── GLOBAL_RULES.md
│   ├── AGENT.md
│   └── FALLBACK_CONTEXT.md
├── projects/
│   ├── _template/          # plantilla base para nuevos proyectos
│   └── mi-repo/            # contexto de tu proyecto
├── schemas/                # esquemas de referencia para los .md
├── scripts/
│   └── install.sh          # instalador cross-platform
└── output/                 # generado automáticamente (gitignored)
    └── ACTIVE_CONTEXT.md
```

---

## Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `BRAIN_CONTEXTS` | directorio del script | Ruta al repo brain-contexts |

Útil si clonaste el repo en una ubicación no estándar:

```bash
export BRAIN_CONTEXTS=/ruta/a/brain-contexts
```

---

## Agregar un repo que no está mapeado

Si ejecutas `brain` desde un repo no registrado, usará el contexto `_template` como fallback. Para mapearlo:

1. Edita `context-map.json` y agrega la entrada
2. Crea la carpeta en `projects/` con el contexto
3. Commitea los cambios en brain-contexts
