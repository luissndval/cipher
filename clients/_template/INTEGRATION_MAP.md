# INTEGRATION_MAP — [client-name]
<!-- Registro compacto de contratos entre repositorios del cliente. -->
<!-- Generado automáticamente — actualizar cuando cambie un contrato entre repos. -->
<!-- Este archivo es lo que el agente lee para detectar impacto cross-repo sin leer código real. -->

## Contratos HTTP

| Repo proveedor | Endpoint | Repos consumidores | Notas |
|----------------|----------|--------------------|-------|
| <!-- takeapp-api --> | <!-- POST /orders --> | <!-- takeapp-web --> | <!-- campo delivery_fee obligatorio --> |

## Eventos / WebSocket

| Repo emisor | Canal / Evento | Repos receptores |
|-------------|----------------|------------------|
| <!-- takeapp-api --> | <!-- ws: order_status_changed --> | <!-- takeapp-web --> |

## Schemas / Tipos compartidos

| Repo origen | Schema / Tipo | Repos que lo usan |
|-------------|---------------|-------------------|
| <!-- takeapp-api --> | <!-- OrderStatus enum --> | <!-- takeapp-web --> |

## Variables de entorno compartidas

| Variable | Repos que la usan |
|----------|-------------------|
| <!-- API_BASE_URL --> | <!-- takeapp-web --> |
