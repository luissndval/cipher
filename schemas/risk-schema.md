# risk-schema — Formato canónico de la matriz de riesgo

## Propósito

Este schema define los criterios para asignar niveles de riesgo a componentes en los archivos `RISK_MATRIX.md`. Su objetivo es que el agente pueda determinar de forma consistente qué nivel de precaución requiere un cambio, sin depender de criterios subjetivos.

---

## Criterios de asignación de nivel

### CRÍTICO
Se asigna cuando el componente cumple **al menos una** de estas condiciones:
- Es una interface pública consumida por servicios externos a este repositorio (endpoint HTTP, topic Kafka, schema gRPC).
- Es un evento compartido con múltiples consumidores conocidos.
- Su falla tiene consecuencias legales, regulatorias o de compliance (ej: enviar mensajes a usuarios no suscritos, exponer datos personales, procesar pagos incorrectos).
- Es el punto de entrada o salida principal del sistema (API gateway, consumer principal de cola).

**Acción mínima obligatoria:** Análisis completo de impacto + notificación a todos los equipos consumidores + prueba de contrato antes de merge.

### ALTO
Se asigna cuando el componente cumple **al menos una** de estas condiciones:
- Implementa lógica de negocio core que afecta directamente el resultado observable por el usuario final.
- Tiene dependencias directas sobre múltiples servicios externos.
- Su falla impacta el SLA o la disponibilidad del servicio completo.
- Contiene reglas de seguridad o autenticación internas al servicio.

**Acción mínima obligatoria:** Análisis de impacto documentado + prueba de integración.

### MEDIO
Se asigna cuando el componente cumple **al menos una** de estas condiciones:
- Es un componente auxiliar con una sola dependencia externa.
- Implementa una regla de negocio secundaria que no afecta el flujo principal.
- Su falla degrada funcionalidad pero no la interrumpe completamente.
- Es un adaptador o transformer entre dos sistemas.

**Acción mínima obligatoria:** Revisión de reglas de impacto relevantes + prueba unitaria.

### BAJO
Se asigna cuando el componente cumple **todas** estas condiciones:
- No tiene dependencias externas.
- Su falla no interrumpe ningún flujo de negocio (solo afecta observabilidad, logging, métricas).
- Es completamente aislado y reemplazable sin impacto en otros módulos.

**Acción mínima recomendada:** Prueba unitaria básica.

---

## Árbol de decisión para determinar el nivel correcto

```
¿El componente expone o consume una interface pública (HTTP, Kafka, gRPC) con consumidores externos?
├─ SÍ → ¿Tiene consecuencias legales/regulatorias si falla?
│        ├─ SÍ → CRÍTICO
│        └─ NO → CRÍTICO (por ser interface pública compartida)
└─ NO → ¿Implementa lógica de negocio core o afecta el SLA del servicio?
         ├─ SÍ → ALTO
         └─ NO → ¿Tiene al menos una dependencia externa y su falla degrada el servicio?
                  ├─ SÍ → MEDIO
                  └─ NO → BAJO
```

---

## Ejemplos de componentes por nivel con justificación

### Ejemplos CRÍTICO

| Componente | Servicio | Justificación |
|------------|---------|---------------|
| `AuthController` (endpoints `/login`, `/token`) | auth-service | Interface HTTP pública consumida por todos los clientes. Cambios rompen contratos de múltiples consumidores. |
| `PaymentEventEmitter` (topic `payments.completed`) | payment-service | Evento consumido por order-service, analytics-service, finance-service. Un cambio de schema rompe múltiples sistemas. |
| `UnsubscribeGuard` | notification-worker | Su falla puede causar envíos a usuarios no suscritos, violando regulaciones de privacidad (GDPR, CAN-SPAM). |
| `KafkaConsumer` (entrada principal) | notification-worker | Punto de entrada de todos los mensajes. Cambios afectan a todos los productores upstream. |

### Ejemplos ALTO

| Componente | Servicio | Justificación |
|------------|---------|---------------|
| `PasswordHasher` (bcrypt logic) | auth-service | Lógica de seguridad core. Un error compromete todas las contraseñas almacenadas. |
| `RetryEngine` (backoff + dead-letter) | notification-worker | Controla SLA de entrega. Un bug puede causar duplicados o pérdida de mensajes. |
| `FraudEvaluator` (integración con fraud-detector) | payment-service | Dependencia externa crítica para aprobar/rechazar pagos. Su falla impacta revenue. |
| `SessionManager` (Redis) | auth-service | Maneja todas las sesiones activas. Un bug puede invalidar sesiones o crear vulnerabilidades. |

### Ejemplos MEDIO

| Componente | Servicio | Justificación |
|------------|---------|---------------|
| `MarketingScheduler` (horario BR-008) | notification-worker | Solo afecta mensajes de marketing. Una falla no interrumpe notificaciones transaccionales. |
| `TemplateRenderer` | notification-worker | Falla degrada la presentación pero no bloquea el sistema (puede usar fallback de texto plano). |
| `AuditLogger` | auth-service | Afecta observabilidad y auditoría, pero no interrumpe el flujo de autenticación. |
| `RateLimiter` (Redis) | auth-service | Su ausencia temporal no rompe la funcionalidad core, pero expone el sistema a ataques. |

### Ejemplos BAJO

| Componente | Servicio | Justificación |
|------------|---------|---------------|
| `HealthCheckEndpoint` | cualquier servicio | No afecta ningún flujo de negocio. Solo usado por orquestadores de infraestructura. |
| `MetricsCollector` (Prometheus) | cualquier servicio | No tiene dependencias externas. Su falla solo impacta dashboards, no el servicio. |
| `RequestIdMiddleware` | cualquier servicio | Añade headers de trazabilidad. Su ausencia no interrumpe ningún flujo. |

---

## Qué hacer cuando no se puede determinar el nivel

Si el nivel de riesgo no puede determinarse con certeza, seguir estos pasos en orden:

1. **Escalar al usuario antes de proceder.** Nunca asumir nivel bajo por omisión.
2. **Asumir el nivel superior** entre los candidatos posibles hasta tener más información.
3. **Documentar la incertidumbre** explícitamente en la propuesta de cambio: `Nivel de riesgo: ALTO (pendiente de validar si el componente X tiene consumidores externos)`.
4. **Consultar DEPENDENCIES.md** para verificar si el componente tiene consumidores o dependencias no evidentes.
5. **Si el componente es nuevo** y no hay información histórica: asignar MEDIO como punto de partida y documentarlo.

> Regla de oro: ante la duda, escalar. El costo de una pregunta es siempre menor al costo de un incidente.
