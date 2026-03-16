# TEST_STRATEGY — notification-worker

## Cobertura mínima por tipo de cambio

| Tipo de cambio | Unit | Integración | Contrato | E2E |
|----------------|------|-------------|----------|-----|
| Lógica de reintento / backoff | Obligatoria | Recomendada | No aplica | No aplica |
| UnsubscribeGuard / preferencias | Obligatoria | Obligatoria | No aplica | No aplica |
| Integración SendGrid | Recomendada | Obligatoria (mock) | Obligatoria | Según criticidad |
| Integración Twilio | Recomendada | Obligatoria (mock) | Obligatoria | No aplica |
| Integración Firebase FCM | Recomendada | Obligatoria (mock) | No aplica | No aplica |
| Consumer Kafka / deserialización | Obligatoria | Obligatoria | Obligatoria | No aplica |
| Eventos emitidos (sent/failed/suppressed) | Obligatoria | Obligatoria | Obligatoria | No aplica |
| Renderizado de plantillas | Obligatoria | Recomendada | No aplica | No aplica |
| Horario marketing (BR-008) | Obligatoria | No aplica | No aplica | No aplica |
| Bugfix crítico en entrega | Obligatoria | Obligatoria | Según contexto | Según criticidad |

## Comandos de prueba del proyecto

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requiere Docker Compose con Kafka, PostgreSQL, mocks de providers)
docker-compose -f docker-compose.test.yml up -d
pytest tests/integration/ -v
docker-compose -f docker-compose.test.yml down

# Contract tests (valida schemas Avro contra el registry)
pytest tests/contract/ -v --avro-registry=http://localhost:8081

# E2E tests (solo para flujos críticos en ambiente staging)
pytest tests/e2e/ -v -m "critical" --env=staging
```

## Criterios mínimos de calidad

- Cobertura de unit tests: 85% mínimo en módulos `dispatcher`, `providers`, `retry`, `unsubscribe_guard`.
- Los tests de contrato Avro deben pasar antes de merge a main.
- `UnsubscribeGuard` debe tener 100% de cobertura de ramas (es un invariante de compliance).
- Las pruebas de integración con proveedores deben usar mocks certificados (WireMock para SendGrid/Twilio, Firebase emulator para FCM).
- Ningún test de integración puede usar credenciales reales de producción.

## Casos de prueba obligatorios por área

### UnsubscribeGuard
- Usuario suscrito → notificación pasa
- Usuario no suscrito → notificación suprimida, evento `notification.suppressed` emitido
- user-preferences-service no responde → notificación bloqueada (fail-safe)
- user-preferences-service retorna error 5xx → notificación bloqueada

### Lógica de reintento
- Primer intento exitoso → sin reintento
- Primer intento falla, segundo exitoso → 1 reintento, backoff de 1s
- Tres intentos fallidos → evento `notification.failed` en dead-letter
- `notification_id` duplicado → idempotencia: no se procesa, no se emite evento

### Horario marketing (BR-008)
- Marketing en horario permitido (10:00 UTC-6) → envía
- Marketing fuera de horario (22:00 UTC-6) → suprime
- Transactional fuera de horario → envía siempre (BR-003 tiene prioridad)

## Ambientes de prueba disponibles

| Ambiente | URL / Endpoint | Propósito |
|----------|---------------|-----------|
| local | localhost + Docker Compose | Desarrollo y unit/integration tests |
| staging | kafka.staging.internal:9092 | E2E y pruebas de contrato con productores reales |
| sandbox-sendgrid | api.sendgrid.com (sandbox mode) | Pruebas de integración email sin entrega real |
| sandbox-twilio | api.twilio.com (test credentials) | Pruebas de integración SMS sin entrega real |
| firebase-emulator | localhost:9099 | Pruebas de push notification sin FCM real |
