# RISK_MATRIX — notification-worker

## Niveles de riesgo

| Nivel | Criterio | Acción obligatoria |
|-------|----------|--------------------|
| CRÍTICO | Interface pública o evento compartido con múltiples consumidores | Análisis completo + notificación a equipos consumidores + prueba de contrato |
| ALTO | Lógica de negocio core con impacto directo en entrega de mensajes | Análisis de impacto + prueba de integración con provider real/mock |
| MEDIO | Componente auxiliar con dependencia externa o regla de negocio secundaria | Revisión de regla de impacto + prueba unitaria |
| BAJO | Componente aislado sin dependencias externas ni impacto en entrega | Prueba unitaria recomendada |

## Componentes del servicio y su nivel de riesgo

| Componente | Nivel | Razón | Revisar también |
|------------|-------|-------|-----------------|
| Kafka consumer / dispatcher principal | CRÍTICO | Es el punto de entrada de todos los eventos; cambios afectan a todos los productores | `NotificationRequest` schema, topic names, consumer group offsets |
| Lógica de verificación de suscripción (`UnsubscribeGuard`) | CRÍTICO | Una falla puede enviar mensajes a usuarios no suscritos, violando BR-002 y regulaciones | `user-preferences-service` contrato, estados de suscripción válidos |
| Eventos emitidos (`notification.sent`, `notification.failed`) | CRÍTICO | Consumidos por analytics-service y audit-service; cambios en schema rompen contratos | Schema Avro `NotificationEvent`, consumidores en DEPENDENCIES.md |
| Motor de reintento con backoff exponencial | ALTO | Controla SLA de entrega; fallas pueden causar duplicados o pérdida de mensajes | BR-004, idempotencia por `notification_id`, dead-letter logic |
| Despacho a SendGrid (email) | ALTO | Afecta entrega de notificaciones transaccionales críticas (OTPs, alertas) | Límites de rate, manejo de 429, campos requeridos en DEPENDENCIES.md |
| Despacho a Twilio (SMS) | ALTO | SMS usados para OTPs de autenticación; una falla impacta flujos de login | Manejo de errores Twilio, campos `To`/`From`, BR-003 |
| Renderizado de plantillas (integración con template-service) | ALTO | Una plantilla mal renderizada puede enviar contenido incorrecto o malformado | `template_id`, `template_version`, manejo de timeout de template-service |
| Lógica de horario para notificaciones marketing (BR-008) | MEDIO | Afecta solo mensajes de tipo `marketing`; error puede causar envíos fuera de horario | BR-008, manejo de timezone, tipo `transactional` no afectado |
| Despacho a Firebase FCM (push) | MEDIO | Canal de menor criticidad; tokens expirados son error esperado | Manejo de `registration-token-not-registered`, WARN-004 |
| Escritura de estado en notification-db | MEDIO | Sin esto no hay auditoría, pero no bloquea entrega | Schema tabla `notifications`, campos en DEPENDENCIES.md |
| Configuración de variables de entorno (credenciales) | MEDIO | Error en credenciales bloquea todos los despachos del canal afectado | RO-002, nombres exactos de env vars |
| Logging y métricas | BAJO | No impacta entrega; impacta observabilidad | RO-005 (no loguear PII) |
| Script de health check | BAJO | Solo afecta monitoreo del proceso | Dependencias de health check |

## Reglas de escalamiento

- Si nivel CRÍTICO: obligatorio notificar a `analytics-service`, `audit-service`, `auth-service`, `order-service` y `campaign-service` antes de deployar.
- Si cambia el schema `NotificationRequest`: versionar el schema en el registry antes de modificar el consumer. Los productores migran en paralelo o con compatibilidad backward.
- Si cambia el schema `NotificationEvent` emitido: validar compatibilidad backward con consumidores antes del merge.
- Si cambia la lógica de `UnsubscribeGuard`: requiere revisión legal/compliance además de análisis técnico.
- Si cambia la lógica de reintento: evaluar impacto en volumen de mensajes y posibles duplicados.
