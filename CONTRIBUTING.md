# Contributing / Contribuir

**EN** - Issues and pull requests are welcome.

1. Open an issue first for new skills, profiles or CLI commands; significant changes need an ADR in `docs/adr/`.
2. Keep the CLI standard-library only and Python ≥ 3.11 compatible.
3. Run `python3 -m unittest discover -s tests` before pushing. Add tests for CLI behaviour changes.
4. Skills must pass the Agent Skills format checks (`sdlc check` on an installed template).
5. Update both `docs/en/` and `docs/es/` when changing user-facing documentation.
6. Use Conventional Commits. Disclose substantial AI assistance in the PR description.
7. Do not copy text or code from sources whose license is incompatible with MIT; cite them in `ACKNOWLEDGEMENTS.md`.

**ES** - Se aceptan issues y pull requests.

1. Abre primero un issue para proponer nuevas skills, perfiles o comandos de la CLI. Los cambios significativos
   requieren un ADR en `docs/adr/`.
2. La CLI debe usar solo la biblioteca estándar y ser compatible con Python ≥ 3.11.
3. Ejecuta `python3 -m unittest discover -s tests` antes de hacer push y agrega tests cuando cambie el
   comportamiento de la CLI.
4. Las skills deben pasar las validaciones del formato Agent Skills (`sdlc check` sobre la plantilla instalada).
5. Actualiza `docs/en/` y `docs/es/` cuando cambies documentación dirigida a usuarios.
6. Usa Conventional Commits y declara en la descripción del PR si hubo asistencia sustancial de IA.
7. No copies texto ni código de fuentes con licencia incompatible con MIT; cítalas en `ACKNOWLEDGEMENTS.md`.
