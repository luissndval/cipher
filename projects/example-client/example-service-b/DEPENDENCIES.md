# DEPENDENCIES — notification-worker

## Dependencias de salida (lo que este servicio CONSUME)

| Destino | Tipo | Protocolo | Contrato | Versión | Campos críticos | SLA |
|---------|------|-----------|----------|---------|-----------------|-----|
| SendGrid API | Sincrónico | HTTPS REST | `POST /v3/mail/send` | v3 | `to`, `from`, `subject`, `content`, `template_id` | timeout 10s, retry hasta 3x |
| Twilio API | Sincrónico | HTTPS REST | `POST /2010-04-01/Accounts/{SID}/Messages` | 2010-04-01 | `To`, `From`, `Body` | timeout 8s, retry hasta 3x |
| Firebase FCM | Sincrónico | HTTPS REST | `POST /fcm/send` | v1 | `token`, `notification.title`, `notification.body`, `data` | timeout 5s, retry hasta 3x |
| notification-db | Sincrónico | PostgreSQL | Schema `notifications` | 1.3 | `notification_id`, `user_id`, `channel`, `status`, `attempts` | timeout 3s |
| user-preferences-service | Sincrónico | gRPC | `PreferencesService/GetUserPreferences` | v1 | `user_id`, `channel_preferences[].subscribed` | timeout 2s, sin retry (fail-safe bloquea) |
| template-service | Sincrónico | HTTP REST | `GET /templates/{id}/versions/{version}/render` | v2 | `template_id`, `template_version`, `variables` | timeout 5s, retry hasta 2x |

## Dependencias de entrada (quién CONSUME este servicio)

| Origen | Tipo | Protocolo | Contrato | Versión |
|--------|------|-----------|----------|---------|
| Kafka topic `notifications.dispatch` | Asincrónico | Kafka | Avro schema `NotificationRequest` | v3 |
| Kafka topic `notifications.dispatch.priority` | Asincrónico | Kafka | Avro schema `NotificationRequest` | v3 |

> Este servicio no expone endpoints HTTP. Solo consume de Kafka.

## Eventos que EMITE

| Evento | Topic/Queue | Schema | Consumidores conocidos |
|--------|-------------|--------|------------------------|
| `notification.sent` | `notifications.events` | Avro `NotificationEvent` v1 | analytics-service, audit-service |
| `notification.failed` | `notifications.dead-letter` | Avro `NotificationEvent` v1 | alert-service, audit-service |
| `notification.suppressed` | `notifications.events` | Avro `NotificationEvent` v1 | analytics-service |

## Eventos que CONSUME

| Evento | Topic/Queue | Schema | Productor |
|--------|-------------|--------|-----------|
| `NotificationRequest` | `notifications.dispatch` | Avro `NotificationRequest` v3 | auth-service, order-service, campaign-service |
| `NotificationRequest` | `notifications.dispatch.priority` | Avro `NotificationRequest` v3 | auth-service (solo OTPs y alertas de seguridad) |

## Schema del evento de entrada (NotificationRequest v3)

```json
{
  "notification_id": "uuid-v4",
  "user_id": "string",
  "channel": "email | sms | push",
  "type": "transactional | marketing",
  "template_id": "string",
  "template_version": "semver",
  "variables": { "key": "value" },
  "scheduled_at": "ISO8601 | null",
  "idempotency_key": "string"
}
```

## Advertencias críticas de dependencias

- WARN-001: Si `user-preferences-service` no responde, la notificación se BLOQUEA (no se envía). Nunca asumir que el usuario está suscrito ante una falla de preferencias.
- WARN-002: SendGrid puede retornar 429 (rate limit). El worker debe respetar el header `Retry-After` y no reintentar antes de ese tiempo.
- WARN-003: El schema Avro v3 de `NotificationRequest` eliminó el campo `recipient_email` presente en v2. Cualquier productor en v2 debe migrarse antes de deployar este worker.
- WARN-004: Firebase FCM tokens expiran. Si FCM retorna `registration-token-not-registered`, el worker debe emitir un evento `notification.failed` con razón `token_expired` y NO reintentar.
- WARN-005: `template-service` tiene una ventana de mantenimiento los domingos de 02:00–04:00 UTC. Mensajes en ese rango pueden fallar en el paso de renderizado.
