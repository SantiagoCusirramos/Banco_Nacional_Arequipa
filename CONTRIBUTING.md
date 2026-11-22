# Cómo contribuir

Este repositorio es el producto integrado del BNA. Lo que llega a `main` lo usa todo el equipo, así que cada cambio pasa por un pull request con la CI en verde.

## El flujo

1. **Una rama por cambio**, creada desde el `main` actual: `git switch -c <modulo>/<que-cambia> origin/main`.
2. **Pruebas.** Si el cambio modifica un comportamiento, primero la prueba que falla y después el código. Antes de abrir el PR, `./bna test` tiene que terminar en verde (ver [Pruebas](README.md#pruebas)).
3. **Pull request contra `main`**, con qué cambia, por qué y qué pruebas se corrieron. Para cerrar un issue, escribir `Closes #N` (GitHub no reconoce «Cierra»).
4. **CI en verde**: los flujos «CI» y, si toca el despliegue, «Kubernetes».
5. **Merge commit**, nunca squash ni rebase. Después se borra la rama.

## Trabajar en paralelo

Varias personas o agentes pueden trabajar a la vez en la misma máquina, cada uno en su worktree, sin cruzarse:

```bash
git worktree add -b <modulo>/<que-cambia> ../bna-<que-cambia> origin/main
cd ../bna-<que-cambia>
./bna test                            # proyecto propio: bna-prueba-<rama>-<pid>
BNA_PROYECTO=bna-<que-cambia> ./bna up   # una copia del producto para probar a mano
BNA_PROYECTO=bna-<que-cambia> ./bna smoke
BNA_PROYECTO=bna-<que-cambia> ./bna down -v
```

- `BNA_PROYECTO` es el proyecto de Compose: contenedores, redes y volúmenes llevan su nombre, y `./bna down -v` solo borra los suyos. Por omisión es `bna`, el producto de uso diario.
- `BNA_ETIQUETA_LOCAL` es la etiqueta de las imágenes `bna/*` (por omisión `local`). `./bna test` usa el nombre de su proyecto, así que dos corridas no construyen sobre la misma imagen, y borra sus etiquetas al terminar.
- `./bna test` no publica puertos en la máquina (`compose.sin-puertos.yaml`): las suites y el flujo corren dentro de las redes de Compose, y la base de cada suite de integración toma un puerto libre. Se niega a usar el proyecto `bna` y cualquier proyecto que ya tenga contenedores o volúmenes.
- Una copia levantada con `./bna up` sí publica puertos. Para dos a la vez, cambie también los `BNA_PUERTO_*` en el `.env` de uno de los worktrees.
- kind: `./bna k8s-up` crea el clúster con el nombre del proyecto. El clúster `bna` publica sus puertos; uno con otro nombre no, y `k8s-smoke` corre igual dentro del clúster. `scripts/prueba_k8s_infra_kind.sh` usa `<proyecto>-infra` y reenvía a puertos libres.
- La limpieza solo toca lo que cada corrida creó. No use `docker system prune` ni `docker volume rm` sobre lo que no es suyo.

## Lo que no se hace

- **No se sube nada directo a `main`.** Eso incluye «Add files via upload» desde la web: en ese formulario hay que elegir «Create a new branch for this commit and start a pull request». Cada push directo abre un aviso automático para su autor (`.github/workflows/aviso-push-directo.yml`). El aviso no revierte nada.
- No se versionan claves (`.env`), datos personales reales, documentos de la empresa ni archivos generados como registros o resultados de pruebas. La CI falla si aparece un archivo de claves.
- No se edita `database/`. La base integrada vive en [bna-core-db](https://github.com/miguelpro324/bna-core-db): el cambio va allá, sale con una etiqueta nueva y llega aquí con `git subtree pull` (ver [`database/README-UPSTREAM.md`](database/README-UPSTREAM.md)).
- Ningún módulo se conecta a la base integrada: todo dato del CORE se lee y se escribe por COREDB (`backend/COREDB`), a través del Bus de Servicios. Ningún módulo tiene base propia, y uno nuevo tampoco.

## Un módulo nuevo

- Va en `backend/<MODULO>` (y sus pantallas en `frontend/app/<modulo>`), con su README, sus pruebas y un puerto libre (ver [Servicios y puertos](README.md#servicios-y-puertos)).
- Se agrega a `compose.yaml`, a `./bna test` (`scripts/pruebas.sh`), a los manifiestos de `k8s/` y al Bus de Servicios: su ruta en `MODULOS` (`backend/BUS_SERVICIOS/config.py`) y su `BUS_URL_<MÓDULO>`; si llama a otros módulos, también como consumidor (`BUS_CONSUMIDORES` y su `BUS_TOKEN_<MÓDULO>` en `.env.example`). Ver [`backend/BUS_SERVICIOS/README.md`](backend/BUS_SERVICIOS/README.md).
- Si a COREDB o a la base le falta algo, se pide en un issue o en el PR. Se implementa ahí y luego se integra el módulo.

## Trabajo de otra persona

Para seguir el trabajo de alguien que todavía no se fusionó: una rama nueva basada en la suya (nunca se empuja a su rama), con un `Co-authored-by: <id>+<login>@users.noreply.github.com` por cada autor. El PR la menciona.
