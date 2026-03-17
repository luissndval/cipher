# cipher

> Memoria persistente y portable para agentes IA.
> Un sistema de contexto centralizado para consultoras y equipos de desarrollo.

**cipher no es un agente. Es la memoria que cualquier agente consume.**
El agente cambia (Claude, Gemini, Codex). La memoria siempre es la misma.

---

## El problema que resuelve

Sin cipher, cada sesión con un agente IA empieza desde cero. El dev explica el proyecto, las reglas de negocio, el stack, las dependencias — cada vez, en cada herramienta.

Con cipher, el contexto vive en un repositorio central. Todos los devs del equipo comparten la misma memoria. Todos los agentes la consumen automáticamente.

---

## Instalación

```bash
git clone https://github.com/tu-org/cipher.git
cd cipher
bash install.sh
```

`install.sh` hace todo:
- Instala dependencias Python (`anthropic`, `google-genai`, `openai`)
- Registra `cipher` como comando global en tu sistema
- Crea `.cipher/config.local.json` a partir del ejemplo

Reiniciá tu terminal al finalizar.

---

## Configuración de API keys

Editá `.cipher/config.local.json` (nunca va al repo):

```json
{
  "anthropic": { "api_key": "sk-ant-...", "model": "claude-sonnet-4-6" },
  "google":    { "api_key": "AIza...",    "model": "gemini-2.5-flash"  },
  "openai":    { "api_key": "sk-...",     "model": "gpt-4o"            }
}
```

O exportá las variables de entorno (tienen prioridad máxima):

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export GOOGLE_API_KEY=AIza...
export OPENAI_API_KEY=sk-...
```

---

## Dos IAs, dos roles

| IA | Rol | Cuándo |
|----|-----|--------|
| **Gemini** | Análisis y generación de contexto | `cipher init`, `cipher update` |
| **Claude** | Agente de codificación | `cipher claude` |

Gemini aprovecha su ventana de 400k tokens para leer el código fuente completo de cada repo y generar el contexto. Claude recibe ese contexto inyectado y ejecuta el desarrollo.

> ¿Querés integrar otro provider? Implementá `analyze_repo()` en `providers.py` y registralo en `get_analysis_provider()`.

---

## Uso

### 1. Registrar un cliente y sus repos

```bash
cd /proyectos/cliente-xyz      # carpeta con uno o varios repos
cipher init
```

`cipher init` (usa Gemini por defecto):
1. Detecta todos los subdirectorios con `.git`
2. Pregunta cuáles registrar
3. Lee el código fuente real de cada repo (hasta 400k chars con Gemini)
4. Genera los 4 archivos de contexto por repo en una sola llamada:
   - `ARCHITECTURE.md` — stack, patrones, estructura
   - `BUSINESS_RULES.md` — reglas y flujos de negocio
   - `DEPENDENCIES.md` — dependencias y servicios externos
   - `RISK_MATRIX.md` — áreas críticas y riesgos
5. Los guarda en `clients/<cliente>/<repo>/`
6. Registra el cliente en `.cipher/config.json`

### 2. Iniciar una sesión de desarrollo

```bash
cipher claude
```

Al ejecutar este comando, cipher:

1. Resuelve el cliente desde `.cipher/config.json`
2. Muestra los repos registrados y pregunta en cuál trabajar:
   ```
   ▸ Repos disponibles:
     1. takeapp-api   (C:\...\takeapp-api)
     2. takeapp-web   (C:\...\takeapp-web)
   Seleccioná el repo [1-2]:
   ```
3. Carga o genera `ACTIVE_CONTEXT.md` (contexto ensamblado en capas)
4. Pregunta el tipo de work item:
   ```
   ▸ Tipo de work item:
     1. FEATURE
     2. TASK
     3. ERROR
     4. HOTFIX
   ```
5. Pide número de ticket, título y descripción
6. Genera el nombre de branch: `FEATURE-142-AGREGAR-LOGIN-CON-GOOGLE`
7. Crea `task-agent.md` con instrucciones paso a paso para el agente
8. Lanza el agente con el contexto inyectado

El agente recibe instrucciones para:
- Crear la branch con el nombre generado
- Implementar la tarea
- Hacer commit, push y crear el PR al finalizar

### 3. Actualizar contexto después de un cambio

```bash
cipher update
```

Analiza el `git diff` con Gemini, detecta cambios arquitecturales y propone actualizar los archivos de contexto. Si el cambio afecta a otros repos del cliente, genera `ALERT.md` automáticamente.

### 4. Ver estado del proyecto

```bash
cipher status
```

Muestra: contexto cargado, alertas pendientes, estado de archivos de contexto.

---

## Flujo operacional completo

Ver [FLOW.html](./FLOW.html) para el diagrama visual interactivo.

---

## Estructura del repositorio

```
cipher/
├── install.sh                       ← instalación global
├── bin/cipher                         ← wrapper del comando global
├── .cipher/
│   ├── config.json                  ← clientes y repos registrados (va al repo)
│   ├── config.local.json            ← API keys (NO va al repo, en .gitignore)
│   ├── config.local.example.json    ← plantilla para nuevos usuarios
│   └── sessions/
│       └── <cliente>/<repo>/
│           ├── ACTIVE_CONTEXT.md    ← contexto ensamblado (generado)
│           └── task-agent.md        ← ticket activo (generado)
├── global/
│   ├── CONVENTIONS.md               ← estándares de código de la consultora
│   ├── WORKFLOW.md                  ← GitFlow, PRs, proceso estándar
│   └── AGENT.md                     ← comportamiento base del agente
├── clients/
│   ├── _template/                   ← plantilla para nuevos proyectos
│   └── <cliente>/
│       └── <repo>/
│           ├── ARCHITECTURE.md
│           ├── BUSINESS_RULES.md
│           ├── DEPENDENCIES.md
│           ├── RISK_MATRIX.md
│           ├── IMPACT_RULES.md
│           ├── TASK_FLOW.md
│           └── TEST_STRATEGY.md
└── cli/
    ├── main.py                      ← punto de entrada del CLI
    ├── context_loader.py            ← ensambla ACTIVE_CONTEXT.md
    ├── providers.py                 ← abstracción Claude / Gemini / OpenAI
    ├── requirements.txt
    └── commands/
        ├── init.py                  ← cipher init
        ├── session.py               ← cipher claude / gemini / codex
        ├── update.py                ← cipher update
        ├── status.py                ← cipher status
        └── export.py                ← cipher export
```

---

## Cómo funciona el contexto

Cuando ejecutás `cipher claude`, el contexto se ensambla en tres capas:

```
CAPA GLOBAL     →  CONVENTIONS.md + WORKFLOW.md + AGENT.md
                   (reglas de la consultora, aplica a todos los proyectos)

CAPA CLIENTE    →  BUSINESS_RULES.md + ARCHITECTURE.md
                   (reglas y arquitectura del cliente específico)

CAPA PROYECTO   →  DEPENDENCIES.md + RISK_MATRIX.md + IMPACT_RULES.md
                   + TASK_FLOW.md + TEST_STRATEGY.md
                   (detalles del repo en el que se trabaja)
```

El resultado se guarda en `.cipher/sessions/<cliente>/<repo>/ACTIVE_CONTEXT.md` — nunca en el repo del cliente.

El modo por defecto es `summary` (~30 líneas por archivo). Los archivos completos se referencian como paths y el agente los carga on-demand.

---

## Agregar un cliente manualmente

Si preferís no usar `cipher init`:

```bash
# 1. Copiar template
cp -r clients/_template clients/mi-cliente/mi-repo

# 2. Llenar los archivos .md con contenido real

# 3. Registrar en .cipher/config.json
```

```json
{
  "clients": {
    "mi-cliente": {
      "repos": {
        "mi-repo": {
          "name": "mi-repo",
          "path": "/ruta/absoluta/al/repo",
          "owner": "dev@consultora.com",
          "depends_on": [],
          "consumed_by": []
        }
      }
    }
  }
}
```

---

## Troubleshooting

**`cipher: command not found`**
Reiniciá tu terminal o ejecutá `source ~/.zshrc` / `source ~/.bashrc`.

**`No se encontró cipher`**
cipher debe estar en el directorio padre del repo, o configurá:
```bash
export CIPHER_PATH=/ruta/a/cipher
```

**`API key no configurada`**
Editá `.cipher/config.local.json` o exportá la variable de entorno correspondiente.

**`cipher init` no detecta mis repos**
Verificá que los directorios tengan `.git` inicializado:
```bash
ls /tu/carpeta/*/.git
```

**`ModuleNotFoundError`**
Activá el virtualenv o instalá dependencias:
```bash
pip install -r cli/requirements.txt
```

**`ALERT.md` en mi repo**
Otro repo del mismo cliente tuvo un cambio que te afecta. Leé el archivo antes de continuar.

---

## Contribuir

1. Fork del repo
2. Branch: `FEATURE-<numero>-<descripcion>` desde `main`
3. PR con descripción del cambio
4. Los cambios al CLI deben incluir prueba manual documentada

---

## Licencia

MIT — Libre para uso comercial y personal.
