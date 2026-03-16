# BUSINESS_RULES.md — [NOMBRE_DEL_SERVICIO]
> Servicio: [NOMBRE_DEL_SERVICIO]
> Equipo responsable: [EQUIPO_RESPONSABLE]
> Última actualización: [FECHA]
> Criticidad: [CRÍTICO / ALTO / MEDIO / BAJO]

---

## Propósito del servicio

[Descripción en 2-3 oraciones de qué hace este servicio, a quién sirve, y cuál es su rol en el sistema general. No usar lenguaje técnico aquí — describir desde la perspectiva del negocio.]

---

## Reglas de negocio

### BR-001 — [Nombre de la regla]
**Descripción:** [Qué debe cumplirse y por qué es importante para el negocio.]
**Condición:** [Si X entonces Y. Ser específico con valores si aplica.]
**Violación implica:** [Consecuencia concreta si se viola esta regla.]

### BR-002 — [Nombre de la regla]
**Descripción:** [Descripción de la regla.]
**Condición:** [Condición específica.]
**Violación implica:** [Consecuencia.]

### BR-003 — [Agregar tantas como sean necesarias]
**Descripción:** [...]
**Condición:** [...]
**Violación implica:** [...]

---

## Restricciones de operación

### RO-001 — [Nombre de la restricción]
**Descripción:** [Qué está prohibido o limitado en operación normal.]
**Excepción:** [Si existe alguna excepción a esta restricción, describirla aquí.]

### RO-002 — [Nombre de la restricción]
**Descripción:** [...]
**Excepción:** [...]

---

## Invariantes del sistema

> Los invariantes son condiciones que SIEMPRE deben ser verdaderas, sin excepción.

- **INV-001:** [Condición que nunca puede ser falsa, e.g., "Todo registro X debe tener un campo Y no nulo"]
- **INV-002:** [Otra condición invariante]
- **INV-003:** [Otra condición invariante]

---

## Glosario de términos del dominio

| Término | Definición en el contexto de este servicio |
|---------|---------------------------------------------|
| [Término 1] | [Definición específica — puede diferir de la definición general de la empresa] |
| [Término 2] | [Definición específica] |
| [Término 3] | [Definición específica] |

---

## Responsabilidades del servicio (qué hace)

- [Responsabilidad 1]
- [Responsabilidad 2]
- [Responsabilidad 3]

## Fuera de alcance (qué NO hace)

- [Lo que explícitamente este servicio no maneja, aunque podría parecer relacionado]
- [Otra cosa fuera de alcance]
