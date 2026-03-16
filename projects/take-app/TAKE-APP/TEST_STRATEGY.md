# TEST_STRATEGY.md — [NOMBRE_DEL_SERVICIO]
> Define la cobertura mínima requerida y los comandos para ejecutar pruebas.
> Última actualización: [FECHA]

---

## Cobertura mínima requerida

| Tipo de prueba | Cobertura mínima | Obligatoria antes de | Herramienta |
|----------------|-----------------|----------------------|-------------|
| Unitaria | [X]% líneas | Merge a cualquier rama | [pytest / jest / go test / etc.] |
| Integración | Casos críticos cubiertos | Merge a main/master | [herramienta] |
| Contrato | Todos los consumers cubiertos | Cambio de API o schema | [Pact / schemathesis / etc.] |
| E2E | Flujos de negocio principales | Release a producción | [herramienta] |
| Regresión | Suite completa verde | Deploy a staging | [herramienta] |

---

## Comandos de prueba

```bash
# Pruebas unitarias
[COMANDO_PRUEBAS_UNITARIAS]
# Ejemplo: pytest tests/unit/ -v --cov=src --cov-report=term-missing

# Pruebas de integración
[COMANDO_PRUEBAS_INTEGRACION]
# Ejemplo: pytest tests/integration/ -v --timeout=60

# Pruebas de contrato
[COMANDO_PRUEBAS_CONTRATO]
# Ejemplo: pact-verifier --provider-base-url=http://localhost:8080

# Pruebas E2E
[COMANDO_PRUEBAS_E2E]
# Ejemplo: pytest tests/e2e/ -v -m "smoke"

# Suite completa
[COMANDO_SUITE_COMPLETA]
# Ejemplo: make test-all
```

---

## Criterios mínimos antes de dar por terminada una tarea

Una tarea se considera completa sólo cuando:

- [ ] Las pruebas unitarias del código nuevo/modificado pasan al 100%
- [ ] La cobertura total no disminuyó respecto al estado anterior
- [ ] Las pruebas de integración de los flujos afectados pasan
- [ ] Si se modificó una interfaz externa: las pruebas de contrato pasan
- [ ] No hay regresiones en la suite existente
- [ ] Los logs del servicio no muestran errores nuevos durante las pruebas de integración

---

## Ambientes de prueba

| Ambiente | URL / Conexión | Cuándo usarlo | Datos de prueba |
|----------|----------------|---------------|-----------------|
| Local | [localhost:XXXX] | Desarrollo y pruebas unitarias | [Fixtures en tests/fixtures/] |
| Development | [URL de dev] | Pruebas de integración | [Seed script: scripts/seed-dev.sh] |
| Staging | [URL de staging] | Pruebas E2E y regresión | [Datos de staging — no usar datos reales] |
| Production | — | NUNCA ejecutar pruebas | — |

---

## Pruebas críticas (no omitir bajo ninguna circunstancia)

> Estas pruebas cubren los invariantes y reglas de negocio más importantes. Si fallan, el cambio NO puede desplegarse.

1. **[Nombre de prueba crítica 1]** — `[ruta/al/test]` — Verifica: [qué invariante o regla cubre]
2. **[Nombre de prueba crítica 2]** — `[ruta/al/test]` — Verifica: [qué cubre]
3. **[Nombre de prueba crítica 3]** — `[ruta/al/test]` — Verifica: [qué cubre]

---

## Datos de prueba y fixtures

| Dataset | Ubicación | Descripción |
|---------|-----------|-------------|
| [Nombre del dataset] | `[tests/fixtures/nombre.json]` | [Qué escenario cubre] |
| [Otro dataset] | `[tests/fixtures/otro.json]` | [Escenario] |

**Advertencia:** [Descripción de cualquier dato de prueba sensible y cómo manejarlo. E.g., "Los fixtures de prueba no deben contener datos reales de usuarios. Usar el script generate-fixtures.py para regenerarlos."]
