# Cómo contribuir

Este repositorio es el producto integrado del BNA. Lo que llega a `main` lo usa todo el equipo, así que cada cambio pasa por un pull request con la CI en verde.

## El flujo

1. **Una rama por cambio**, creada desde el `main` actual: `git switch -c <modulo>/<que-cambia> origin/main`.
2. **Pruebas.** Si el cambio modifica un comportamiento, primero la prueba que falla y después el código. Antes de abrir el PR, `./bna test` tiene que terminar en verde (ver [Pruebas](README.md#pruebas)).
3. **Pull request contra `main`**, con qué cambia, por qué y qué pruebas se corrieron. Para cerrar un issue, escribir `Closes #N` (GitHub no reconoce «Cierra»).
4. **CI en verde**: los flujos «CI» y, si toca el despliegue, «Kubernetes».
5. **Merge commit**, nunca squash ni rebase. Después se borra la rama.

## Lo que no se hace

- **No se sube nada directo a `main`.** Eso incluye «Add files via upload» desde la web: en ese formulario hay que elegir «Create a new branch for this commit and start a pull request». Cada push directo abre un aviso automático para su autor (`.github/workflows/aviso-push-directo.yml`). El aviso no revierte nada.
- No se versionan claves (`.env`), datos personales reales, documentos de la empresa ni archivos generados como registros o resultados de pruebas. La CI falla si aparece un archivo de claves.
- No se edita `database/`. La base integrada vive en [bna-core-db](https://github.com/miguelpro324/bna-core-db): el cambio va allá, sale con una etiqueta nueva y llega aquí con `git subtree pull` (ver [`database/README-UPSTREAM.md`](database/README-UPSTREAM.md)).
- Ningún módulo se conecta a la base integrada: todo dato del CORE se lee y se escribe por COREDB (`backend/COREDB`), a través del Bus de Servicios. Un módulo nuevo no tiene base propia; las dos excepciones de hoy, SOL (`bna_sol_mvp` en `db-aux`) y el prototipo de Seguridad (SQLite), no se conectan con el CORE.

## Un módulo nuevo

- Va en `backend/<MODULO>` (y sus pantallas en `frontend/app/<modulo>`), con su README, sus pruebas y un puerto libre (ver [Servicios y puertos](README.md#servicios-y-puertos)).
- Se agrega a `compose.yaml`, a `./bna test` (`scripts/pruebas.sh`), a los manifiestos de `k8s/` y al Bus de Servicios: su ruta en `MODULOS` (`backend/BUS_SERVICIOS/config.py`) y su `BUS_URL_<MÓDULO>`; si llama a otros módulos, también como consumidor (`BUS_CONSUMIDORES` y su `BUS_TOKEN_<MÓDULO>` en `.env.example`). Ver [`backend/BUS_SERVICIOS/README.md`](backend/BUS_SERVICIOS/README.md).
- Si a COREDB o a la base le falta algo, se pide en un issue o en el PR. Se implementa ahí y luego se integra el módulo.

## Trabajo de otra persona

Para seguir el trabajo de alguien que todavía no se fusionó: una rama nueva basada en la suya (nunca se empuja a su rama), con un `Co-authored-by: <id>+<login>@users.noreply.github.com` por cada autor. El PR la menciona.
