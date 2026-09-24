# Notas de actualización

*English: [Upgrade notes](../en/upgrading.md).*

Qué cambia para un repositorio que ya usa el arnés. Acá aparecen solo las versiones con consecuencias para vos; la
lista completa de cambios está en el [changelog](https://github.com/huanrasan/sdlc-harness/blob/main/CHANGELOG.md).

Actualizar son siempre los mismos dos comandos, y nada se aplica hasta que lo fusionás:

```bash
pipx upgrade sdlc-harness && sdlc upgrade --dry-run   # revisar primero
sdlc upgrade                                          # después aplicar
```

`sdlc upgrade` necesita las plantillas, así que se ejecuta desde el paquete instalado o desde `sdlc-full.pyz`. El
`.harness/sdlc.pyz` que vive en tu repositorio viene sin ellas a propósito: corre las compuertas, no instala.

## De 0.7.4 a 0.7.5

**Los `.sdlc-new` van a aparecer una última vez.** Antes de 0.7.5, integrar un `.sdlc-new` y borrarlo no quedaba
registrado: el upgrade conservaba la plantilla anterior como base del merge, así que cada upgrade siguiente volvía a
ofrecer los mismos archivos, aunque el release no los hubiera tocado. Tu manifest todavía tiene esas bases viejas,
así que este upgrade ofrece tus archivos personalizados una vez más. Quedate con tu versión (o integrá, si la
plantilla cambió de verdad), borrá los `.sdlc-new`, y desde ahí un archivo solo se ofrece cuando su plantilla cambia.

## De 0.7.2 a 0.7.3

Nada que pasaba antes puede fallar ahora: el chequeo de evidencia prueba primero la regla vieja. Lo que cambia es lo
que ya no tenés que esquivar.

- **Volvé a poner las comillas invertidas.** Si reescribiste evidencia en prosa porque los comandos y las rutas entre
  `comillas invertidas` fallaban la compuerta, restauralas. Las rutas ahora se verifican; los comandos se aceptan
  marcados como `$ pnpm test`. Lo que no es test ni archivo y no está marcado sigue fallando, con un mensaje que
  dice cómo marcarlo.
- **`sdlc tdd --explain <ruta> ...`** responde por archivos concretos y nombra el glob que decidió cada uno. El
  listado completo ya no se trunca.
- **Los criterios en español ya no generan warning.** `Dado/Cuando/Entonces` y `debe` cuentan como criterios
  estructurados.

## De 0.6.x a 0.7.x

### Cuatro cosas que pueden poner tu pipeline en rojo

**1. Un job `workflows` nuevo ejecuta actionlint y zizmor.** El arnés ya exigía fijar las acciones por SHA de commit
y no interpolar contexto no confiable dentro de bloques `run:`; este job es lo que de verdad lo verifica. En un
repositorio existente suele encontrar algo la primera vez. Los dos hallazgos más comunes son un `checkout` sin
`persist-credentials: false` (el token queda en `.git/config` para todos los pasos siguientes) y `${{ ... }}` dentro
de un `run:` (una inyección de shell cuando el valor viene de un pull request). Los dos son reales. Si necesitás
fusionar la actualización antes de arreglarlos, borrá el job de `.github/workflows/sdlc-gates.yml` y volvé a
ponerlo cuando puedas, o dejalo y registrá lo que no podés arreglar ahora con
`sdlc exception propose <regla> <ruta> --reason "..." --days 30`.

**2. Los runners autoalojados necesitan la versión 2.327.1 o posterior.** Las acciones actualizadas (`checkout` 7,
`setup-python` 7, `upload-artifact` 7, `download-artifact` 8, `dependency-review` 5) corren sobre Node 24. Los
runners hospedados por GitHub ya lo cumplen; una flota propia puede que no, y el mensaje de error habla del runner,
no del arnés.

**3. Tus globs de fuente pueden empezar a cubrir más archivos.** `tdd.source_globs` y `verification.test_paths`
siguen la semántica de git: `**` abarca cualquier cantidad de directorios *incluyendo ninguno*, y `*` no cruza una
barra. Antes de 0.7, `src/**/*.ts` no casaba `src/proxy.ts` en silencio, así que los archivos en la raíz de un
directorio quedaban clasificados como `other` y el sensor test-first los ignoraba. Ahora quedan cubiertos, que es el
punto, pero significa que el sensor puede empezar a reportar commits que antes dejaba pasar. Ejecutá
`sdlc tdd --explain` antes de subir: imprime cómo queda clasificado cada archivo versionado y avisa cuando hay
código que sigue fuera de los globs. Si escribiste `src/*.ts` y `src/**/*.ts` para esquivar el comportamiento viejo,
ahora alcanza con el segundo patrón.

**4. Los bundles de firma publicados cambian de formato.** Los releases se firman con
`cosign sign-blob --new-bundle-format`, que es el bundle actual de Sigstore. Quien verifique con cosign 3 usa la
receta de la cabecera del workflow sin cambios; quien siga en cosign 2.x tiene que agregar `--new-bundle-format` a
`verify-blob`. Los bundles publicados antes de la actualización no se tocan y siguen verificándose como antes, así
que avisá a quien consume tus artefactos a partir de qué release cambia el formato.

### Si sos la única persona que mantiene el repositorio, activá la firma de commits

`separation_of_duties = false` estaba documentado pero era inalcanzable: `sdlc approvals verify` exigía una revisión
aprobatoria de la misma persona nombrada en el recibo, y GitHub no permite aprobar tu propio pull request. Todo pull
request que agregaba un recibo fallaba.

Desde 0.7, con la separación de funciones desactivada, una firma de commit que la plataforma verifica reemplaza esa
revisión. El recibo tiene que llegar en un commit firmado por quien aprueba. Se configura una sola vez, antes de tu
próxima aprobación:

```bash
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
git config commit.gpgsign true
```

Después hay que agregar esa clave pública en GitHub, en Settings → SSH and GPG keys, **como signing key**. Una clave
de autenticación con el mismo contenido no sirve; la API las reporta por separado y el check va a seguir fallando.
Si son más de una persona, dejá `separation_of_duties = true`, que sigue siendo el valor por defecto y sigue
exigiendo la revisión.

**Después elegí cómo se mergean los pull requests, porque uno de los métodos tira la firma.** El *Rebase and merge*
de GitHub reescribe cada commit sobre `main`, y los commits reescritos quedan sin firma. La compuerta del arnés no se
ve afectada —verifica la firma dentro del pull request, y los commits originales firmados quedan asociados al pull
request en GitHub—, pero `main` deja de mostrar quién firmó cada aprobación, y una auditoría que lea solo `main` no
encuentra nada. Qué deja cada método en `main`:

| Método | Firma en `main` | Historial |
|---|---|---|
| Rebase and merge | ninguna | lineal |
| Squash and merge | la clave de GitHub, con vos como autor | lineal, un commit por pull request |
| Create a merge commit | **la tuya, en cada commit original** | con commits de merge |

Y convertí la elección en configuración, en vez de algo que hay que recordar en cada pull request:

1. En Settings → General, desactivá **Allow rebase merging**.
2. En la protección de rama de `main`, activá **Require signed commits**. GitHub rechaza entonces cualquier cosa sin
   firmar que llegue a `main`. El squash y los merge commits los firma GitHub, igual que los de Dependabot, así que
   siguen pasando.

Si `main` además tiene **Require linear history**, los merge commits se rechazan y el squash es el único método que
queda que mantiene `main` firmado. Es una combinación sólida: la firma propia de quien aprueba se verificó en el pull
request, y ahí queda.

### Lo que ganás

- **`sdlc amend <cambio> <artefacto> --as <usuario> --role <rol>`** le muestra a quien aprobó qué cambió desde su
  aprobación y registra un recibo nuevo en un solo paso. Usalo en vez de reaprobar a ciegas, y dejá de sacar
  información verdadera de un documento aprobado para proteger su recibo: agregá los digests publicados a
  `release.md` y enmendá.
- **Resultados `blocked` y `pending` en `verification.md`**, cuando nombran dueño y motivo, como en
  `blocked - owner: rita - hace falta un admin del repositorio para proteger la rama`. La compuerta sigue en rojo y
  la fase no avanza, pero el registro ya no obliga a elegir entre estancarse y escribir algo falso.
- **`sdlc deviation propose` y `sdlc exception propose`** permiten que un agente registre un riesgo aceptado con
  vencimiento, en estado pendiente que no suprime nada hasta que una persona con rol autorizado ejecuta el
  `approve` correspondiente. El riesgo que antes terminaba como un párrafo en un documento ahora caduca solo.
- **`sdlc check --staged`**, que usa el hook de pre-commit, valida únicamente los change records que toca el commit.
- **`[release] sbom_source` en `harness.toml`** decide qué escanea Syft. `dir:dist` inventaría archivos; un release
  en contenedor necesita `docker-archive:dist/<imagen>.tar`. Escanear una imagen guardada como si fuera un
  directorio produce un SBOM del tarball, y entonces la política de licencias no verifica nada.
- **`sdlc status` y `sdlc explain`** (desde 0.6) dicen qué bloquea cada cambio y qué significa cualquier mensaje de
  compuerta. `sdlc explain "<el error que te salió>"` suele ser más rápido que leer la documentación.

### Nada que hacer

Los recibos de aprobación, los logs de auditoría, los change records y los perfiles no cambian. `sdlc upgrade`
conserva cada archivo que personalizaste y escribe `<archivo>.sdlc-new` al lado de aquellos donde vos y el release
cambiaron lo mismo.
