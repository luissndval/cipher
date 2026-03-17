# TEST_STRATEGY — [NOMBRE_DEL_SERVICIO]

## Cobertura mínima por tipo de cambio
| Tipo de cambio | Unit | Integración | Contrato | E2E |
|----------------|------|-------------|----------|-----|
| Lógica de negocio | Obligatoria | Recomendada | No aplica | No aplica |
| Interface HTTP | Recomendada | Obligatoria | Obligatoria | Según criticidad |
| Evento / Mensaje | Recomendada | Obligatoria | Obligatoria | No aplica |
| Config / Infra | No aplica | Obligatoria | No aplica | No aplica |
| Bugfix crítico | Obligatoria | Obligatoria | Según contexto | Según criticidad |

## Comandos de prueba
```bash
# Unit tests
[COMANDO_UNIT_TESTS]

# Integration tests
[COMANDO_INTEGRATION_TESTS]

# Contract tests
[COMANDO_CONTRACT_TESTS]
```

## Criterios mínimos de calidad
- Cobertura de unit tests: [PORCENTAJE]%
- Tests de contrato deben pasar antes de merge a main
- [CRITERIO_ESPECÍFICO]

## Ambientes de prueba
| Ambiente | URL | Propósito |
|----------|-----|-----------|
| local | localhost | Desarrollo |
| staging | [url] | QA / integración |
