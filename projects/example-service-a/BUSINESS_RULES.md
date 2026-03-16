# BUSINESS_RULES.md — auth-service
> Servicio: auth-service (Autenticación y Gestión de Usuarios)
> Equipo responsable: Platform Security Team
> Última actualización: 2024-01-15
> Criticidad: CRÍTICO

---

## Propósito del servicio

El `auth-service` es el guardián central de identidad de la plataforma. Emite, valida e invalida tokens JWT para todos los servicios del ecosistema. Gestiona el ciclo de vida completo de usuarios: registro, verificación de email, login, cambio de contraseña, y baja. Ningún otro servicio puede autenticar usuarios directamente — toda autenticación pasa por este servicio.

---

## Reglas de negocio

### BR-001 — Expiración de JWT de acceso
**Descripción:** Los tokens de acceso (access tokens) tienen una vida útil corta para minimizar el riesgo de tokens comprometidos.
**Condición:** Todo access token emitido DEBE tener `exp` = tiempo de emisión + 15 minutos. No se permiten tokens sin expiración ni con expiración mayor a 15 minutos.
**Violación implica:** Tokens comprometidos permanecen válidos indefinidamente, exponiendo toda la plataforma.

### BR-002 — Refresh tokens y rotación
**Descripción:** Los refresh tokens se usan para obtener nuevos access tokens sin requerir login. Implementan rotación para detectar robos.
**Condición:** Al usar un refresh token, el sistema DEBE: (1) emitir un nuevo refresh token, (2) invalidar el anterior, (3) si el token ya fue usado antes (detección de reutilización), invalidar TODA la familia de tokens del usuario e iniciar flujo de alerta.
**Violación implica:** Imposibilidad de detectar refresh tokens robados; sesiones comprometidas permanecen activas.

### BR-003 — Política de contraseñas
**Descripción:** Las contraseñas deben cumplir requisitos mínimos de seguridad en el momento de creación o cambio.
**Condición:** La contraseña DEBE tener: mínimo 8 caracteres, al menos 1 mayúscula, 1 minúscula, 1 dígito, 1 carácter especial (`!@#$%^&*`). No puede ser igual a ninguna de las últimas 5 contraseñas del usuario. No puede contener el email o username del usuario.
**Violación implica:** Credenciales débiles aumentan el riesgo de compromiso de cuenta.

### BR-004 — Hash de contraseñas
**Descripción:** Las contraseñas nunca se almacenan en texto plano ni con hashes débiles.
**Condición:** Toda contraseña DEBE ser hasheada con bcrypt usando cost factor ≥ 12. SHA-*, MD5, o cualquier otro algoritmo están prohibidos para contraseñas.
**Violación implica:** Compromiso de la base de datos expone todas las contraseñas de usuarios.

### BR-005 — Rate limiting en endpoints de autenticación
**Descripción:** Limitar intentos de autenticación para prevenir ataques de fuerza bruta.
**Condición:** Por IP: máximo 10 intentos de login fallidos en 5 minutos → bloqueo de 15 minutos. Por cuenta: máximo 5 intentos fallidos consecutivos → bloqueo de cuenta por 30 minutos + email de alerta al usuario. Los contadores se almacenan en Redis con TTL.
**Violación implica:** Ataques de fuerza bruta y credential stuffing sin restricción.

### BR-006 — Verificación de email obligatoria
**Descripción:** Los usuarios no pueden autenticarse hasta verificar su email.
**Condición:** Al registrarse, se envía un email con token de verificación (válido 24 horas). El usuario tiene estado `PENDING_VERIFICATION` y NO puede hacer login hasta completar la verificación. Pasadas 24 horas sin verificar, se puede solicitar reenvío pero la cuenta permanece en `PENDING_VERIFICATION`.
**Violación implica:** Accounts con emails inválidos; imposibilidad de contactar usuarios para recuperación de cuenta.

### BR-007 — Sesiones concurrentes
**Descripción:** Control del número de sesiones activas simultáneas por usuario.
**Condición:** Un usuario puede tener máximo 5 refresh tokens activos simultáneamente (5 dispositivos/sesiones). Al crear la sesión número 6, se invalida la sesión más antigua automáticamente. El usuario puede ver y revocar sesiones individuales desde su panel.
**Violación implica:** Usuarios pueden acumular sesiones activas indefinidamente, dificultando la detección de sesiones comprometidas.

---

## Restricciones de operación

### RO-001 — Inmutabilidad del user_id
**Descripción:** El `user_id` (UUID v4) asignado al momento del registro nunca cambia, incluso si el usuario cambia su email o username.
**Excepción:** No existe excepción. Si se necesita "transferir" una cuenta, se crea una nueva cuenta y se migran los datos asociados con una historia de auditoría.

### RO-002 — Logs sin datos sensibles
**Descripción:** Los logs del servicio NUNCA deben contener contraseñas, tokens completos, ni PII sin enmascarar.
**Excepción:** Los tokens pueden logearse parcialmente para debugging: sólo los primeros 8 caracteres del token + "..." (e.g., `eyJhbGci...`).

### RO-003 — No eliminar usuarios, sólo desactivar
**Descripción:** Las cuentas de usuario no se eliminan de la base de datos. Se marcan como `DELETED` con timestamp.
**Excepción:** Solicitudes de derecho al olvido (GDPR/CCPA) ejecutadas mediante el proceso legal documentado en `/docs/gdpr-process.md`, que incluye anonimización de PII pero mantiene el registro del `user_id`.

---

## Invariantes del sistema

- **INV-001:** Todo `user_id` en la base de datos es único y no nulo. Nunca pueden existir dos usuarios con el mismo `user_id`.
- **INV-002:** Todo token JWT emitido tiene `iss` = "auth-service", `sub` = `user_id`, y `exp` en el futuro en el momento de emisión.
- **INV-003:** Ninguna contraseña en texto plano existe en la base de datos, caché, ni logs bajo ninguna circunstancia.
- **INV-004:** Todo refresh token tiene exactamente un usuario asociado y un estado (`ACTIVE`, `USED`, `REVOKED`).
- **INV-005:** Si un usuario está en estado `DELETED`, ningún token activo puede existir para ese usuario.

---

## Glosario de términos del dominio

| Término | Definición en el contexto de este servicio |
|---------|---------------------------------------------|
| Access Token | JWT de corta duración (15 min) usado para autenticar requests a otros servicios |
| Refresh Token | Token opaco de larga duración (30 días) usado exclusivamente para obtener nuevos access tokens |
| Token Family | Cadena de refresh tokens relacionados por rotación; si uno es reutilizado, toda la familia se revoca |
| User State | Estado del ciclo de vida del usuario: `PENDING_VERIFICATION`, `ACTIVE`, `LOCKED`, `DELETED` |
| Cost Factor | Parámetro de bcrypt que determina el tiempo de hash; actualmente 12 (~250ms en hardware actual) |
| Credential Stuffing | Ataque que usa listas de usuario/contraseña de otras filtraciones para intentar acceso |

---

## Responsabilidades del servicio (qué hace)

- Registro de nuevos usuarios con validación y envío de email de verificación
- Autenticación de usuarios (login) con emisión de access + refresh tokens
- Validación de tokens JWT (endpoint `/validate` para uso interno de otros servicios)
- Rotación y revocación de refresh tokens
- Cambio y recuperación de contraseñas
- Gestión de sesiones (listar y revocar sesiones activas)
- Rate limiting de endpoints críticos con Redis
- Bloqueo y desbloqueo de cuentas

## Fuera de alcance (qué NO hace)

- No gestiona permisos ni roles (eso es responsabilidad de `permissions-service`)
- No almacena perfiles de usuario extendidos (nombre, foto, etc. — eso es `user-profile-service`)
- No maneja autenticación de servicio-a-servicio (eso usa mTLS gestionado por el API Gateway)
- No implementa MFA actualmente (está en el roadmap del Q3)
