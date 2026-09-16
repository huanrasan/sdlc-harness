# sdlc-harness

> [Read in English](README.md)

Un **arnés agnóstico al agente para el ciclo de vida del desarrollo de software**. Da a cualquier agente de
programación (Claude Code, Codex, GitHub Copilot, Cursor, Gemini CLI, Windsurf, OpenCode...) las mismas guías y
las mismas compuertas deterministas, desde la especificación hasta la operación. Sus controles escalan desde un
desarrollador individual hasta una organización regulada. No depende del stack ni de la nube: funciona en nube
pública, nube privada, on-prem o entornos air-gapped.

**Estado:** v0.2.0, versión preliminar.

## Por qué

Un agente de programación es tan confiable como el arnés que lo rodea: las **guías** que lee antes de actuar y los
**sensores** que le indican, de forma determinista, cuándo se equivocó. Este proyecto empaqueta ese arnés sobre
estándares abiertos para que un equipo pueda cambiar o combinar agentes sin rehacer su proceso.

## Qué incluye

- **`AGENTS.md` + 10 Agent Skills**: orquestación, especificación, diseño (ADR + modelo de amenazas), planificación,
  implementación, verificación, revisión, release, operación y mantenimiento.
- **Change records** (`docs/changes/<id>/`) con plantillas: la evidencia vive junto al código y sobrevive a los
  reinicios de contexto.
- **Compuertas de fase** que verifican consistencia (criterios trazados a tests, amenazas a controles), ejecutadas por
  una CLI sin dependencias incluida en cada repositorio, idéntica en git hooks y en CI (GitHub Actions y GitLab).
- **Aprobaciones humanas ligadas al contenido**: recibos SHA-256 por artefacto, roles y matriz de autoridad, generación
  de CODEOWNERS, separación de funciones, verificación contra la plataforma en CI y log de auditoría encadenado por hash.
- **Perfiles** `lite`, `standard` y `regulated` que exigen artefactos según el tipo y el riesgo del cambio.
- **Adaptadores** generados para los agentes que no leen `.agents/skills` de forma nativa.
- **Matriz de controles** mapeada a NIST SSDF, SLSA, OWASP Agentic Top 10, DORA y marcos de gobierno de IA.

## Inicio rápido

```bash
pipx install git+https://github.com/huanrasan/sdlc-harness.git
sdlc init ../mi-servicio --profile standard --ci github
cd ../mi-servicio
python3 .harness/sdlc.pyz hooks && python3 .harness/sdlc.pyz doctor
python3 .harness/sdlc.pyz new feature payment-retries --risk medium
```

Luego pídele a tu agente que trabaje en el cambio: `AGENTS.md` lo dirige a la skill `sdlc-orchestrator`.

## Documentación

| | Español | English |
|---|---|---|
| Guía de uso | [docs/es/guia.md](docs/es/guia.md) | [docs/en/guide.md](docs/en/guide.md) |
| Investigación y fundamentos del diseño | [docs/es/investigacion.md](docs/es/investigacion.md) | [docs/en/research.md](docs/en/research.md) |
| Matriz de controles | [docs/es/controles.md](docs/es/controles.md) | [docs/en/controls.md](docs/en/controls.md) |
| Decisiones (ADRs) | | [docs/adr/](docs/adr/README.md) |

Política de idioma: las guías son bilingües. Los archivos dirigidos a agentes (skills, plantillas, `AGENTS.md`) y
los ADRs están en inglés como fuente única.

## Principios

1. Estándares abiertos antes que funciones propietarias. 2. Compuertas deterministas antes que instrucciones.
3. El agente nunca aprueba su propio trabajo. 4. Ceremonia proporcional al riesgo. 5. Evidencia dentro del
repositorio. 6. Todo error repetido se convierte en un control.

## Contribuciones, seguridad y licencia

Ver [CONTRIBUTING.md](CONTRIBUTING.md) y [SECURITY.md](SECURITY.md). Licencia [MIT](LICENSE).
Fuentes y créditos: [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md).
