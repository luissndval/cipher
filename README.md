# brain-contexts

Sistema de contexto estructurado para agentes IA. En lugar de explicarle tu proyecto al agente cada vez, lo documentas aquí una sola vez y se inyecta automáticamente como system prompt.

Soporta **Claude Code**, **Gemini CLI** y **Aider**. Diseñado para consultoras con múltiples clientes y proyectos.

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

## Poblar contexto automáticamente

El script `populate-context.sh` clona un repo, lo analiza y genera todos los `.md` de contexto usando Claude.

```bash
bash brain-contexts/scripts/populate-context.sh <git-url> [client-name] [project-name]
```

**Ejemplos:**

```bash
# Con cliente
bash scripts/populate-context.sh git@github.com:org/backend.git acme-corp backend

# Sin cliente (proyecto standalone)
bash scripts/populate-context.sh https://github.com/org/app.git
```

Qué hace automáticamente:
- Clona el repo en un directorio temporal
- Extrae README, dependencias, estructura, CI/CD, código fuente
- Llama a Claude para generar cada `.md` con contenido real
- Registra el repo en `context-map.json`

> Requiere `claude` CLI instalado (`npm install -g @anthropic-ai/claude-code`).

### Primera vez (repo no registrado)

Si ejecutas `brain` desde un repo que no está en `context-map.json`, el script te preguntará automáticamente:

```
[brain] El repo 'mi-repo' no está registrado en context-map.json.

  ¿Querés generar el contexto automáticamente?

  Proporciona la URL git del repo (o Enter para omitir):
  > git@github.com:org/mi-repo.git

  Nombre del cliente (opcional, Enter para omitir):
  > acme-corp
```

---

## Setup manual: nuevo cliente + proyecto

### 1. Crea el cliente

```bash
cp -r clients/_template clients/nombre-cliente
# edita los .md con la info del cliente
```

| Archivo | Qué documenta |
|---|---|
| `CLIENT_PROFILE.md` | Quiénes son, stack preferido, contactos |
| `TECH_PREFERENCES.md` | Tecnologías aprobadas, infraestructura, estándares |
| `BILLING_RULES.md` | Modelo de facturación, horas, SLAs |
| `COMMUNICATION.md` | Canales, frecuencia de reportes, tono |

### 2. Crea el proyecto

```bash
cp -r projects/_template projects/nombre-cliente/nombre-proyecto
# edita los .md con el contexto del proyecto
```

| Archivo | Qué documenta |
|---|---|
| `BUSINESS_RULES.md` | Reglas de negocio, restricciones del dominio |
| `DEPENDENCIES.md` | Dependencias clave, versiones, integraciones |
| `TECHNICAL_STATE.md` | Estado técnico actual, deuda técnica |
| `RISK_MATRIX.md` | Riesgos conocidos y mitigaciones |
| `TASK_FLOW.md` | Cómo se trabajan las tareas |
| `TEST_STRATEGY.md` | Estrategia de testing |
| `IMPACT_RULES.md` | Zonas de alto impacto, qué no tocar sin revisión |

> No necesitas llenar todos. El agente usa lo que encuentre.

### 3. Registra el repo en `context-map.json`

```json
{
  "mappings": {
    "nombre-del-repo": "nombre-cliente/nombre-proyecto"
  }
}
```

> El nombre del repo es el que devuelve `basename $(git rev-parse --show-toplevel)`.
> Múltiples repos pueden apuntar al mismo contexto.

---

## Setup: proyecto standalone (sin cliente)

Para proyectos internos o sin cliente asociado:

```bash
cp -r projects/_template projects/nombre-proyecto
```

```json
{
  "mappings": {
    "nombre-del-repo": "nombre-proyecto"
  }
}
```

---

## Uso diario

```bash
cd ~/Projects/mi-repo

brain              # genera ACTIVE_CONTEXT.md (imprime la ruta)
brain claude       # genera contexto + lanza Claude Code
brain gemini       # genera contexto + lanza Gemini CLI
brain aider        # genera contexto + lanza Aider
```

### Capas que se inyectan al agente

```
CAPA GLOBAL      → global/                              (aplica a todos)
CAPA CLIENTE     → clients/nombre-cliente/              (si existe)
CAPA PROYECTO    → projects/nombre-cliente/nombre-proj/
CAPA TÉCNICA     → TECHNICAL_STATE.md del proyecto
CAPA TAREA       → IMPACT_RULES, TASK_FLOW, TEST_STRATEGY
```

---

## Estructura del repo

```
brain-contexts/
├── detect-context.sh          # script principal
├── context-map.json           # mapeo repo → cliente/proyecto
├── global/                    # reglas para todos los proyectos
│   ├── GLOBAL_RULES.md
│   ├── AGENT.md
│   └── FALLBACK_CONTEXT.md
├── clients/
│   ├── _template/             # plantilla de cliente
│   └── nombre-cliente/        # contexto del cliente
│       ├── CLIENT_PROFILE.md
│       ├── TECH_PREFERENCES.md
│       ├── BILLING_RULES.md
│       └── COMMUNICATION.md
├── projects/
│   ├── _template/             # plantilla de proyecto
│   └── nombre-cliente/
│       └── nombre-proyecto/   # contexto del proyecto
├── schemas/                   # esquemas de referencia para los .md
├── scripts/
│   └── install.sh             # instalador cross-platform (Mac/Linux/Windows)
└── output/                    # generado automáticamente (gitignored)
    └── ACTIVE_CONTEXT.md
```

---

## Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `BRAIN_CONTEXTS` | directorio del script | Ruta al repo brain-contexts |

```bash
export BRAIN_CONTEXTS=/ruta/a/brain-contexts
```

---

## Repo no mapeado

Si ejecutas `brain` desde un repo no registrado, usa `_template` como fallback. Para registrarlo:

1. Agrega la entrada en `context-map.json`
2. Crea la carpeta del cliente (si aplica) y del proyecto
3. Commitea los cambios en brain-contexts
