# dependency-schema — Formato canónico para declarar dependencias

## Propósito

Este schema define el formato estándar para documentar dependencias en los archivos `DEPENDENCIES.md` de cada proyecto. El objetivo es que un agente de IA pueda parsear el archivo y determinar con precisión qué sistemas se ven afectados ante un cambio.

---

## Campos de la tabla de dependencias de salida

| Campo | Descripción | Valores válidos | Obligatorio |
|-------|-------------|-----------------|-------------|
| `Destino` | Nombre del servicio, base de datos o sistema externo que se consume | Nombre del servicio o sistema | Sí |
| `Tipo` | Naturaleza de la comunicación | `Sincrónico` / `Asincrónico` | Sí |
| `Protocolo` | Protocolo de transporte o mensajería | `HTTP REST`, `gRPC`, `Kafka`, `AMQP`, `PostgreSQL`, `Redis`, `S3`, `SMTP` | Sí |
| `Contrato` | Ruta o nombre del endpoint/topic/queue/schema que se usa | Path exacto, nombre de topic o schema | Sí |
| `Versión` | Versión del contrato consumido | Semver (`v1`, `v2.1`), fecha (`2010-04-01`) o `N/A` | Sí |
| `Campos críticos` | Campos del request/evento que son mandatorios y cuyo cambio es breaking | Lista de nombres de campo separados por coma | Sí |
| `SLA` | Expectativa de latencia y estrategia ante falla | `timeout Xs`, `retry hasta Nx`, `circuit breaker`, `fire-and-forget` | Sí |

## Campos de la tabla de dependencias de entrada

| Campo | Descripción |
|-------|-------------|
| `Origen` | Nombre del servicio que llama a este servicio |
| `Tipo` | `Sincrónico` / `Asincrónico` |
| `Protocolo` | Protocolo usado |
| `Contrato` | Endpoint, topic o schema expuesto |
| `Versión` | Versión del contrato que el origen consume |

---

## Ejemplo completo con valores reales

```markdown
## Dependencias de salida (lo que este servicio CONSUME)

| Destino | Tipo | Protocolo | Contrato | Versión | Campos críticos | SLA |
|---------|------|-----------|----------|---------|-----------------|-----|
| inventory-service | Sincrónico | HTTP REST | `GET /inventory/items/{sku}/availability` | v2 | `sku`, `warehouse_id` | timeout 3s, retry hasta 2x |
| payments-db | Sincrónico | PostgreSQL | Schema `payments`, tabla `transactions` | 4.2 | `transaction_id`, `amount`, `currency`, `status` | timeout 5s |
| event-bus | Asincrónico | Kafka | Topic `payments.completed` | v1 | `payment_id`, `order_id`, `amount`, `timestamp` | fire-and-forget, at-least-once |
| fraud-detector | Sincrónico | gRPC | `FraudService/EvaluateTransaction` | v3 | `transaction_id`, `user_id`, `amount`, `merchant_id` | timeout 2s, sin retry (falla = rechazar) |
| exchange-rates-api | Sincrónico | HTTP REST | `GET /rates/{currency}` | v1 | `currency`, `base` | timeout 1s, retry hasta 3x, fallback a caché |
```

---

## Reglas para elegir Tipo (Sincrónico vs Asincrónico)

**Usar Sincrónico cuando:**
- El resultado de la llamada es necesario para continuar el flujo actual.
- Se necesita una respuesta inmediata (validación, consulta de datos en tiempo real).
- El cliente debe saber si la operación tuvo éxito o falló antes de continuar.

**Usar Asincrónico cuando:**
- El resultado no bloquea el flujo actual.
- La operación es de notificación, procesamiento en background o propagación de eventos.
- Se acepta eventual consistency.
- El productor no necesita conocer a los consumidores.

---

## Reglas para elegir Protocolo

| Protocolo | Cuándo usarlo |
|-----------|---------------|
| `HTTP REST` | APIs externas, servicios con contrato OpenAPI, integraciones con terceros |
| `gRPC` | Comunicación interna de baja latencia, streaming, contratos con Protobuf |
| `Kafka` | Eventos de dominio, comunicación asincrónica desacoplada, alto volumen |
| `AMQP` | Colas de trabajo, tareas en background, cuando se necesita acknowledgment explícito |
| `PostgreSQL` | Acceso directo a base de datos relacional (solo desde el servicio dueño del schema) |
| `Redis` | Cache compartido, pub/sub, rate limiting, sesiones distribuidas |
| `S3` | Transferencia de archivos, almacenamiento de objetos, exports/imports |
| `SMTP` | Envío directo de correo (preferir HTTP REST a un proveedor de email cuando sea posible) |

---

## Guía para identificar "campos críticos"

Un campo es **crítico** si cumple al menos una de estas condiciones:

1. **Es un identificador único** que correlaciona entidades entre sistemas (`user_id`, `order_id`, `transaction_id`). Su ausencia o cambio de tipo rompe la trazabilidad.
2. **Es un campo de control de flujo** que determina el comportamiento del receptor (`status`, `type`, `channel`, `action`). Su cambio de valores válidos es un breaking change.
3. **Es un campo financiero o de compliance** (`amount`, `currency`, `tax_id`). Cambios de precisión, tipo o formato son breaking changes.
4. **Es un campo de contrato de interface** que el receptor usa para enrutar, filtrar o agregar. Si desaparece o se renombra, el receptor falla silenciosamente.
5. **Es un timestamp de ordenamiento** (`created_at`, `event_time`). Cambios de formato o zona horaria afectan procesamiento downstream.

**NO son campos críticos:** campos de logging, metadatos opcionales de auditoría, campos de UI, comentarios libres.

---

## Advertencias (sección WARN)

Cada dependencia que tenga un comportamiento no obvio, una limitación conocida o un riesgo de integración debe documentarse como:

```
- WARN-NNN: [Descripción del riesgo, limitación o comportamiento especial]
```

Ejemplos:
- `WARN-001: Si X no responde, el flujo debe bloquearse (fail-safe), no asumir estado por defecto`
- `WARN-002: El endpoint Y retorna 200 incluso en error; revisar el campo 'success' en el body`
- `WARN-003: El campo Z fue eliminado en v3; los consumidores en v2 deben migrar antes del deploy`
