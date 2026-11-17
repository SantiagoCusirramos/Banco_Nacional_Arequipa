"""Avisa cuando un commit llega a main sin pasar por un PR.

Corre en cada push a main (`.github/workflows/aviso-push-directo.yml`). Para cada
commit del push pregunta a GitHub si pertenece a un PR fusionado. Si el último
commit es de un PR fusionado (el merge de un PR), no hace nada. Por cada autor con
commits directos abre el issue «Push directo a main de <login>», o comenta en el que
ya tenga abierto. No revierte nada y nunca termina con error.

Solo biblioteca estándar. Simulación de solo lectura, sin escribir en GitHub:
    GITHUB_TOKEN=... python3 aviso_push_directo.py --simular --repo dueno/repo --sha <sha>
"""

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
TITULO = "Push directo a main de {login}"
MAX_PAGINAS = 10


class ErrorApi(Exception):
    pass


class ClienteGitHub:
    def __init__(self, token):
        self.token = token

    def _pedir(self, metodo, ruta, params=None, cuerpo=None):
        url = API + ruta
        if params:
            url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        cabeceras = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "bna-aviso-push-directo",
        }
        if self.token:
            cabeceras["Authorization"] = f"Bearer {self.token}"
        pedido = urllib.request.Request(url, data=datos, method=metodo, headers=cabeceras)
        try:
            with urllib.request.urlopen(pedido, timeout=20) as respuesta:
                return json.loads(respuesta.read() or b"null")
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            raise ErrorApi(f"{metodo} {ruta}: {error}") from error

    def get(self, ruta, params=None):
        return self._pedir("GET", ruta, params=params)

    def post(self, ruta, cuerpo):
        return self._pedir("POST", ruta, cuerpo=cuerpo)


def commits_del_push(evento):
    if evento.get("deleted"):
        return []
    shas = [c["id"] for c in evento.get("commits") or [] if c.get("id")]
    if not shas and evento.get("after"):
        shas = [evento["after"]]
    return shas


def de_un_pr_fusionado(api, repo, sha):
    prs = api.get(f"/repos/{repo}/commits/{sha}/pulls") or []
    return any(pr.get("merged_at") for pr in prs)


def es_bot(autor):
    return autor.get("type") == "Bot" or autor.get("login", "").endswith("[bot]")


def issue_abierto(api, repo, titulo):
    for pagina in range(1, MAX_PAGINAS + 1):
        issues = api.get(f"/repos/{repo}/issues",
                         {"state": "open", "per_page": 100, "page": pagina}) or []
        for issue in issues:
            if "pull_request" not in issue and issue.get("title") == titulo:
                return issue["number"]
        if len(issues) < 100:
            return None
    return None


def lista_de_commits(repo, commits):
    return "\n".join(f"- [`{sha[:7]}`](https://github.com/{repo}/commit/{sha}) {mensaje}"
                     for sha, mensaje in commits)


def cuerpo_issue(repo, login, commits):
    return (
        f"Hola @{login} 👋\n\n"
        "Estos commits llegaron a `main` sin pasar por un pull request:\n\n"
        f"{lista_de_commits(repo, commits)}\n\n"
        "No se revirtió nada. Para los próximos cambios, por favor sigue el flujo de "
        f"[CONTRIBUTING.md](https://github.com/{repo}/blob/main/CONTRIBUTING.md): una rama, "
        "un PR y la CI en verde antes del merge. Eso vale también para «Add files via upload» "
        "desde la web: GitHub ofrece «Create a new branch for this commit and start a pull "
        "request» en el mismo formulario.\n\n"
        "_Aviso automático de `.github/workflows/aviso-push-directo.yml`._"
    )


def cuerpo_comentario(repo, commits):
    return ("Llegaron más commits directos a `main`:\n\n"
            f"{lista_de_commits(repo, commits)}\n\n"
            f"Recuerda el flujo de [CONTRIBUTING.md](https://github.com/{repo}/blob/main/CONTRIBUTING.md).")


def procesar(api, repo, evento, simular=False):
    """Devuelve {login: [sha, ...]} con los commits directos de cada autor."""
    shas = commits_del_push(evento)
    if not shas or de_un_pr_fusionado(api, repo, shas[-1]):
        print("Ningún commit directo: el último commit del push es de un PR fusionado.")
        return {}

    por_autor, mensajes = {}, {}
    for sha in shas:
        if de_un_pr_fusionado(api, repo, sha):
            continue
        datos = api.get(f"/repos/{repo}/commits/{sha}")
        autor = datos.get("author")
        if not autor or not autor.get("login") or es_bot(autor):
            continue
        por_autor.setdefault(autor["login"], []).append(sha)
        mensaje = (datos.get("commit") or {}).get("message", "")
        mensajes[sha] = mensaje.splitlines()[0] if mensaje else ""

    for login, suyos in por_autor.items():
        commits = [(sha, mensajes[sha]) for sha in suyos]
        titulo = TITULO.format(login=login)
        numero = issue_abierto(api, repo, titulo)
        if simular:
            destino = f"comentaría en #{numero}" if numero else f"abriría «{titulo}»"
            print(f"{login}: {len(suyos)} commit(s) directo(s); {destino}.")
            continue
        if numero:
            api.post(f"/repos/{repo}/issues/{numero}/comments",
                     {"body": cuerpo_comentario(repo, commits)})
            print(f"{login}: comentario en #{numero}.")
        else:
            creado = api.post(f"/repos/{repo}/issues",
                              {"title": titulo, "body": cuerpo_issue(repo, login, commits)})
            print(f"{login}: issue #{creado.get('number')} abierto.")
    if not por_autor:
        print("Ningún commit directo de una persona.")
    return por_autor


def leer_argumentos(argv):
    opciones = {"simular": "--simular" in argv, "repo": None, "sha": None}
    for nombre in ("repo", "sha"):
        bandera = f"--{nombre}"
        if bandera in argv and argv.index(bandera) + 1 < len(argv):
            opciones[nombre] = argv[argv.index(bandera) + 1]
    return opciones


def main(argv):
    try:
        opciones = leer_argumentos(argv)
        repo = opciones["repo"] or os.environ["GITHUB_REPOSITORY"]
        if opciones["sha"]:
            evento = {"after": opciones["sha"], "commits": [{"id": opciones["sha"]}]}
        else:
            with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as archivo:
                evento = json.load(archivo)
        api = ClienteGitHub(os.environ.get("GITHUB_TOKEN", ""))
        procesar(api, repo, evento, simular=opciones["simular"])
    except Exception as error:  # el aviso nunca debe romper el push
        print(f"::warning::No se pudo revisar el push: {error}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
