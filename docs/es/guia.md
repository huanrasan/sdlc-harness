# Guía de uso

> English version: [../en/guide.md](../en/guide.md)

## Requisitos

- Git y Python ≥ 3.11 (solo biblioteca estándar). En Windows: WSL, Git Bash o `--mode copy`.
- Cualquier agente de programación que lea `AGENTS.md`. Las skills funcionan de forma nativa o mediante los
  adaptadores generados.

## Instalar en un repositorio

```bash
pipx install git+https://github.com/huanrasan/sdlc-harness.git
sdlc init ruta/a/tu-repo --profile standard --agents claude-code,codex,copilot,cursor,gemini-cli --ci github
cd ruta/a/tu-repo
python3 .harness/sdlc.pyz hooks
python3 .harness/sdlc.pyz doctor
```

`init` nunca sobrescribe archivos existentes (lista los que omitió) e incluye la CLI en el repo como
`.harness/sdlc.pyz` (solo biblioteca estándar), así que el repositorio destino y la CI solo necesitan Python ≥ 3.11.
Después:

1. Completa la sección `Project` de `AGENTS.md` (comandos de build, test y lint). Mantenla breve.
2. Asigna personas o equipos en `.harness/roster.toml`, ejecuta `python3 .harness/sdlc.pyz codeowners` y configura la
   protección de ramas (ver [controles](controles.md#checklist-de-configuración-de-plataforma)).
3. Agrega los jobs de CI propios de tu stack (tests, SAST, SBOM...) junto a `sdlc-gates`.
4. Haz commit de todo, incluidos los adaptadores generados, para que todos los colaboradores y la CI usen el
   mismo arnés.

| Opción | Valores | Notas |
|---|---|---|
| `--profile` | `lite`, `standard`, `regulated` | Se puede cambiar después en `harness.toml`. |
| `--agents` | claves de `.harness/adapters.toml` | Los agentes que leen `.agents/skills` de forma nativa no necesitan archivos adicionales. |
| `--mode` | `symlink`, `copy` | `copy` para sistemas de archivos sin symlinks; `check` detecta desincronización. |
| `--ci` | `github`, `gitlab`, `none` | GitLab: incluye `.gitlab-ci.sdlc.yml` desde tu `.gitlab-ci.yml`. |

## Flujo diario

Pídele el trabajo a tu agente como siempre. `AGENTS.md` lo dirige a la skill `sdlc-orchestrator`, que ejecuta:

```bash
python3 .harness/sdlc.pyz new feature payment-retries --risk high   # crea docs/changes/<fecha>-payment-retries/
python3 .harness/sdlc.pyz phase <id> design                          # bloqueado hasta que spec.md esté completo y aprobado
python3 .harness/sdlc.pyz check                                      # la misma compuerta que corre en CI
```

Los artefactos obligatorios por perfil, tipo y riesgo se definen en `.harness/profiles/<perfil>.toml`. Una regla
vuelve obligatorio un artefacto cuando el cambio **ya pasó** la fase de esa regla. Las secciones de plantilla
sin completar (`<!-- sdlc:fill -->`) hacen fallar la compuerta. Además de la presencia, las **compuertas semánticas**
verifican la consistencia:

| Artefacto | Verificaciones |
|---|---|
| `spec.md` | al menos un criterio `AC-n` en formato Given/When/Then o EARS; ninguna fila NFR vacía |
| `threat-model.md` | al menos una amenaza `T-n`; cada amenaza con un control verificable |
| `plan.md` | cada `AC-n` y `T-n` en la tabla de trazabilidad con su test; cada tarea con su verificación de "done" |
| `verification.md` | cada `AC-n` aprobado con evidencia; los tests citados existen si se define `[verification] test_paths`; hallazgos con disposición |
| `review.md` | veredicto `ready-for-human-approval`, contexto limpio `yes` y ningún ítem sin marcar |
| `release.md`, `runbook.md` | versión, artefactos, rollout y rollback; al menos una alerta y mitigaciones seguras |
| ADRs | al menos dos opciones, decisión y consecuencias |

| Artefacto | lite | standard | regulated |
|---|---|---|---|
| `spec.md` | feature/architecture; fix desde medium | todos | todos |
| `design.md` | architecture; feature high | feature desde medium; architecture | todos |
| ADR | architecture | architecture | architecture |
| `threat-model.md` | - | feature high; architecture desde medium | feature desde medium; architecture |
| `plan.md` | - | feature desde medium; architecture | todos |
| `verification.md` | desde medium | todos | todos |
| `review.md` | - | desde medium | todos |
| `release.md` | - | feature/architecture desde medium | todos |
| `runbook.md` | - | feature high; architecture desde medium | feature/architecture desde medium |
| Trailer `Change:` en commits | - | - | obligatorio |
| Recibos de aprobación humana | ninguno | spec, design, ADR, modelo de amenazas, release | todos los artefactos |

## Aprobaciones

Los perfiles marcan artefactos con `approve = true`. Un artefacto así bloquea la fase siguiente hasta que una persona
con un rol autorizado (ver `[authority]` en `.harness/roster.toml`) registra un recibo y aprueba el pull request:

```bash
python3 .harness/sdlc.pyz approve <id> spec.md --as alice --role product-owner   # solo humanos
git add docs/changes/<id> && git commit -m "docs: approve spec" && git push
# luego envía una revisión aprobatoria en el pull request
```

El recibo guarda el SHA-256 del artefacto; si el artefacto se edita después, la aprobación queda invalidada. En CI,
`sdlc approvals verify` confirma con la API de GitHub o GitLab que la persona indicada aprobó un commit que contiene
exactamente ese contenido y el recibo, que pertenece al rol (directamente o mediante un equipo) y, con
`separation_of_duties`, que no es autora del pull request ni del artefacto. Cada cambio mantiene además un
`audit.jsonl` encadenado por hash, y la CI rechaza modificaciones a eventos existentes. En GitLab hay que activar
"Remove all approvals when commits are added". La verificación de equipos necesita un token con lectura de la
organización (secreto `SDLC_APPROVALS_TOKEN` en GitHub, `GITLAB_TOKEN` en GitLab).

## Sensores

`check --base <ref>` (lo que ejecuta la CI en los pull requests) agrega sensores de historia y de estructura. Cada uno
tiene un nivel por perfil (`[sensors]` en `.harness/profiles/<perfil>.toml`: `error`, `warn` u `off`).

| Sensor | Qué impone | Vía de excepción |
|---|---|---|
| Test-first (`sdlc tdd`) | los commits `feat`/`fix`/`perf` que tocan código fuente van después de un cambio de tests del rango, o junto con él | trailer `TDD-Waiver: <motivo>` |
| Tests debilitados (`sdlc tdd`) | sin nuevos marcadores skip/ignore/only/focus (Python, JS/TS, JVM, Go, .NET, Rust, Ruby) ni archivos de test borrados | trailer `Test-Waiver: <motivo>` |
| Arquitectura (`sdlc arch`) | dependencias entre capas e imports prohibidos definidos en `.harness/architecture.toml`, con referencia al ADR | cambiar la regla mediante un ADR |
| Contratos (`sdlc contracts`) | sin cambios incompatibles en `[contracts] files` (OpenAPI 3.x, AsyncAPI 2.x/3.x) salvo que suba el major de `info.version` | subir la versión major |
| Evidencia (`sdlc evidence check`) | archivos SARIF/SBOM requeridos presentes; ningún hallazgo igual o superior a `[evidence] fail_on`; ninguna licencia prohibida | entrada en `.harness/exceptions.toml` con motivo, aprobador y vencimiento |

Los escáneres son reemplazables: sirve cualquiera que escriba SARIF (`sdlc-evidence/<tipo>.sarif`) o CycloneDX JSON
(`sdlc-evidence/sbom*.json`). El job `sensors` de CI incluye contenedores de gitleaks, Semgrep, Trivy, Syft y Checkov;
fíjalos por digest y replícalos en un registro interno para CI privada o air-gapped.

## Releases

Crear un tag `v*` ejecuta `.github/workflows/sdlc-release.yml` (o los jobs `release-*` de GitLab): compuertas sobre el
commit etiquetado, tu `scripts/build-release`, SBOM CycloneDX validado contra la política de licencias, attestations de
procedencia SLSA y de SBOM, firmas keyless con Sigstore y la publicación, detrás de un entorno protegido `production`.

## Cómo funciona

```text
            guías (feedforward)                          sensores (feedback)
  AGENTS.md ──> .agents/skills/<fase>/SKILL.md     tests, linters, escáneres (CI del stack)
       │                  │                        sdlc check / compuertas de fase
       ▼                  ▼                        revisión independiente (contexto limpio)
  cualquier agente ──escribe──> docs/changes/<id>/* ──> git hooks (rápido) ──> CI (autoridad) ──> aprobación humana (plataforma)
       ▲
  adaptadores generados por `sdlc sync` desde .harness/adapters.toml (CLAUDE.md, GEMINI.md, enlaces de skills)
```

| Ruta | Propósito |
|---|---|
| `AGENTS.md` | Mapa para agentes: comandos, flujo, reglas no negociables, índice de skills generado. |
| `.agents/skills/` | Skills canónicas (formato Agent Skills): una por fase del SDLC, más el orquestador y el mantenimiento. |
| `harness.toml` | Perfil, agentes destino, rutas y configuración de verificación. |
| `.harness/roster.toml` | Roles, miembros, matriz de autoridad y reglas extra de CODEOWNERS. |
| `.harness/architecture.toml`, `.harness/exceptions.toml` | Reglas de capas ejecutables; excepciones de sensores con vencimiento. |
| `.harness/profiles/` | Reglas de compuerta por perfil (TOML editable). |
| `.harness/adapters.toml` | Adaptadores declarativos por agente. |
| `.harness/sdlc.pyz`, `.harness/hooks/` | CLI incluida en el repo y git hooks. |
| `docs/changes/<id>/approvals.toml`, `audit.jsonl` | Recibos de aprobación y log de auditoría encadenado por hash. |
| `docs/changes/` | Change records (sistema de registro). |
| `docs/sdlc/templates/` | Plantillas de artefactos. |
| `docs/adr/` | Registros de decisiones de arquitectura. |

## Extender

- **Nuevo agente**: agrega una entrada en `.harness/adapters.toml` (`files` con el contenido requerido y `links`
  para reflejar las skills), inclúyelo en `targets` y ejecuta `sdlc sync`. Considera contribuirlo al repositorio.
- **Perfil propio**: copia un perfil a `.harness/profiles/<nombre>.toml` y define `profile = "<nombre>"`.
- **Skills de la organización**: agrega carpetas en `.agents/skills/` (por ejemplo, reglas de tu landing zone) y
  ejecuta `sdlc sync`.
- **Hooks del agente (opcional)**: apunta el hook previo a herramientas o de cierre de tu agente a
  `python3 .harness/sdlc.pyz check` para recibir feedback antes; la CI sigue siendo la autoridad.
- **MCP (opcional)**: servidores de memoria (p. ej. engram) o de inteligencia de código (p. ej. gortex)
  complementan los change records, pero no los reemplazan.

## Actualizar el arnés

Actualiza el paquete (`pipx upgrade sdlc-harness`), ejecuta `init` en un directorio temporal y compara. Copia
`.harness/sdlc.pyz` y las skills que no hayas personalizado. Una vez instalados, los perfiles, el roster y los
adaptadores son tuyos. El comando `sdlc upgrade` está previsto para v0.5.
