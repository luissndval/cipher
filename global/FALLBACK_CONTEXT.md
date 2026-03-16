# FALLBACK_CONTEXT.md
> Este archivo se activa cuando brain-agent no encuentra un mapeo específico para el repositorio actual en `context-map.json`.
> Se aplica como contexto genérico de análisis seguro.

---

## ¿Por qué estás viendo esto?

El resolver de contexto (`detect-context.sh` o `detect-context.ps1`) buscó el nombre del repositorio actual en `context-map.json` y no encontró una entrada para él.

Esto ocurre cuando:
- El repositorio es nuevo y aún no ha sido registrado en brain-agent.
- El nombre del repositorio cambió y el mapeo no fue actualizado.
- brain-agent se añadió como submodulo a un proyecto sin configurar su mapeo.

---

## Cómo agregar este repositorio al contexto

1. Crea una carpeta de proyecto en `brain-agent/projects/`:
   ```bash
   mkdir brain-agent/projects/nombre-de-tu-repo
   ```

2. Copia los templates como punto de partida:
   ```bash
   cp -r brain-agent/projects/_template/* brain-agent/projects/nombre-de-tu-repo/
   ```

3. Completa los 6 archivos reemplazando los marcadores `[PLACEHOLDER]`:
   - `BUSINESS_RULES.md` — Reglas de negocio del servicio
   - `DEPENDENCIES.md` — Dependencias de entrada y salida
   - `RISK_MATRIX.md` — Niveles de riesgo por componente
   - `IMPACT_RULES.md` — Reglas de evaluación de impacto
   - `TASK_FLOW.md` — Flujo de trabajo para tareas
   - `TEST_STRATEGY.md` — Estrategia de pruebas

4. Registra el repositorio en `brain-agent/context-map.json`:
   ```json
   {
     "mappings": {
       "nombre-de-tu-repo": "nombre-de-tu-repo"
     }
   }
   ```

5. Vuelve a ejecutar el resolver:
   ```bash
   bash brain-agent/scripts/detect-context.sh
   ```

---

## Reglas genéricas aplicables a cualquier proyecto

Dado que no hay contexto específico disponible, el agente aplicará estas reglas conservadoras:

### Análisis de impacto
- Asumir nivel de riesgo **ALTO** para cualquier cambio hasta que se pueda determinar el nivel real con información de proyecto.
- No realizar cambios en archivos de configuración, infraestructura, o acceso a datos sin confirmación explícita.
- Documentar todas las asunciones realizadas durante el análisis.

### Exploración de código
- Leer los `README.md` del proyecto antes de proponer cualquier cambio.
- Identificar el stack tecnológico antes de sugerir implementaciones específicas.
- Buscar patrones existentes en el codebase antes de introducir nuevos patrones.

### Comunicación
- Señalar explícitamente que se está operando sin contexto de proyecto específico.
- Solicitar información de dominio al usuario antes de proceder con cambios de lógica de negocio.
- Proponer contexto mínimo a documentar si el usuario quiere que brain-agent opere con mayor autonomía en este repositorio.

### Restricciones en modo fallback
- No ejecutar migraciones de base de datos.
- No modificar pipelines de CI/CD.
- No realizar cambios que afecten más de 3 archivos sin aprobación explícita.
- Preferir propuestas sobre implementación directa.

---

## Referencia rápida de archivos de brain-agent

| Archivo | Propósito |
|---------|-----------|
| `context-map.json` | Mapeo de repos a carpetas de contexto |
| `global/GLOBAL_RULES.md` | Reglas universales |
| `global/AGENT.md` | Comportamiento del agente |
| `projects/*/BUSINESS_RULES.md` | Reglas de negocio por servicio |
| `projects/*/DEPENDENCIES.md` | Dependencias externas |
| `projects/*/RISK_MATRIX.md` | Niveles de riesgo |
| `projects/*/IMPACT_RULES.md` | Evaluación de impacto |
| `projects/*/TASK_FLOW.md` | Flujo de trabajo |
| `projects/*/TEST_STRATEGY.md` | Estrategia de pruebas |
