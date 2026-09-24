# Manual paso a paso: el arnés, fase por fase y rol por rol

*English: [Playbook](../en/playbook.md).*

Esta es la versión larga y literal: para cada fase, quién actúa, el comando exacto que ejecuta, por qué el arnés lo
pide, cómo se ve el fallo (salida real, copiada de una ejecución) y cómo salir de él. Si querés la versión corta
primero, leé el [recorrido](recorrido.md). Si querés ver los artefactos terminados de los que habla esta página,
están en el [ejemplo de change record](../examples/README.md).

Todo lo que sigue acompaña a un cambio real: **`2026-09-17-staff-csv-export`**, una funcionalidad chica (el personal
del estudio exporta sus reservas a CSV), de tipo `feature`, riesgo `medium`, scopes `ui,api`, con el perfil
`standard`.

## 0. Tres reglas que explican todo lo demás

**El agente produce evidencia, las personas la aprueban y la plataforma prueba que la aprobación existió.** Un
agente puede escribir todos los documentos y correr todos los chequeos. Nunca puede ejecutar `sdlc approve` ni
`sdlc amend`, ni editar `approvals.toml` o `audit.jsonl`. Si lo hace, la CI lo detecta, porque la aprobación se
verifica contra GitHub o GitLab, no contra el archivo.

**`sdlc check` y `sdlc phase` hacen cosas distintas, y esto confunde a todo el mundo una vez.** Una regla vuelve
obligatorio un artefacto *una vez que el cambio pasó la fase de ese artefacto*. Mientras tu cambio está en
`discover`, `sdlc check` dice `OK: 0 errors` aunque `discovery.md` siga lleno de marcadores. La compuerta se
dispara cuando querés salir: `sdlc phase <id> spec` evalúa las reglas de la fase a la que entrás. Usá
`sdlc status` cuando quieras la respuesta hacia adelante: te dice qué bloquea la fase *siguiente*, antes de
intentarlo.

**Un recibo está atado a los bytes del archivo.** Aprobar registra el SHA-256 del artefacto. Si después cambiás un
carácter, la aprobación queda vencida. Eso no es burocracia: es lo que impide que "aprobado" se despegue de lo que
alguien leyó de verdad.

## 1. El reparto

Una persona puede ocupar varios roles; un rol puede ser un equipo de la plataforma (`@acme/security`). Quién puede
aprobar qué vive en `[authority]` de `.harness/roster.toml`, y **un artefacto solo necesita recibo si el perfil lo
exige**.

| Rol | Aprueba (cuando el perfil lo exige) | En palabras simples |
|---|---|---|
| `product-owner` | `discovery.md`, `spec.md`, `ux.md`, `outcome.md` | decide que el problema vale la pena y que "terminado" significa lo correcto |
| `tech-lead` | `spec.md`, `design.md`, `plan.md`, `verification.md`, `review.md`, `cost.md`, `retirement.md` | responde por la forma técnica y por que la evidencia sea real |
| `architect` | `design.md`, ADRs, `ai-risk.md`, `retirement.md`, desviaciones | responde por las decisiones difíciles de revertir |
| `security` | `threat-model.md`, `data.md`, `ai-risk.md`, desviaciones, excepciones | acepta, o se niega a aceptar, riesgo de seguridad |
| `ux-lead` | `ux.md` | responde por los estados que la persona usuaria ve de verdad, errores incluidos |
| `data-steward` | `data.md` | responde por los datos y su uso lícito |
| `finops` | `cost.md` | responde por la factura |
| `release-manager` | `release.md` | decide que esta versión sale, y cómo se revierte |
| `sre` | `runbook.md` | responde por operarlo a las 3 de la mañana |
| `platform` | (ningún artefacto) | es dueño de la instalación del arnés, la CI y el roster |
| el agente | **nada, nunca** | escribe documentos y código, corre chequeos, pide aprobaciones |

En `standard`, los artefactos que necesitan recibo son `discovery.md`, `spec.md`, `design.md`, los ADRs,
`threat-model.md`, `data.md`, `ai-risk.md`, `retirement.md` y `release.md`. En `lite`, ninguno. En `regulated`, casi
todos, incluidos `plan.md`, `verification.md`, `review.md`, `ux.md`, `cost.md` y `runbook.md`.

## 2. Instalación por única vez — el rol `platform`

```bash
pipx install git+https://github.com/huanrasan/sdlc-harness@v0.7.5
sdlc init ruta/al/repo --interactive          # pregunta perfil, agentes, CI y roster; --adopt en un repo existente
cd ruta/al/repo
python3 .harness/sdlc.pyz hooks               # compuertas en pre-commit y chequeo del mensaje de commit
python3 .harness/sdlc.pyz doctor              # revisión de la configuración
```

Después hay que completar `.harness/roster.toml`. **Un rol sin miembros es un rol por el que nadie puede aprobar**,
y el cambio se va a frenar en seco en esa compuerta:

```
WARN  roster: role 'product-owner' has no members (approves spec.md, discovery.md, ux.md, outcome.md)
```

Commiteá `.github/workflows/`, activá la protección de rama exigiendo el check `harness` y —si sos la única persona
que mantiene el repositorio— poné `separation_of_duties = false`, activá la firma de commits, **desactivá el
rebase merge** y exigí commits firmados en `main`, según las
[notas de actualización](actualizar.md#si-sos-la-única-persona-que-mantiene-el-repositorio-activá-la-firma-de-commits).
El rebase merge convierte tus commits firmados en commits sin firma dentro de `main`.

## 3. Fase por fase

Cada fase indica quién actúa, el comando y qué se rompe de verdad.

### `discover` — ¿vale la pena hacerlo?

**Quién:** el agente escribe `discovery.md`; el `product-owner` lo aprueba.

```bash
python3 .harness/sdlc.pyz new feature staff-csv-export --risk medium --scope ui,api   # agente
python3 .harness/sdlc.pyz status                                                      # cualquiera, cuando sea
```

`new` crea `docs/changes/<fecha>-<slug>/` con `change.toml` y una plantilla por artefacto. `status` te dice
enseguida dónde estás parado:

```
2026-09-18-staff-csv-export  [feature risk=medium scopes=ui,api]  phase: discover -> spec
  - blocks spec: docs/changes/2026-09-18-staff-csv-export/discovery.md: unfilled sections (<!-- sdlc:fill -->)
  next: fix the evidence listed above, then: python3 .harness/sdlc.pyz phase 2026-09-18-staff-csv-export spec
```

`discovery.md` tiene que plantear el problema con evidencia, al menos dos opciones **incluyendo no hacer nada**,
métricas de éxito medibles y una decisión. La decisión se verifica:

```
ERROR docs/changes/<id>/discovery.md: 'Decision:' must be one of go, no-go, iterate
```

Hay que escribir `go`, `no-go` o `iterate` literalmente. `no-go` es un resultado válido y detiene el cambio ahí: eso
es un éxito, no un fracaso.

**La aprobación (product-owner, en su propia terminal):**

```bash
python3 .harness/sdlc.pyz approve <id> discovery.md --as pat --role product-owner
```

Dos cosas que salen mal la primera vez:

```
ERROR role 'security' is not authorized to approve 'spec.md' (allowed: ['product-owner', 'tech-lead'])
ERROR 'bob' is not a member of role 'product-owner' in .harness/roster.toml
```

El primero significa que la entrada `[authority]` de ese artefacto no incluye tu rol; el segundo, que tu usuario no
está en el roster. Ambos se arreglan en `.harness/roster.toml`, desde el rol `platform`, no editando el recibo.

Cuando funciona obtenés el recibo y una instrucción que importa:

```
receipt recorded: docs/changes/<id>/discovery.md sha256=ae6b3a077a91 approver=pat role=product-owner
Commit approvals.toml and audit.jsonl, then approve the pull request on the platform.
```

**No te saltees esa segunda frase.** El recibo local es la mitad de la prueba; la CI además le pregunta a GitHub o
GitLab si esa persona aprobó realmente. Si te olvidás, la CI dice:

```
ERROR <artefacto> (pat): no current approval from 'pat' on the pull/merge request
```

### `spec` — ¿qué significa "terminado"?

**Quién:** el agente escribe; `product-owner` o `tech-lead` aprueba.

```bash
python3 .harness/sdlc.pyz phase <id> spec     # agente, una vez aprobado discovery.md
```

Si intentás avanzar antes de que exista la aprobación:

```
gate blocked: <id> stays in 'discover'. Run `python3 .harness/sdlc.pyz status --change <id>` for what is missing and who approves.
ERROR docs/changes/<id>/discovery.md: requires approval by one of roles ['product-owner']; a human approves with:
      python3 .harness/sdlc.pyz approve <id> discovery.md --as <username> --role product-owner
```

El error trae el comando. Pasale esa línea a la persona que ocupa el rol.

`spec.md` necesita criterios de aceptación escritos `AC-1`, `AC-2`, … en forma Dado/Cuando/Entonces, **cada uno
nombrando el test que lo va a verificar**, más requisitos no funcionales con números ("p95 < 300 ms", no "rápido").
Nombrar el test acá es lo que hace que las compuertas de `plan` y `verify` pasen después sin inventar vínculos.

Las fases avanzan de a una. Es deliberado:

```
ERROR cannot skip phases: discover -> design
```

### `design` — cómo, y qué puede salir mal

**Quién:** el agente escribe `design.md` (y `ux.md`, porque este cambio declara el scope `ui`); `tech-lead` o
`architect` aprueba el diseño. En `standard`, `ux.md` **no** necesita recibo; en `regulated`, sí.

```bash
python3 .harness/sdlc.pyz phase <id> design
```

`design.md` cubre la solución, los modos de fallo, la observabilidad, el despliegue y la reversión. Un servicio
nuevo, un datastore, una frontera o un contrato público también requieren un ADR en `docs/adr/`, aprobado por
`architect`. `ux.md` lista los cuatro estados de cada pantalla (vacío, cargando, error, éxito) y una checklist WCAG
2.2 AA completa: "n/a: motivo" es una respuesta aceptable, el silencio no.

Bloqueo típico:

```
ERROR docs/changes/<id>/design.md: requires approval by one of roles ['tech-lead', 'architect']; a human approves with:
      python3 .harness/sdlc.pyz approve <id> design.md --as <username> --role tech-lead
ERROR docs/changes/<id>/ux.md: 'Booking list' does not define states ['empty'] (write 'n/a' if not applicable)
```

### `plan` — cada criterio trazado a un test

**Quién:** el agente. Recibo solo en `regulated`.

`plan.md` tiene una tabla de trazabilidad (cada `AC-n` y cada amenaza `T-n` hacia los tests que los cubren) y tareas
cuyo "done when" es un comando, no una opinión. La compuerta lee `spec.md` y compara:

```
ERROR docs/changes/<id>/plan.md: AC-3 from spec.md is missing in the traceability table
ERROR docs/changes/<id>/plan.md: AC-2 has no planned test
```

Se arregla agregando la fila, no borrando el criterio de `spec.md`. Aunque si el criterio realmente no debería
existir, se saca de ahí y se vuelve a aprobar la spec.

### `implement` — código, en commits chicos

**Quién:** el agente, con la revisión humana de siempre.

Acá miran dos sensores la historia de git, y solo corren con una referencia base (que es lo que pasa la CI):

```bash
python3 .harness/sdlc.pyz check --base origin/main
```

```
ERROR test-first: commit 4f2a9c1b23 'feat: export bookings' changes source before any test change
      (add tests first or a 'TDD-Waiver: <reason>' trailer)
ERROR weakened test: tests/test_export.py: added python skip/xfail: @pytest.mark.skip(reason="flaky")
      (fix the test or add a 'Test-Waiver: <reason>' trailer)
```

La vía de escape es un trailer de commit escrito por una persona, con un motivo. Antes de confiar en la
configuración, comprobá qué está mirando el sensor: los archivos fuera de tus globs le son invisibles.

```bash
python3 .harness/sdlc.pyz tdd --explain                          # todos los archivos, sin ocultar nada
python3 .harness/sdlc.pyz tdd --explain src/proxy.ts src/a.test.ts   # solo estos, y qué regla decidió
```

```
src/proxy.ts: source - matches source glob `src/**/*.ts`
README.md: other - matches no test glob and no source glob
```

### `verify` — evidencia, no afirmaciones

**Quién:** el agente ejecuta todo y lo registra; `tech-lead` aprueba en `regulated`.

`verification.md` registra los comandos y su salida real, una fila por criterio de aceptación, y los hallazgos de
los escáneres con su disposición. En la columna de evidencia, todo lo que va entre `comillas invertidas` se verifica,
así que tiene que ser una de tres cosas:

| Forma | Ejemplo | Qué hace la compuerta |
|---|---|---|
| un nombre de test — una oración sirve | `` `responde 200 con db ok en menos de 500 ms` `` | verifica que exista bajo `verification.test_paths` |
| una ruta del repositorio | `` `src/export.ts` ``, `` `tests/test_x.py::test_y` ``, `` `src/a.ts:12` `` | verifica que el archivo exista |
| un comando, marcado con `$ ` | `` `$ pnpm test:integration` `` | nada: un comando es tan inverificable como la prosa |

Cualquier otra cosa falla, y es a propósito: así se detecta la evidencia que no apunta a nada.

```
ERROR docs/changes/<id>/verification.md: AC-2 cites `sdlc tdd --explain`, which is not a test under
      verification.test_paths nor a file in the repository (write a command as `$ sdlc tdd --explain` if that is what it is)
ERROR docs/changes/<id>/verification.md: AC-4 cites `src/components/OldBanner.tsx`, which does not exist in the repository
```

Marcá el comando, corregí la ruta. **No saques las comillas invertidas para pasar la compuerta**: la prosa pasa
porque no se puede verificar, y eso deja la evidencia peor, no mejor.

El resultado tiene que ser `pass`, `verified` o `n/a`:

```
ERROR docs/changes/<id>/verification.md: AC-1 result is 'fail' (expected pass/verified/n/a, or blocked/pending with an owner and a reason)
```

**Cuando algo honestamente todavía no se puede verificar** —hace falta un permiso de administración, un entorno que
no existe— decilo en vez de inventar un resultado:

```
| AC-9 | blocked | blocked - owner: rita - hace falta un admin del repositorio para proteger la rama |
```

Sin dueño, la compuerta rechaza la excusa:

```
ERROR docs/changes/<id>/verification.md: AC-1 is 'blocked' and must name an owner and a reason,
      e.g. 'blocked - owner: rita - needs repository admin to protect the branch'
```

Con dueño, el registro se acepta como verdadero y la fase sigue sin avanzar, que es justamente el punto:

```
ERROR docs/changes/<id>/verification.md: AC-1 is blocked (owner: rita); verify cannot close until it passes,
      or record it as n/a with the reason
```

La evidencia de los escáneres es política, no intuición:

```bash
python3 .harness/sdlc.pyz evidence check
```

```
ERROR missing evidence 'sast': expected sdlc-evidence/sast*.sarif
ERROR trivy: high CVE-2026-1234 at package-lock.json: lodash 4.17.20 is vulnerable to prototype pollution
```

Si no podés arreglar un hallazgo ahora, no edites el archivo: proponé una excepción con vencimiento, que tiene que
aprobar un rol de seguridad.

```bash
python3 .harness/sdlc.pyz exception propose "CVE-2026-1234" "package-lock.json" --reason "arreglo upstream en 4.17.22, ISSUE-88" --days 30   # agente
python3 .harness/sdlc.pyz exception approve "CVE-2026-1234" "package-lock.json" --as sam --role security             # persona
```

Hasta que se apruebe no suprime nada, y `sdlc check` lo sigue diciendo.

### `review` — un segundo par de ojos que no escribió el código

**Quién:** una revisión con *contexto limpio* (una segunda sesión del agente, o una persona); `tech-lead` aprueba en
`regulated`.

Quien revisa no puede ser la sesión que implementó el cambio: todo el valor está en que no se convenció a sí misma
antes. En el ejemplo, acá se encontró un error de autorización real: el chequeo de permisos corría después de armar
la consulta. `review.md` registra el veredicto, los hallazgos por severidad y **qué no se revisó**.

### `release` — versión, digests, reversión

**Quién:** el agente prepara `release.md`; `release-manager` aprueba; la CI hace el resto al crear un tag.

```bash
git tag v1.4.0 && git push origin v1.4.0
```

El pipeline corre las compuertas sobre el commit etiquetado, tu `scripts/build-release` (ejecutable, sin argumentos,
todo lo publicable en `dist/`), un SBOM CycloneDX validado contra la política de licencias, procedencia SLSA,
attestation del SBOM y firmas keyless con Sigstore.

**La trampa en la que cae todo el mundo:** los digests recién existen después del build, pero `release.md` se aprobó
antes. No los dejes afuera para proteger el recibo: agregalos y que quien aprobó vea exactamente qué cambió.

```bash
python3 .harness/sdlc.pyz amend <id> release.md --as rita --role release-manager
```

Imprime el diff desde la aprobación y pide escribir `yes`. Se niega a correr sin terminal, así que un agente no
puede usarlo:

```
ERROR amend must be run by a human at a terminal; an agent cannot confirm an approval
```

### `operate` y `done` — ¿funcionó?

**Quién:** el agente mide; el `product-owner` aprueba `outcome.md` donde el perfil lo exige; `sre` es dueño de
`runbook.md` cuando el cambio declara `infra`.

`outcome.md` compara las métricas prometidas en `discovery.md` contra lo que pasó de verdad, y termina en `keep`,
`iterate`, `rollback` o `retire`. La compuerta verifica que cada métrica prometida esté reportada:

```
ERROR docs/changes/<id>/outcome.md: success metric 'exports per week' from discovery.md is not reported
```

Una métrica que no llegó a su objetivo no es un fallo del proceso. El ejemplo termina en `iterate`, con honestidad.

## 4. Fichas por rol

**Si sos `product-owner`:** te van a pedir que apruebes `discovery.md` (¿vale la pena?), `spec.md` (¿"terminado"
significa lo correcto?) y, al final, `outcome.md`. Todo tu repertorio es
`sdlc approve <id> <artefacto> --as <vos> --role product-owner`, más una revisión aprobatoria en el pull request. Si
el documento cambió después de que lo aprobaste, usá `sdlc amend` y leé el diff.

**Si sos `tech-lead`:** `spec.md`, `design.md` y, en `regulated`, `plan.md`, `verification.md` y `review.md`. Tu
trabajo real en la compuerta de `verification.md` es comprobar que la evidencia sea real: que los tests nombrados en
la tabla existan y que los comandos pegados produzcan esa salida.

**Si sos `architect`:** los ADRs y `design.md` de todo lo difícil de revertir. También aprobás las desviaciones de
la política de la organización: `sdlc deviation approve <clave> --as <vos> --role architect`.

**Si sos `security`:** `threat-model.md`, `data.md`, `ai-risk.md` y cada excepción a un hallazgo de escáner. Cada
excepción que aprobás tiene vencimiento, y cuando vence la compuerta se pone roja otra vez: eso es el diseño.

**Si sos `release-manager`:** `release.md`, y sos quien dice que una versión sale. Verificá que el procedimiento de
reversión se haya probado, no solo escrito.

**Si sos `platform`:** sos dueño de `sdlc init`, `sdlc upgrade`, el roster, CODEOWNERS (`sdlc codeowners --check` en
CI) y la configuración de CI. No aprobás artefactos; hacés posible que otros los aprueben.

**Si sos el agente:** escribís documentos y código, ejecutás `sdlc check`, `sdlc status`, `sdlc tdd --explain` y
`sdlc explain`, avanzás con `sdlc phase` y proponés desviaciones y excepciones. Te detenés y pedís cada aprobación.
Nunca escribís en `approvals.toml`.

## 5. Cuando te trabaste

El camino más rápido es pegarle el error al propio arnés:

```bash
python3 .harness/sdlc.pyz explain "approval by pat is stale (content changed); re-approve"
```

```
message: approval by pat is stale (content changed); re-approve
  cause: The artifact changed after it was approved, so the receipt no longer matches.
  fix: The approver reads the delta and confirms it in one step: python3 .harness/sdlc.pyz amend
       <id> <artifact> --as <user> --role <role>. Never drop true information from a document to
       protect its receipt.
```

`explain` también responde `sdlc explain design`, `sdlc explain spec.md`, `sdlc explain security`,
`sdlc explain receipt` y `sdlc explain separation-of-duties`. El catálogo completo de mensajes está en el
[recorrido](recorrido.md#7-cuándo-bloquea-una-compuerta), y el vocabulario en el [glosario](glosario.md).

## 6. Tres situaciones que no son fallos

| Situación | Qué hacer | Qué **no** hacer |
|---|---|---|
| Un criterio todavía no se puede verificar | `blocked - owner: <quién> - <qué tiene que pasar>` en `verification.md` | escribir `pass`, o `n/a` para algo simplemente no hecho |
| Un documento aprobado necesita un agregado verdadero | `sdlc amend`, quien aprobó lee el diff | dejar la información afuera para proteger el recibo |
| Un hallazgo o una política no se puede cumplir ahora | `sdlc exception propose` / `sdlc deviation propose`, con vencimiento, y después aprueba una persona | escribir el riesgo en prosa, donde nada lo hace caducar |
