"""La pregunta del comprobante (hallazgo M6 de la prueba «solo con el mouse»): el botón «No»
llevaba al menú sin decirlo y la pantalla no dejaba claro que la operación ya había terminado.

Las pruebas leen la pantalla estática, igual que test_pantalla_y_sesion.py.
"""
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "static"


def pantalla_comprobante():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    return html.split("function preguntarRecibo")[1].split("\n}")[0]


def test_la_pantalla_del_comprobante_dice_que_la_operacion_termino():
    bloque = pantalla_comprobante()
    assert "¿Desea comprobante?" in bloque
    assert "Operación terminada" in bloque
    assert "operación ya terminó" in bloque


def test_el_no_del_comprobante_dice_que_vuelve_al_menu():
    bloque = pantalla_comprobante()
    assert "No, volver al menú" in bloque
    assert "siguiente" in bloque
