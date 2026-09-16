# Guía de uso

> English version: [../en/guide.md](../en/guide.md)

## Requisitos

- Git y Python ≥ 3.11 (solo biblioteca estándar). En Windows: WSL, Git Bash o `--mode copy`.
- Cualquier agente de programación que lea `AGENTS.md`. Las skills funcionan de forma nativa o mediante los
  adaptadores generados.

## Instalar en un repositorio

```bash
git clone https://github.com/huanrasan/sdlc-harness.git
python3 sdlc-harness/cli/sdlc.py init ruta/a/tu-repo --profile standard --agents claude-code,codex,copilot,cursor,gemini-cli --ci github
cd ruta/a/tu-repo
python3 .harness/sdlc.py hooks
python3 .harness/sdlc.py doctor
```

`init` nunca sobrescribe archivos existentes (lista los que omitió). Después:

1. Completa la sección `Project` de `AGENTS.md` (comandos de build, test y lint). Mantenla breve.
2. Renombra `.github/CODEOWNERS.example` a `CODEOWNERS` y configura la protección de ramas
   (ver [controles](controles.md#checklist-de-configuración-de-plataforma)).
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
python3 .harness/sdlc.py new feature payment-retries --risk high   # crea docs/changes/<fecha>-payment-retries/
python3 .harness/sdlc.py phase <id> design                          # bloqueado hasta que spec.md esté completo
python3 .harness/sdlc.py check                                      # la misma compuerta que corre en CI
```

Los artefactos obligatorios por perfil, tipo y riesgo se definen en `.harness/profiles/<perfil>.toml`. Una regla
vuelve obligatorio un artefacto cuando el cambio **ya pasó** la fase de esa regla. Las secciones de plantilla
sin completar (`<!-- sdlc:fill -->`) hacen fallar la compuerta.

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
| `harness.toml` | Perfil, agentes destino y rutas. |
| `.harness/profiles/` | Reglas de compuerta por perfil (TOML editable). |
| `.harness/adapters.toml` | Adaptadores declarativos por agente. |
| `.harness/sdlc.py`, `.harness/hooks/` | CLI y git hooks. |
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
  `python3 .harness/sdlc.py check` para recibir feedback antes; la CI sigue siendo la autoridad.
- **MCP (opcional)**: servidores de memoria (p. ej. engram) o de inteligencia de código (p. ej. gortex)
  complementan los change records, pero no los reemplazan.

## Actualizar el arnés

Ejecuta `init` desde un clon más reciente en un directorio temporal y compara. Copia `.harness/sdlc.py` y las
skills que no hayas personalizado. Una vez instalados, los perfiles y adaptadores son tuyos.
