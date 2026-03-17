# IMPACT_RULES — [NOMBRE_DEL_SERVICIO]

## Reglas de evaluación de impacto
- IR-001: Si se modifica una interfaz HTTP → revisar consumidores en DEPENDENCIES.md
- IR-002: Si se modifica un evento/mensaje → revisar compatibilidad con consumidores
- IR-003: Si se modifica un modelo de datos → verificar migraciones y contratos de API
- IR-004: Si se modifica un timeout o retry → evaluar impacto en SLA
- IR-005: Si se elimina un campo → es breaking change; versionar el contrato
- IR-006: [Regla específica del proyecto]

## Checklist antes de modificar
1. ¿Qué servicios consumen el componente que voy a cambiar?
2. ¿El cambio modifica un contrato público o evento?
3. ¿Qué pruebas existentes fallarían si el cambio es incorrecto?
4. ¿Existe alguna regla en BUSINESS_RULES.md que restrinja este cambio?
5. ¿El cambio requiere migración de datos o cambio de configuración?

## Áreas de revisión por tipo de cambio
| Tipo | Áreas a revisar | Notificar |
|------|-----------------|-----------|
| Interface HTTP | Consumidores, contrato openapi | [equipos] |
| Evento | Consumidores del topic | [equipos] |
| Modelo de datos | Migraciones, APIs que exponen el modelo | [equipos] |
| Config | Entornos afectados, secrets | [equipos] |
