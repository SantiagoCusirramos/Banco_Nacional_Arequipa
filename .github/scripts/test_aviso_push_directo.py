"""Pruebas del aviso de push directo, con una API de GitHub falsa."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import aviso_push_directo as aviso  # noqa: E402

REPO = "dueno/repo"


class ApiFalsa:
    """Responde GET desde un diccionario y anota cada escritura."""

    def __init__(self, prs=None, autores=None, issues=None, falla=False):
        self.prs = prs or {}          # sha -> lista de PR asociados
        self.autores = autores or {}  # sha -> {"login", "type"} o None
        self.issues = issues or []
        self.falla = falla
        self.escrituras = []

    def get(self, ruta, params=None):
        if self.falla:
            raise aviso.ErrorApi("sin red")
        partes = ruta.split("/")
        if ruta.endswith("/pulls"):
            return self.prs.get(partes[-2], [])
        if "/commits/" in ruta:
            sha = partes[-1]
            return {"sha": sha, "author": self.autores.get(sha),
                    "commit": {"author": {"name": "Nombre " + sha}, "message": "Mensaje " + sha}}
        if ruta.endswith("/issues"):
            pagina = (params or {}).get("page", 1)
            return self.issues if pagina == 1 else []
        raise AssertionError("ruta inesperada: " + ruta)

    def post(self, ruta, cuerpo):
        if self.falla:
            raise aviso.ErrorApi("sin red")
        self.escrituras.append((ruta, cuerpo))
        return {"number": 99, "html_url": "https://example.invalid/99"}


def evento(*shas):
    return {"after": shas[-1], "deleted": False, "commits": [{"id": s} for s in shas]}


def humano(login):
    return {"login": login, "type": "User"}


PR_FUSIONADO = [{"number": 5, "merged_at": "2026-11-16T00:00:00Z"}]
PR_ABIERTO = [{"number": 6, "merged_at": None}]


def test_merge_de_un_pr_no_avisa():
    api = ApiFalsa(prs={"a1": PR_FUSIONADO, "m1": PR_FUSIONADO}, autores={"a1": humano("ana")})
    assert aviso.procesar(api, REPO, evento("a1", "m1")) == {}
    assert api.escrituras == []


def test_commit_directo_abre_un_issue_que_menciona_al_autor():
    api = ApiFalsa(autores={"c1": humano("camila")})
    avisos = aviso.procesar(api, REPO, evento("c1"))
    assert avisos == {"camila": ["c1"]}
    assert len(api.escrituras) == 1
    ruta, cuerpo = api.escrituras[0]
    assert ruta == "/repos/dueno/repo/issues"
    assert cuerpo["title"] == "Push directo a main de camila"
    assert "@camila" in cuerpo["body"]
    assert "CONTRIBUTING.md" in cuerpo["body"]
    assert "c1" in cuerpo["body"]


def test_si_ya_hay_un_issue_abierto_comenta_en_el():
    abierto = {"number": 12, "title": "Push directo a main de camila"}
    otro_pr = {"number": 13, "title": "Push directo a main de camila", "pull_request": {}}
    api = ApiFalsa(autores={"c1": humano("camila")}, issues=[otro_pr, abierto])
    aviso.procesar(api, REPO, evento("c1"))
    assert [r for r, _ in api.escrituras] == ["/repos/dueno/repo/issues/12/comments"]
    assert "c1" in api.escrituras[0][1]["body"]


def test_un_aviso_por_autor():
    api = ApiFalsa(autores={"c1": humano("ana"), "c2": humano("beto"), "c3": humano("ana")})
    avisos = aviso.procesar(api, REPO, evento("c1", "c2", "c3"))
    assert avisos == {"ana": ["c1", "c3"], "beto": ["c2"]}
    titulos = sorted(c["title"] for _, c in api.escrituras)
    assert titulos == ["Push directo a main de ana", "Push directo a main de beto"]


def test_los_bots_no_reciben_aviso():
    api = ApiFalsa(autores={"b1": {"login": "dependabot[bot]", "type": "Bot"},
                            "b2": {"login": "otro[bot]", "type": "User"}})
    assert aviso.procesar(api, REPO, evento("b1", "b2")) == {}
    assert api.escrituras == []


def test_solo_cuentan_los_commits_que_no_son_de_un_pr_fusionado():
    api = ApiFalsa(prs={"p1": PR_FUSIONADO}, autores={"p1": humano("ana"), "c1": humano("camila")})
    assert aviso.procesar(api, REPO, evento("p1", "c1")) == {"camila": ["c1"]}


def test_un_pr_abierto_no_basta():
    api = ApiFalsa(prs={"c1": PR_ABIERTO}, autores={"c1": humano("camila")})
    assert aviso.procesar(api, REPO, evento("c1")) == {"camila": ["c1"]}


def test_simular_no_escribe():
    api = ApiFalsa(autores={"c1": humano("camila")})
    assert aviso.procesar(api, REPO, evento("c1"), simular=True) == {"camila": ["c1"]}
    assert api.escrituras == []


def test_main_nunca_termina_con_error(tmp_path, monkeypatch):
    ruta_evento = tmp_path / "evento.json"
    ruta_evento.write_text(json.dumps(evento("c1")))
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(ruta_evento))
    monkeypatch.setenv("GITHUB_REPOSITORY", REPO)
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    monkeypatch.setattr(aviso, "ClienteGitHub", lambda token: ApiFalsa(falla=True))
    assert aviso.main([]) == 0
