# BUSINESS_RULES — notification-worker
> Última actualización: 2026-03-16 | Equipo: Platform Engineering

## Propósito del servicio

notification-worker es un servicio asíncrono de procesamiento de notificaciones multicanal. Consume eventos de una cola Kafka y los despacha al canal correspondiente: correo electrónico (SendGrid), SMS (Twilio) o push notification (Firebase FCM). Es el único componente autorizado para interactuar con proveedores externos de mensajería.

## Reglas de negocio

- BR-001: Cada notificación debe tener exactamente un canal destino (email, sms, push). No se permite despacho simultáneo a múltiples canales desde un mismo evento.
- BR-002: Un usuario con estado `unsubscribed` en cualquier canal NO debe recibir notificaciones por ese canal bajo ninguna circunstancia, incluso si el evento es crítico.
- BR-003: Las notificaciones de tipo `transactional` (confirmaciones, alertas de seguridad) tienen prioridad sobre las de tipo `marketing` y no pueden ser suprimidas por preferencias de usuario.
- BR-004: El sistema debe reintentar el despacho hasta 3 veces con backoff exponencial (1s, 4s, 16s) antes de marcar la notificación como fallida.
- BR-005: Las plantillas de notificación se versionan. Un evento siempre referencia una versión específica de plantilla (`template_id` + `template_version`). Nunca se usa la última versión de forma implícita.
- BR-006: Cada notificación fallida definitivamente (agotados reintentos) debe emitir un evento `notification.failed` al topic de dead-letter para auditoría.
- BR-007: El tiempo máximo de procesamiento de un mensaje desde recepción hasta despacho es de 30 segundos. Superado este límite, el mensaje se marca como timeout y se reintenta.
- BR-008: Las notificaciones de tipo `marketing` solo pueden enviarse entre las 08:00 y las 21:00 hora local del destinatario. Si el horario no está disponible, se asume UTC-6.

## Restricciones operativas

- RO-001: El worker nunca almacena el contenido completo de la notificación. Solo registra metadatos (id, canal, estado, timestamps, intentos). El contenido proviene del renderizado de la plantilla en memoria.
- RO-002: Las credenciales de SendGrid, Twilio y Firebase se inyectan como variables de entorno. Nunca se hardcodean ni se leen de archivos locales.
- RO-003: El volumen máximo de procesamiento es de 1,000 mensajes/minuto. Por encima de ese umbral, el consumer debe pausarse y generar una alerta.
- RO-004: El worker no expone endpoints HTTP públicos. Es un proceso puramente orientado a eventos.
- RO-005: Los logs de notificaciones deben omitir PII (nombres, correos, teléfonos). Solo se loguean IDs de usuario y IDs de notificación.

## Invariantes del sistema

- Una notificación procesada exitosamente NUNCA se reenvía, incluso si el evento llega duplicado (idempotencia garantizada por `notification_id`).
- El estado de una notificación sigue una máquina de estados estricta: `pending` → `processing` → `sent` | `failed`. No hay transiciones inversas.
- El canal `unsubscribe` de un usuario es sagrado: si falla la verificación de estado de suscripción, la notificación se bloquea (fail-safe).

## Glosario del dominio

| Término | Definición |
|---------|------------|
| notification_id | UUID único por evento de notificación. Usado para idempotencia. |
| template_id | Identificador de la plantilla de contenido (ej. `welcome_email`, `otp_sms`). |
| template_version | Versión semántica de la plantilla (ej. `2.1.0`). Siempre debe ser explícita. |
| canal | Medio de despacho: `email`, `sms`, `push`. |
| transactional | Tipo de notificación disparada por acción del usuario (OTP, confirmación, alerta). |
| marketing | Tipo de notificación de comunicación masiva o campaña. |
| dead-letter | Topic Kafka donde van los mensajes que fallaron definitivamente. |
| unsubscribed | Estado de preferencia de usuario que prohíbe notificaciones en un canal. |
| backoff exponencial | Estrategia de reintento con esperas crecientes: 1s, 4s, 16s. |
