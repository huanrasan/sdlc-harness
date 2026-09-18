# Glosario

> English version: [../en/glossary.md](../en/glossary.md)
> Los términos también están disponibles en la terminal: `sdlc explain <término>`.

## El ciclo central

| Término | Significado |
|---|---|
| **Arnés (harness)** | Todo lo que rodea al agente para que su resultado sea confiable: guías que lee antes de actuar, sensores que verifican después, compuertas que detienen el trabajo sin evidencia y aprobaciones humanas. |
| **Guía (feedforward)** | Información que el agente lee antes de actuar: `AGENTS.md`, skills, memoria y plantillas. Aumenta la probabilidad de acertar la primera vez. |
| **Sensor (feedback)** | Una verificación posterior: tests, linters, escáneres, sensores de historia (test-first y tests debilitados), reglas de capas y compatibilidad de contratos. |
| **Compuerta (gate)** | La condición para pasar a la fase siguiente: la evidencia requerida existe, es consistente y, cuando el perfil lo indica, está aprobada por una persona. Corre en `sdlc check`, en los git hooks y en CI. |
| **Control computacional vs inferencial** | Los computacionales son deterministas y baratos (un test, un linter). Los inferenciales usan un modelo (un agente revisor) y son más lentos y no deterministas. El arnés prefiere los computacionales para todo lo que deba bloquear. |

## Trabajo y evidencia

| Término | Significado |
|---|---|
| **Change record** | Una carpeta `docs/changes/<id>/` con `change.toml` y los artefactos de las fases completadas. Es el sistema de registro de un cambio. |
| **Fase** | `discover, spec, design, plan, implement, verify, review, release, operate, done`. Cada una produce evidencia y termina en una compuerta. |
| **Tipo de cambio** | `fix`, `feature`, `architecture`, `retirement`. Define qué artefactos exige el perfil. |
| **Riesgo** | `low`, `medium`, `high`, declarado por cambio. Eleva cuánta evidencia y cuántas aprobaciones se exigen. |
| **Scope** | Una etiqueta del cambio (`ui`, `api`, `data`, `personal-data`, `infra`, `ai`) que activa artefactos condicionales como `ux.md`, `data.md`, `cost.md` o `ai-risk.md`. |
| **Artefacto** | Un archivo Markdown del change record (`spec.md`, `design.md`, ...) con plantilla y verificaciones semánticas. |
| **Compuerta semántica** | Una verificación sobre el significado de la evidencia, no solo su presencia: cada criterio trazado a un test, cada amenaza con un control, cada métrica medida. |
| **Criterio de aceptación (`AC-n`)** | Un enunciado verificable del comportamiento esperado, escrito como Given/When/Then o EARS. |
| **Amenaza (`T-n`)** | Un riesgo identificado en el modelo de amenazas, que debe tener un control verificable. |
| **Evidencia** | Salida de escáneres en formatos estándar (hallazgos SARIF, SBOM CycloneDX) en `sdlc-evidence/`, más los artefactos. |
| **Log de auditoría** | `audit.jsonl` por cambio: creación, aprobaciones, transiciones de fase e intentos bloqueados, encadenados por hash y solo agregables. |

## Personas y autoridad

| Término | Significado |
|---|---|
| **Roster** | `.harness/roster.toml`: quién ocupa cada rol, qué roles pueden aprobar qué y las entradas extra de CODEOWNERS. |
| **Rol** | `product-owner`, `tech-lead`, `architect`, `security`, `release-manager`, `sre`, `platform`, `ux-lead`, `data-steward`, `finops`. Una persona puede ocupar varios. |
| **Matriz de autoridad** | La tabla `[authority]` que asocia cada artefacto con los roles que pueden aprobarlo. |
| **Recibo de aprobación** | Una entrada en `approvals.toml` con el SHA-256 del artefacto aprobado, la persona que aprueba y su rol. Editar el artefacto lo invalida. |
| **Separación de funciones** | La regla de que quien aprueba no puede ser autor del cambio; se verifica en CI contra los datos de la plataforma. Se desactiva cuando hay una sola persona manteniendo el repositorio, y entonces una firma de commit verificada reemplaza la revisión en la plataforma. |
| **Enmienda** | Volver a aprobar un artefacto después de leer el diff desde la última aprobación (`sdlc amend`). Existe para que proteger un recibo nunca sea motivo para dejar información verdadera fuera de un documento. |
| **Propuesta** | Una desviación o excepción escrita por un agente con el aprobador vacío: queda registrada y visible en `sdlc check`, pero no suprime nada hasta que la aprueba una persona con un rol autorizado. |
| **Resultado abierto (`blocked` / `pending`)** | Un resultado de verificación que nombra dueño y motivo para un criterio que honestamente todavía no se puede verificar. El registro sigue siendo cierto; la compuerta sigue en rojo. |
| **CODEOWNERS** | El archivo de la plataforma, generado desde el roster, que fuerza la revisión de las personas correctas. |

## Configuración y política

| Término | Significado |
|---|---|
| **Perfil** | `lite`, `standard`, `regulated` o uno propio: las reglas que definen qué artefactos y aprobaciones aplican según tipo, riesgo y scope, además de los niveles de sensores y la evidencia requerida. |
| **Regla** | Una entrada del perfil: artefacto, fase que lo produce, tipos aplicables, riesgo mínimo, scopes opcionales y si exige recibo de aprobación. |
| **Política de organización** | `policy.toml` en un repositorio compartido, copiado a `.harness/org/` con un lock de hashes. Sus mínimos de `[require]` no pueden debilitarse desde un proyecto. |
| **Desviación** | Una excepción aprobada y con vencimiento a un mínimo de la política de organización, en `.harness/deviations.toml`. |
| **Excepción** | Una excepción con vencimiento y aprobada por seguridad a un hallazgo de escáner o a una licencia prohibida, en `.harness/exceptions.toml`. |
| **Waiver** | Un trailer del commit (`TDD-Waiver:`, `Test-Waiver:`) con el que una persona justifica una excepción a los sensores de historia; queda registrado, no oculto. |

## Distribución e integración

| Término | Significado |
|---|---|
| **`AGENTS.md`** | El archivo del estándar abierto que leen todos los agentes soportados: mapa del proyecto, flujo y reglas no negociables. |
| **Skill (`SKILL.md`)** | Conocimiento condicional en formato Agent Skills, que se carga solo cuando su "use when" coincide. Hay una por fase o preocupación. |
| **Adaptador** | El archivo o enlace generado que hace visibles las guías canónicas a un agente (`CLAUDE.md`, `GEMINI.md`, `.claude/skills`), producido por `sdlc sync`. |
| **CLI incluida en el repo** | `.harness/sdlc.pyz`: el arnés mismo, commiteado al repositorio para que los hooks y la CI lo ejecuten sin instalar nada y sin red. |
| **Manifiesto** | `.harness/manifest.toml`: hashes de los archivos del arnés tal como se instalaron; `sdlc upgrade` los usa para conservar tus personalizaciones. |
| **Servidor MCP** | `sdlc mcp`: expone herramientas del arnés de solo lectura (memoria, status, check, trace, explain) a cualquier cliente MCP. |
| **Memoria** | Entradas Markdown curadas en `docs/memory/` (decisiones, lecciones, convenciones, errores conocidos) que los agentes consultan antes de empezar. |

## Métricas

| Término | Significado |
|---|---|
| **Reporte de trazabilidad** | `sdlc report trace`: criterio → test planificado → resultado de verificación → aprobación → commits, con las brechas listadas. |
| **Reporte de flujo** | `sdlc report flow`: lead time, horas por fase, bloqueos de compuerta, esperas de aprobación y proporción de cambios asistidos por IA. |
| **Reporte DORA** | `sdlc report dora`: frecuencia de despliegue, lead time, tasa de fallos, tiempo de recuperación y tasa de retrabajo, usando los tags de release como aproximación de despliegue. |
