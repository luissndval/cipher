# IMPACT_RULES — notification-worker

## Reglas de evaluación de impacto

- IR-001: Si se modifica el consumer de Kafka (topic, consumer group, deserializer) → revisar todos los productores en DEPENDENCIES.md y validar compatibilidad de schema en el registry.
- IR-002: Si se modifica el schema del evento de entrada `NotificationRequest` → versionar en Avro registry y coordinar migración con auth-service, order-service y campaign-service.
- IR-003: Si se modifica el schema de eventos emitidos (`notification.sent`, `notification.failed`, `notification.suppressed`) → notificar a analytics-service y audit-service; validar compatibilidad backward.
- IR-004: Si se modifica `UnsubscribeGuard` o la lógica de verificación de preferencias → revisión obligatoria con el equipo legal/compliance. Una falla es un incidente regulatorio.
- IR-005: Si se modifica la lógica de reintento (tiempos, número de intentos) → evaluar impacto en SLA de entrega, posibilidad de duplicados, y carga sobre proveedores externos (SendGrid, Twilio).
- IR-006: Si se modifica la integración con un proveedor externo (SendGrid, Twilio, Firebase) → actualizar el timeout y la estrategia de error en DEPENDENCIES.md; revisar WARN correspondiente.
- IR-007: Si se agrega un nuevo canal de notificación → debe actualizarse: `NotificationRequest` schema, `UnsubscribeGuard`, `BUSINESS_RULES.md`, y `RISK_MATRIX.md`.
- IR-008: Si se modifica el manejo de dead-letter → revisar que `audit-service` y `alert-service` siguen recibiendo los eventos de falla correctamente.
- IR-009: Si se modifica la lógica de horario de notificaciones marketing (BR-008) → revisar manejo de timezone y asegurarse de que `transactional` nunca queda bloqueado.
- IR-010: Si se elimina o renombra un campo en cualquier evento Kafka → es breaking change; requiere versionar el schema antes de merge.

## Checklist de preguntas obligatorias antes de modificar

1. ¿El cambio afecta la recepción de mensajes Kafka o los eventos emitidos? (→ IR-001, IR-002, IR-003)
2. ¿El cambio toca la lógica de verificación de suscripción? (→ IR-004, BR-002)
3. ¿El cambio modifica cuándo o cuántas veces se intenta el despacho? (→ IR-005, BR-004)
4. ¿El cambio toca la integración con SendGrid, Twilio o Firebase? (→ IR-006, DEPENDENCIES.md)
5. ¿El cambio introduce un nuevo canal o tipo de notificación? (→ IR-007)
6. ¿Existe alguna regla en BUSINESS_RULES.md que restrinja este cambio? (→ BR-001 a BR-008)
7. ¿El cambio puede causar que una notificación se envíe dos veces? (→ idempotencia, `notification_id`)

## Áreas de revisión por tipo de cambio

| Tipo de cambio | Áreas a revisar | Equipos a notificar |
|----------------|-----------------|---------------------|
| Schema Kafka entrada | Avro registry, productores en DEPENDENCIES.md | auth-service, order-service, campaign-service |
| Schema Kafka salida | Avro registry, consumidores de `notifications.events` | analytics-service, audit-service |
| Lógica de suscripción | user-preferences-service contrato, BR-002, IR-004 | Legal/Compliance, Platform Engineering |
| Integración SendGrid | Campos requeridos, rate limits, WARN-002 | Platform Engineering |
| Integración Twilio | Campos requeridos, manejo de errores, WARN-004 | Platform Engineering, auth-service |
| Integración Firebase FCM | Token handling, WARN-004 | Platform Engineering, mobile team |
| Lógica de reintento | BR-004, dead-letter, idempotencia | Platform Engineering |
| Horario marketing | BR-008, timezone handling | Marketing team |
| Variables de entorno | RO-002, todos los canales afectados | DevOps/Infra |
