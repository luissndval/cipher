# RISK_MATRIX — [NOMBRE_DEL_SERVICIO]

## Niveles de riesgo
| Nivel | Criterio | Acción obligatoria |
|-------|----------|--------------------|
| CRÍTICO | Interface pública o evento compartido | Análisis completo + notificar consumidores |
| ALTO | Lógica de negocio core | Análisis de impacto + prueba de integración |
| MEDIO | Componente con dependencia externa | Revisión + prueba unitaria |
| BAJO | Componente aislado | Prueba unitaria recomendada |

## Componentes y nivel de riesgo
| Componente | Nivel | Razón | Revisar también |
|------------|-------|-------|-----------------|
| [componente] | ALTO | [razón] | [qué revisar] |

## Reglas de escalamiento
- CRÍTICO: notificar equipos consumidores antes de deployar
- Cambio de contrato: versionar antes de modificar
- Cambio de evento: validar compatibilidad backward antes de merge
