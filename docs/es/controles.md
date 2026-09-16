# Matriz de controles

> English version: [../en/controls.md](../en/controls.md)

Relación entre los mecanismos del arnés y marcos reconocidos. Es un punto de partida para tu propio mapeo de
controles y **no** constituye una certificación de cumplimiento. "Plataforma" se refiere a configuración del
sistema VCS/CI: el arnés la documenta y `sdlc doctor` la verifica, pero no puede imponerla por sí solo.

| # | Control | Mecanismo | Imposición | NIST SSDF | Otras referencias |
|---|---|---|---|---|---|
| C1 | Requisitos de seguridad y no funcionales definidos antes de construir | Tabla NFR en `spec.md`; `sdlc-specify` | Compuerta (`phase`) | PO.1, PW.1 | ISO/IEC 42001 |
| C2 | Análisis de riesgo del diseño y modelado de amenazas | `threat-model.md`; referencias de `sdlc-design` | Compuerta según perfil y riesgo | PW.1, PW.2 | Threat Modeling Manifesto; OWASP Agentic Top 10 |
| C3 | Decisiones significativas documentadas con asesoría y trade-offs | ADRs + `adrs` en `change.toml` | Compuerta (architecture) + formato ADR | PW.2 | Advice process; MADR |
| C4 | Cambios pequeños y trazables | `plan.md`; Conventional Commits; trailer `Change:` (regulated) | Hook `commit-msg` + CI | PS.1 | DORA lotes pequeños; SLSA Source track |
| C5 | Pruebas y análisis automatizado del código | `verification.md`; evidencia SARIF (SAST, secretos, IaC) con política de severidad | Compuerta + CI (`evidence check`) | PW.7, PW.8 | OWASP ASVS |
| C6 | Secretos nunca commiteados | Job gitleaks; reglas no negociables del agente | CI | PS.1, PW.5 | OWASP Agentic ASI03 |
| C7 | Componentes de terceros evaluados | SARIF de SCA + SBOM CycloneDX con lista de licencias prohibidas; excepciones con vencimiento | CI (`evidence check`) | PW.4, RV.1 | SLSA; OpenSSF Scorecard |
| C8 | Revisión independiente: quien genera no evalúa | Compuerta semántica de `review.md` (contexto limpio, veredicto) + recibo humano verificado contra la revisión en la plataforma | Compuerta + CI (`approvals verify`) | PW.7 | SLSA Source track; patrón evaluador de Anthropic |
| C9 | Supervisión humana del resultado de la IA y divulgación de su uso | Campo `ai_assisted`; recibos de aprobación por roles autorizados; separación de funciones | Compuerta + CI (`approvals verify`) | PO.2 | EU AI Act (supervisión humana); NIST AI RMF Govern; ISO/IEC 42001 |
| C10 | Configuración del arnés y del pipeline protegida | CODEOWNERS generado desde el roster para `harness.toml`, `.harness/`, `.agents/`, workflows; `codeowners --check` | CI + **Plataforma** | PO.3, PO.5, PS.1 | OWASP Agentic ASI04 |
| C11 | Integridad del release: SBOM, firma, procedencia | Workflow `sdlc-release`: SBOM + política de licencias, attestations de procedencia SLSA y de SBOM, firmas keyless, entorno protegido | CI + **Plataforma** | PS.2, PS.3 | SLSA Build L2/L3; Sigstore; CycloneDX |
| C12 | Despliegue progresivo y rollback | Rollout/rollback en `release.md`; entornos protegidos | Compuerta + **Plataforma** | - | DORA change failure rate |
| C13 | Operabilidad y aprendizaje de incidentes | `runbook.md`; plantilla de postmortem | Compuerta según perfil y riesgo | RV.2, RV.3 | Google SRE |
| C14 | Entrada no confiable hacia agentes (inyección de prompt/objetivo) | Regla no negociable en AGENTS.md; agente con mínimo privilegio | Guía + configuración del agente | PO.5 | OWASP Agentic ASI01, ASI02, ASI06 |
| C15 | Acciones destructivas con confirmación humana | Regla no negociable en AGENTS.md; `apply` de IaC por humanos | Guía + **Plataforma** (entornos protegidos) | PO.5 | OWASP Agentic ASI02, ASI05, ASI10 |
| C16 | Deriva de instrucciones y documentación controlada | `sdlc check` (índice de skills, adaptadores, tamaño de AGENTS.md); `sdlc-maintain` | CI + tarea programada | PO.3 | "Garbage collection" de harness engineering |
| C17 | Integridad de aprobaciones: ligadas al contenido exacto, atribuibles y con evidencia de manipulación | Recibos SHA-256 en `approvals.toml`; `audit.jsonl` encadenado por hash; verificación append-only contra la rama base | Compuerta + CI | PS.1, PO.2 | SLSA Source track; registros ISO/IEC 42001 |
| C18 | Integridad de los tests: preceden a los cambios de comportamiento y no se debilitan | `sdlc tdd`: orden test-first; marcadores skip/only y tests borrados; excepciones humanas por trailer | CI (`check --base`) | PW.8 | OWASP Agentic ASI01/ASI10 |
| C19 | Conformidad con la arquitectura | Reglas de capas en `.harness/architecture.toml` con referencia a ADRs | Compuerta + CI | PW.1, PW.2 | Fitness functions de arquitectura |
| C20 | Compatibilidad de APIs | Detección de cambios incompatibles en OpenAPI/AsyncAPI con política SemVer | CI (`check --base`) | PW.1 | Semantic Versioning |
| C21 | Valor de producto validado antes de construir y después del release | Métricas y decisión go en `discovery.md`; resultados y decisión en `outcome.md` | Compuerta | PO.1 | Foco en el usuario (DORA) |
| C22 | Privacidad y protección de datos desde el diseño | Clasificación, retención e impacto de privacidad en `data.md`; aprobación para datos personales | Compuerta + aprobaciones | PO.1, PW.1 | DPIA estilo GDPR; ISO/IEC 27701 |
| C23 | Gestión de riesgos de sistemas de IA | Riesgos, evals con umbral, supervisión humana y monitoreo en `ai-risk.md` | Compuerta + aprobaciones | PW.1 (SP 800-218A) | NIST AI RMF Map/Measure/Manage; EU AI Act; OWASP LLM Top 10 |
| C24 | Conformidad con la política de la organización y desviaciones gobernadas | `policy.toml` vendorizado con lock de hashes; desviaciones con vencimiento por roles autorizados | Compuerta + CI | PO.1, PO.3 | Controles ISO/IEC 42001; auditoría interna |
| C25 | Integridad y procedencia de la memoria | Memoria revisada en PR; detección de secretos; fechas de revisión; herramientas MCP de solo lectura salvo `memory_add` | Compuerta + revisión de PR | PO.5 | OWASP Agentic ASI06 |
| C26 | Medición y mejora continua | `report trace\|flow\|dora`; revisión de iteración | CI (semanal) | PO.4 | Métricas DORA |
| C27 | Retiro seguro | Consumidores, sunset, disposición de datos y revocación de credenciales en `retirement.md` | Compuerta | PS.3, RV.2 | - |

## Checklist de configuración de plataforma

- Protección de la rama principal: PR obligatorio, status checks requeridos (`sdlc-gates`), revisión de
  Code Owners, descartar aprobaciones obsoletas y prohibir force push.
- `CODEOWNERS` generado con `sdlc codeowners` desde `.harness/roster.toml`.
- Un token con lectura de revisiones y de membresía de equipos para `sdlc approvals verify` (`SDLC_APPROVALS_TOKEN`); en GitLab, activar "Remove all approvals when commits are added".
- Entornos de despliegue protegidos con revisores humanos obligatorios para producción.
- Commits firmados o identidad verificada si la organización lo exige.
- Credenciales de agentes: mínimo privilegio, tokens de corta vida y sin escritura en producción por defecto.
- Acciones e imágenes de CI fijadas por digest; espejo interno para nube privada o entornos air-gapped.
