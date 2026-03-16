# DEPENDENCIES.md — [NOMBRE_DEL_SERVICIO]
> Última actualización: [FECHA]
> Ver `schemas/dependency-schema.md` para el formato completo de cada campo.

---

## Dependencias de salida (este servicio llama a / escribe en)

| Destino | Tipo | Protocolo | Contrato | Versión | Campos críticos | SLA esperado |
|---------|------|-----------|----------|---------|-----------------|--------------|
| [Servicio/DB destino] | [sync/async] | [HTTP/gRPC/SQL/AMQP] | [OpenAPI/GraphQL/Schema] | [v1/v2] | [campo1, campo2] | [p99 < Xms] |
| [Otro destino] | [sync/async] | [protocolo] | [contrato] | [versión] | [campos] | [SLA] |

### Notas de dependencias de salida

- **[Destino 1]:** [Contexto adicional importante, e.g., "Si este servicio no responde en 500ms, el flujo de [X] falla silenciosamente. Ver circuit breaker en config/resilience.yaml"]
- **[Destino 2]:** [Nota relevante]

---

## Dependencias de entrada (quién llama a / lee de este servicio)

| Origen | Tipo | Protocolo | Contrato que expone | Campos críticos que consume |
|--------|------|-----------|---------------------|-----------------------------|
| [Servicio/cliente origen] | [sync/async] | [HTTP/gRPC/AMQP] | [endpoint o schema] | [campos que el origen necesita de la respuesta] |
| [Otro origen] | [sync/async] | [protocolo] | [contrato] | [campos] |

### Notas de dependencias de entrada

- **[Origen 1]:** [Qué pasa si este servicio falla desde la perspectiva del origen]
- **[Origen 2]:** [Nota relevante]

---

## Eventos que EMITE (mensajería/eventos)

| Nombre del evento | Topic/Queue | Schema | Consumidores conocidos | Trigger |
|-------------------|-------------|--------|------------------------|---------|
| [NombreEvento] | [topic.name] | [schema.json / Avro / Protobuf] | [Servicio A, Servicio B] | [Qué acción del negocio lo dispara] |
| [OtroEvento] | [topic.name] | [schema] | [consumidores] | [trigger] |

---

## Eventos que CONSUME (mensajería/eventos)

| Nombre del evento | Topic/Queue | Schema | Productor | Acción que desencadena |
|-------------------|-------------|--------|-----------|------------------------|
| [NombreEvento] | [topic.name] | [schema] | [Servicio X] | [Qué hace este servicio cuando recibe el evento] |
| [OtroEvento] | [topic.name] | [schema] | [productor] | [acción] |

---

## Advertencias críticas

> Estas son las situaciones de dependencia que más frecuentemente causan incidentes. Leer antes de cualquier cambio.

1. **[Advertencia 1]:** [Descripción detallada del riesgo. E.g., "El campo `user_id` en la respuesta de [ServicioX] es un UUID v4, pero nuestros logs lo truncan a 32 chars. No cambiar el formato de log sin actualizar los dashboards de monitoreo."]

2. **[Advertencia 2]:** [Descripción del riesgo.]

3. **[Advertencia 3]:** [Descripción del riesgo.]
