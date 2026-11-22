"""Varias copias de `./bna test` a la vez (por ejemplo, desde dos worktrees) no se cruzan.

Cada corrida usa su propio proyecto de Compose (BNA_PROYECTO), sus propias etiquetas de imagen
(BNA_ETIQUETA_LOCAL), ningún puerto del anfitrión (compose.sin-puertos.yaml) y su propio clúster
de kind. Aquí se comprueba en los archivos que nada quedó fijo; la corrida comprueba además con
`docker compose config` (suite "Aislamiento de la corrida" de scripts/pruebas.sh).

Corre en la imagen del backend con el repositorio montado en REPO: `./bna test`.
"""
import os
import re
from pathlib import Path

REPO = Path(os.environ.get("REPO", Path(__file__).resolve().parent.parent))
ETIQUETA = "${BNA_ETIQUETA_LOCAL:-local}"
# Imagen local del producto escrita con su etiqueta fija.
IMAGEN_FIJA = re.compile(r"\bbna/[a-z-]+:local\b")


def _texto(ruta):
    return (REPO / ruta).read_text(encoding="utf-8")


def _servicios(texto):
    """Servicios de un archivo de Compose con su bloque de texto (sangría de dos espacios)."""
    bloque = texto.split("\nservices:\n", 1)[1]
    bloque = re.split(r"\n(?=\S)", bloque, maxsplit=1)[0]
    partes = re.split(r"\n  (?=[a-z][a-z0-9-]*:\n)", "\n" + bloque)
    servicios = {}
    for parte in partes:
        parte = parte.strip("\n")
        if not parte:
            continue
        nombre, _, cuerpo = parte.partition(":\n")
        servicios[nombre.strip()] = cuerpo
    return servicios


def test_las_imagenes_del_producto_llevan_la_etiqueta_por_proyecto():
    texto = _texto("compose.yaml")
    imagenes = re.findall(r"image:\s*(bna/\S+)", texto)
    assert imagenes, "compose.yaml no tiene imágenes bna/"
    fijas = [imagen for imagen in imagenes if not imagen.endswith(":" + ETIQUETA)]
    assert fijas == [], f"Imágenes sin {ETIQUETA}: {fijas}"


def test_el_modo_sin_puertos_quita_todos_los_puertos_publicados():
    con_puertos = {
        nombre for nombre, cuerpo in _servicios(_texto("compose.yaml")).items() if "\n    ports:" in "\n" + cuerpo
    }
    assert con_puertos, "compose.yaml no publica puertos: revisar esta prueba"
    sin = _servicios(_texto("compose.sin-puertos.yaml"))
    reseteados = {nombre for nombre, cuerpo in sin.items() if re.search(r"ports:\s*!reset\s*\[\]", cuerpo)}
    assert con_puertos - reseteados == set(), f"Servicios con puertos que el modo prueba no quita: {con_puertos - reseteados}"
    assert reseteados - con_puertos == set(), f"compose.sin-puertos.yaml nombra servicios sin puertos: {reseteados - con_puertos}"


def test_los_scripts_de_pruebas_y_kind_no_fijan_etiquetas():
    for ruta in ("scripts/pruebas.sh", "scripts/k8s.sh", "scripts/k8s-infra.sh"):
        fijas = IMAGEN_FIJA.findall(_texto(ruta))
        assert fijas == [], f"{ruta} usa etiquetas fijas: {fijas}"


def test_el_proyecto_y_el_cluster_salen_de_bna_proyecto():
    bna = _texto("bna")
    assert re.search(r'COMPOSE_PROJECT_NAME="\$\{?BNA_PROYECTO', bna), "bna no toma el proyecto de BNA_PROYECTO"
    assert "CLUSTER=bna\n" not in _texto("scripts/k8s.sh"), "k8s.sh fija el nombre del clúster"
    assert re.search(r"BNA_PROYECTO", _texto("scripts/prueba_k8s_infra_kind.sh"))


def test_la_corrida_de_pruebas_usa_su_propio_proyecto_y_no_publica_puertos():
    pruebas = _texto("scripts/pruebas.sh")
    assert "BNA_PROYECTO" in pruebas
    # El producto de `./bna up` (proyecto bna) nunca es el de una corrida.
    assert re.search(r'if \[ "\$BNA_PROYECTO" = bna \]; then', pruebas)
    # bna no le pasa su valor por omisión (bna) a `./bna test`: dos corridas acabarían en el mismo.
    bna = _texto("bna")
    assert bna.index('exec scripts/pruebas.sh') < bna.index('BNA_PROYECTO="${BNA_PROYECTO:-bna}"')
    assert "compose.sin-puertos.yaml" in pruebas
    # Las suites de integración de los módulos publicaban la base en un puerto fijo (3327…3332).
    for modulo in ("COREDB", "EVALUACION", "DESEMBOLSO", "COBRANZA", "CAPTACION", "SEGURIDAD"):
        assert re.search(rf"{modulo}_PUERTO_PRUEBAS=0\b", pruebas), f"{modulo}: la base de sus pruebas usa un puerto fijo"


def test_el_reenvio_de_kind_no_usa_puertos_fijos():
    texto = _texto("scripts/prueba_k8s_infra_kind.sh")
    assert not re.search(r"reenviar \w+ \d+:\d+", texto), "port-forward con puerto local fijo"
