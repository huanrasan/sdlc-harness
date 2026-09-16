# Investigación y recomendación de diseño

> English version: [../en/research.md](../en/research.md)
> Fecha de corte de la investigación: 2026-09-16.

## 1. Qué es un "arnés" y por qué importa

"Harness engineering" es el trabajo de rodear a un agente de programación con **guías** (información que
recibe antes de actuar) y **sensores** (señales que recibe después de actuar para corregirse), de modo que su
resultado sea confiable en software de producción. Birgitta Böckeler (martinfowler.com) propone
clasificar esos controles por tipo:

| | Computacional (determinista, barato) | Inferencial (LLM, caro, no determinista) |
|---|---|---|
| **Guía (feedforward)** | plantillas, scaffolding, codemods | `AGENTS.md`, skills, especificaciones |
| **Sensor (feedback)** | tests, linters, type checkers, escáneres, CI | revisión por agente independiente, evaluadores |

Hallazgos convergentes de las fuentes:

- **El contexto es un recurso escaso.** OpenAI (harness engineering con Codex) usa `AGENTS.md` como *mapa*
  corto que apunta a documentación versionada en el repo, que funciona como sistema de registro. Anthropic
  recomienda instrucciones concisas y carga progresiva. La especificación Agent Skills formaliza esa carga
  progresiva: primero solo metadatos (unos 100 tokens), luego las instrucciones (menos de 5000 tokens) y
  los recursos cuando se necesitan.
- **Las reglas que importan deben ser deterministas.** Las restricciones de arquitectura se imponen con
  linters y tests estructurales, no con prosa. Un error que se repite se codifica como control.
- **Generar y evaluar deben estar separados.** Anthropic observa que un agente que califica su propio trabajo
  tiende a calificarlo bien. Por eso conviene un evaluador independiente con contexto limpio y contratos de
  "done" acordados antes de implementar.
- **Tareas largas: estado en archivos.** Plan, progreso y notas de traspaso quedan en el repo para que una
  sesión nueva retome el trabajo sin memoria previa.
- **Recolección de basura.** Pasadas periódicas que detectan desviaciones entre docs y código y podan
  instrucciones obsoletas.
- **La IA amplifica.** DORA 2025 muestra que la IA potencia las fortalezas y las debilidades del sistema.
  Sus 7 capacidades (postura clara sobre IA, ecosistema de datos sano, datos internos accesibles a la IA,
  control de versiones sólido, lotes pequeños, foco en el usuario, plataformas internas de calidad) son
  precondiciones que el arnés debe reforzar, no sustituir.

## 2. Estándares que hacen posible "cualquier agente"

| Estándar | Rol en el arnés | Estado (2026-09) |
|---|---|---|
| **AGENTS.md** | Instrucciones de proyecto legibles por cualquier agente. El archivo más cercano tiene precedencia. | Bajo la Agentic AI Foundation (Linux Foundation). Adoptado por Codex, Copilot, Cursor, Gemini CLI, Jules, Devin, Amp, VS Code y otros. |
| **Agent Skills (`SKILL.md`)** | Conocimiento condicional por fase con carga progresiva. `name` y `description` obligatorios; directorios `scripts/`, `references/` y `assets/`. | Estándar abierto (agentskills.io). `.agents/skills/` es la ruta neutral que leen Codex, Copilot, Cursor y OpenCode; Claude Code, Gemini CLI y Windsurf necesitan enlace a su ruta. |
| **MCP** | Integraciones opcionales (memoria, inteligencia de código, trackers). | Bajo la AAIF. |
| **Git hooks + CI** | Compuertas deterministas independientes del agente. | Universal. |

Los **hooks de ciclo de vida de cada agente** (Claude Code, Codex, Gemini CLI, Cursor) cumplen funciones
equivalentes, pero cada uno usa un vocabulario de eventos distinto y cambian con frecuencia. Por eso el arnés
**no depende de ellos para imponer controles**: la autoridad está en git hooks y CI. Los hooks del agente
quedan como adaptadores opcionales que invocan los mismos comandos.

## 3. Controles para equipos y organizaciones

| Marco | Qué aporta al arnés |
|---|---|
| NIST SSDF SP 800-218 y el perfil de IA SP 800-218A | Prácticas PO/PS/PW/RV de desarrollo seguro; base de la matriz de controles. |
| SLSA v1.2 (Build + Source track), Sigstore, SBOM CycloneDX/SPDX, OpenSSF Scorecard | Integridad de la cadena de suministro: revisión obligatoria, ramas protegidas, procedencia y firma. |
| OWASP Top 10 for Agentic Applications 2026 y Top 10 for LLM Applications | Riesgos del propio agente (goal hijack, mal uso de herramientas, privilegios, memoria envenenada) y de las funcionalidades con IA que se construyan. |
| OWASP SAMM / ASVS | Madurez del programa y requisitos verificables. |
| NIST AI RMF, ISO/IEC 42001, EU AI Act | Gobierno de IA: divulgación del uso de IA, supervisión humana, trazabilidad y documentación. El arnés genera evidencia; **no certifica cumplimiento**. |
| DORA (throughput, inestabilidad, tasa de retrabajo) | Métricas para saber si el arnés mejora la entrega. |
| Advice process (Harmel-Law), ADRs (Nygard/MADR), marco de decisión (Natanzon), Tech Radar | Decisiones descentralizadas pero documentadas y asesoradas. |

**Principio clave de gobierno:** el agente nunca aprueba su propio trabajo. La aprobación humana debe
imponerla la plataforma (CODEOWNERS, protección de ramas, entornos protegidos) y no un campo que el agente
pueda editar.

## 4. Fuentes del repositorio de referencia: qué se usó y cómo

Se revisó solo la lista de fuentes de `csalamando/harness-sdlc`. No se copió su código, estructura ni textos.

| Fuente | Uso en este arnés |
|---|---|
| Natanzon, *Architectural Decision Framework* | Ideas del proceso de decisión (último momento responsable, criterios ponderados antes de las opciones, revisitar). **Licencia CC BY-NC-SA 4.0, incompatible con MIT**: se redactó un proceso propio y solo se cita. |
| Harmel-Law / Fowler, *Scaling Architecture Conversationally* | Advice process en la skill de diseño y en la plantilla ADR (sección "Advice received"). |
| Nygard (ADR), ThoughtWorks Tech Radar | Formato y ciclo de vida de ADRs. El Tech Radar queda en el roadmap. |
| DeepSeek Harness (MIT) | Se evaluó su enfoque de "todo es plugin". Se descartó un runtime propio: el arnés debe vivir *dentro* del repo y servir a cualquier agente existente. Se conserva la idea de puntos de extensión declarativos (`adapters.toml`, perfiles). |
| gentle-ai / engram (MIT) | Confirman la viabilidad del enfoque multiagente y el valor de la memoria persistente y del principio "verificar le gana a generar". En v0.1 la memoria son archivos versionados (change records); engram queda como integración MCP opcional. |
| gortex (Apache-2.0) | Inteligencia de código vía MCP: integración opcional recomendada para repos grandes. |
| archify (MIT), grip, Penpot | Diagramas, visualización de Markdown y prototipado UX: fuera del alcance de v0.1 y candidatos a extensiones. |

## 5. Recomendación de arquitectura

1. **Núcleo agnóstico al agente**: `AGENTS.md` (mapa ≤150 líneas) + `.agents/skills/` (10 skills del SDLC)
   como única fuente. `sdlc sync` genera adaptadores (`CLAUDE.md`, `GEMINI.md`, enlaces o copias de
   skills) a partir de un catálogo declarativo.
2. **Compuertas deterministas fuera del agente**: CLI `sdlc` en Python solo con stdlib, que se ejecuta
   igual en local, en GitHub Actions, en GitLab self-managed o en runners sin internet. Git hooks para
   feedback rápido; CI como autoridad.
3. **Change records como sistema de registro**: `docs/changes/<id>/change.toml` con tipo, riesgo, fase y
   divulgación de IA, más artefactos por fase. La CLI impide avanzar de fase sin evidencia.
4. **Perfiles proporcionales al riesgo**: `lite`, `standard` y `regulated`, con reglas en TOML editables.
   La ceremonia crece con el riesgo, no de forma uniforme.
5. **Separación generador/evaluador**: la skill de revisión exige contexto limpio; la aprobación final es
   humana vía plataforma.
6. **Agnóstico a la nube**: IaC y policy-as-code descritos por capacidad (Terraform/OpenTofu, Pulumi,
   Crossplane, OPA, Kyverno) y herramientas open source autohospedables para nube privada o air-gapped.
7. **Mejora continua**: skill `sdlc-maintain` para recolección de basura y para convertir errores repetidos
   en controles deterministas.

### Trade-offs asumidos

- **TOML + stdlib** en lugar de YAML: no hay dependencias, pero se exige Python ≥ 3.11.
- **Evidencia en archivos** en lugar de integraciones con Jira u otros trackers: funciona en cualquier
  lugar, pero duplica parte de lo que hay en el tracker. Las integraciones MCP quedan como opcionales.
- **Symlinks por defecto**: evitan que las copias se desincronicen, pero en Windows requieren modo
  desarrollador. Existe el modo `copy` con detección de desincronización.
- **Las compuertas validan forma, no calidad**: comprueban que la evidencia exista y esté completa. La
  calidad la juzgan el revisor independiente y el humano que aprueba.

## 6. Roadmap sugerido

- v0.2: adaptadores de hooks por agente que invoquen la CLI; plantilla de `CODEOWNERS` asistida por `init`.
- v0.3: jobs de referencia para SBOM, firma y procedencia (GitHub y GitLab); integración con OpenSSF Scorecard.
- v0.4: Tech Radar y principios arquitectónicos como artefactos; métricas DORA del arnés.
- v0.5: extensiones opcionales (MCP de memoria e inteligencia de código, diagramas).

## 7. Fuentes

Lista completa con URLs en [ACKNOWLEDGEMENTS.md](../../ACKNOWLEDGEMENTS.md).
