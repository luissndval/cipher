# TECHNICAL_STATE — notification-worker
> Última actualización: 2026-03-16 | Actualizado por: brain-agent (init)

## Endpoints activos

> Este servicio no expone endpoints HTTP. Es un worker orientado a eventos.

## Integraciones activas

| Sistema | Estado | Versión contrato | Último cambio | Notas |
|---------|--------|-----------------|---------------|-------|
| Kafka (entrada) | ✓ activo | NotificationRequest v3 | 2026-03-05 | Topics: notifications.dispatch, notifications.dispatch.priority |
| Kafka (salida) | ✓ activo | NotificationEvent v1 | 2026-02-20 | Topics: notifications.events, notifications.dead-letter |
| SendGrid | ✓ activo | API v3 | 2026-02-15 | Rate limit: 100 req/s |
| Twilio | ✓ activo | REST 2010-04-01 | 2026-02-15 | Solo SMS outbound |
| Firebase FCM | ✓ activo | HTTP v1 | 2026-03-01 | Tokens expiran — ver WARN-004 |
| user-preferences-service | ✓ activo | gRPC v1 | 2026-01-10 | Fail-safe: bloquea si no responde |
| template-service | ✓ activo | REST v2 | 2026-02-28 | Mantenimiento domingos 02-04 UTC |

## Modelos de datos vigentes

| Modelo | Versión | Campos clave | Último cambio |
|--------|---------|-------------|---------------|
| NotificationRequest (entrada) | v3 | notification_id, user_id, channel, type, template_id, template_version | 2026-03-05 |
| NotificationEvent (salida) | v1 | notification_id, user_id, channel, status, timestamp, reason | 2026-02-20 |
| notifications (DB) | v1.3 | notification_id, user_id, channel, status, attempts, created_at | 2026-02-01 |

## Cambios recientes con impacto

- 2026-03-05 [Kafka entrada] Migración NotificationRequest v2 → v3: eliminado campo `recipient_email`, ahora se resuelve vía user-preferences-service — productores en v2 deben migrar
- 2026-03-01 [FCM] Actualización a Firebase HTTP API v1 (legacy API deprecada) — no breaking para consumidores

## Estado de salud por módulo

| Módulo | Estado | Observaciones |
|--------|--------|---------------|
| Kafka Consumer | ✓ estable | Consumer group: notification-worker-cg |
| UnsubscribeGuard | ✓ estable | Fail-safe activo — bloquea ante timeout |
| Despacho Email (SendGrid) | ✓ estable | Monitorear 429s en picos de campaña |
| Despacho SMS (Twilio) | ✓ estable | — |
| Despacho Push (FCM) | ⚠ monitoreado | Tokens expirados ~3% del total — normal |
| Retry Engine | ✓ estable | Backoff: 1s, 4s, 16s |
| Dead-letter | ✓ estable | Tasa actual: <0.5% de mensajes |
