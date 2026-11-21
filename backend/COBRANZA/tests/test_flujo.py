"""Cobrar una cuota contra COREDB y la base integrada reales.

El crédito existe desde la confirmación del desembolso: Cobranza solo lo lee (CR-INT-06). El
operador paga con su propio token, que Cobranza reenvía; COREDB debita la cuenta, aplica el pago
y recalcula el crédito en una sola operación. La misma referencia no cobra dos veces y las rutas
que usa la pantalla conservan la forma anterior.
"""
from datetime import date

from COBRANZA.tests.ayudas import abrir_cuenta, atrasar_cuotas, cabeceras, coredb, pago_legacy, pago_nuevo, saldo


def _monto_cuota(cuota: dict) -> str:
    return cuota["saldoPendiente"]


def test_consulta_del_credito_y_rutas_de_la_pantalla(api, operador, credito):
    token = operador[0]
    lista = api.get("/api/v1/creditos", params={"codCliente": credito["codCliente"]}, headers=cabeceras(token))
    assert lista.status_code == 200, lista.text
    [resumen] = lista.json()
    assert (resumen["codCredito"], resumen["codCliente"], resumen["estado"]) == (
        credito["codCredito"], credito["codCliente"], "AL_DIA")

    detalle = api.get(f"/api/v1/creditos/{credito['codCredito']}", headers=cabeceras(token))
    assert detalle.status_code == 200, detalle.text
    d = detalle.json()
    assert (d["montoDesembolsado"], d["numeroCuotas"], len(d["cuotas"])) == ("1200.00", 3, 3)
    assert float(d["saldoPendiente"]) == sum(float(c["saldoPendiente"]) for c in d["cuotas"])

    # La pantalla sigue encontrando el crédito con su cronograma y lo que toca pagar hoy.
    legacy = api.get(f"/clientes/{credito['codCliente']}/creditos", headers=cabeceras(token))
    assert legacy.status_code == 200, legacy.text
    [c] = legacy.json()
    assert (c["codCredito"], c["idCliente"], c["montoAprobado"], c["estadoCredito"]) == (
        credito["codCredito"], credito["codCliente"], "1200.00", "AL_DIA")
    assert len(c["cuotas"]) == 3 and c["cuotas"][0]["idCuota"] == f"{credito['codCredito']}-1"

    monto = api.get(f"/creditos/{credito['codCredito']}/monto-a-pagar", headers=cabeceras(token))
    assert monto.status_code == 200, monto.text
    m = monto.json()
    assert (m["numeroCuota"], m["saldoCapital"], m["moraVigente"]) == (1, d["cuotas"][0]["saldoPendiente"], "0.00")
    assert m["totalAPagar"] == m["saldoCapital"]

    assert api.get("/api/v1/creditos/CRE-NO-EXISTE", headers=cabeceras(token)).status_code == 404
    assert api.get("/api/v1/creditos", params={"estado": "OTRO"}, headers=cabeceras(token)).status_code == 422


def test_pago_confirmado_idempotente_y_comprobante(api, admin, operador, credito):
    token = operador[0]
    cuota = credito["cuotas"][0]
    monto = _monto_cuota(cuota)
    antes = saldo(admin, credito["numCuenta"])

    referencia = "PAGO-COB-0001"
    pago = pago_nuevo(api, token, credito["codCredito"], credito["numCuenta"], monto, referencia)
    assert pago.status_code == 201, pago.text
    p = pago.json()
    assert (p["estado"], p["referencia"], p["monto"], p["numCuenta"], p["canal"]) == (
        "CONFIRMADO", referencia, monto, credito["numCuenta"], "VEN")
    assert p["motivo"] is None and p["uuidTransaccion"]
    assert [(a["numeroCuota"], a["montoAplicado"]) for a in p["aplicaciones"]] == [(1, monto)]
    assert saldo(admin, credito["numCuenta"]) == f"{float(antes) - float(monto):.2f}"

    # El mismo cuerpo con la misma referencia devuelve el mismo pago, sin otro débito.
    otra = pago_nuevo(api, token, credito["codCredito"], credito["numCuenta"], monto, referencia)
    assert otra.status_code == 200, otra.text
    assert otra.json()["idPago"] == p["idPago"]
    assert saldo(admin, credito["numCuenta"]) == f"{float(antes) - float(monto):.2f}"

    # Otra referencia con otro contenido bajo la misma llave es un conflicto.
    conflicto = pago_nuevo(api, token, credito["codCredito"], credito["numCuenta"], "1.00", referencia)
    assert conflicto.status_code == 409 and conflicto.json()["error"]["code"] == "IDEMPOTENCIA_CONFLICTO"

    comprobante_nuevo = api.get(f"/api/v1/pagos/{referencia}", headers=cabeceras(token))
    assert comprobante_nuevo.status_code == 200
    assert comprobante_nuevo.json()["idPago"] == p["idPago"]

    comprobante = api.get(f"/pagos/{referencia}/comprobante", headers=cabeceras(token))
    assert comprobante.status_code == 200, comprobante.text
    c = comprobante.json()
    assert (c["numeroOperacion"], c["cuotaNumero"], c["montoPagado"]) == (referencia, 1, monto)
    assert (c["montoAplicadoMora"], c["montoAplicadoCapital"]) == ("0.00", monto)
    assert float(c["saldoRestanteCredito"]) > 0

    detalle = api.get(f"/api/v1/creditos/{credito['codCredito']}", headers=cabeceras(token)).json()
    assert detalle["cuotas"][0]["estado"] == "PAGADA"
    assert detalle["cuotasPagadas"] == 1


def test_el_pago_de_la_pantalla_usa_la_ruta_anterior(api, admin, operador, credito):
    token = operador[0]
    monto = _monto_cuota(credito["cuotas"][0])
    antes = saldo(admin, credito["numCuenta"])
    referencia = "HB-COB-0001"

    r = pago_legacy(api, token, {"codCliente": credito["codCliente"], "codCredito": credito["codCredito"],
                                 "montoPago": monto, "numCuenta": credito["numCuenta"]}, referencia)
    assert r.status_code == 201, r.text
    resultado = r.json()
    assert (resultado["referenciaTransaccion"], resultado["estado"], resultado["idempotente"]) == (
        referencia, "CONFIRMADO", False)
    assert (resultado["montoPago"], resultado["idCanal"], resultado["codCredito"]) == (monto, "HB", credito["codCredito"])
    assert resultado["motivo"] is None and resultado["estadoCredito"] == "AL_DIA"
    aplicacion = resultado["aplicacion"]
    assert (aplicacion["numeroCuota"], aplicacion["montoAplicado"], aplicacion["montoAplicadoCapital"]) == (
        1, monto, monto)
    assert aplicacion["montoAplicadoMora"] == "0.00"
    assert saldo(admin, credito["numCuenta"]) == f"{float(antes) - float(monto):.2f}"
    # El comprobante del Home Banking: saldo y cuotas del crédito tal como quedaron en COREDB.
    detalle = api.get(f"/api/v1/creditos/{credito['codCredito']}", headers=cabeceras(token)).json()
    pendientes = sum(1 for c in detalle["cuotas"] if float(c["saldoPendiente"]) > 0)
    assert (resultado["saldoCredito"], resultado["cuotasPendientes"]) == (detalle["saldoPendiente"], pendientes)
    assert pendientes == len(detalle["cuotas"]) - 1 and float(resultado["saldoCredito"]) > 0
    assert (resultado["cuotasPagadas"], resultado["numCuenta"], resultado["moneda"]) == (
        [1], credito["numCuenta"], detalle["moneda"])
    assert resultado["montoAplicado"] == monto and resultado["uuidTransaccion"]

    repetida = pago_legacy(api, token, {"codCliente": credito["codCliente"], "codCredito": credito["codCredito"],
                                        "montoPago": monto, "numCuenta": credito["numCuenta"]}, referencia)
    assert repetida.status_code == 200
    assert repetida.json()["idPago"] == resultado["idPago"] and repetida.json()["idempotente"] is True
    assert (repetida.json()["saldoCredito"], repetida.json()["cuotasPendientes"]) == (
        resultado["saldoCredito"], resultado["cuotasPendientes"])
    assert saldo(admin, credito["numCuenta"]) == f"{float(antes) - float(monto):.2f}"


def test_debito_rechazado_no_cambia_la_cuota(api, admin, operador, credito):
    token = operador[0]
    vacia = abrir_cuenta(admin, credito["codCliente"])
    monto = _monto_cuota(credito["cuotas"][0])
    antes = api.get(f"/api/v1/creditos/{credito['codCredito']}", headers=cabeceras(token)).json()
    referencia = "PAGO-SIN-FONDOS"

    r = pago_nuevo(api, token, credito["codCredito"], vacia, monto, referencia)
    assert r.status_code == 201, r.text
    p = r.json()
    assert (p["estado"], p["motivo"], p["uuidTransaccion"], p["aplicaciones"]) == (
        "RECHAZADO", "SALDO_INSUFICIENTE", None, [])

    despues = api.get(f"/api/v1/creditos/{credito['codCredito']}", headers=cabeceras(token)).json()
    assert despues["saldoPendiente"] == antes["saldoPendiente"]
    assert [c["saldoPendiente"] for c in despues["cuotas"]] == [c["saldoPendiente"] for c in antes["cuotas"]]

    comprobante = api.get(f"/pagos/{referencia}/comprobante", headers=cabeceras(token))
    assert comprobante.status_code == 409 and comprobante.json()["error"]["code"] == "PAGO_NO_CONFIRMADO"

    # La misma referencia rechazada se repite sin otro intento de débito.
    otra = pago_nuevo(api, token, credito["codCredito"], vacia, monto, referencia)
    assert otra.status_code == 200 and otra.json()["idPago"] == p["idPago"] and otra.json()["estado"] == "RECHAZADO"


def test_mora_y_vencimientos(api, admin, operador, credito):
    token = operador[0]
    assert atrasar_cuotas(credito["codCredito"], 40, 1) == 1

    vencimientos = api.post("/api/v1/vencimientos", headers=cabeceras(admin), json={})
    assert vencimientos.status_code == 200, vencimientos.text
    assert vencimientos.json()["cuotasVencidas"] >= 1
    assert vencimientos.json()["creditosActualizados"] >= 1

    detalle = api.get(f"/api/v1/creditos/{credito['codCredito']}", headers=cabeceras(token)).json()
    assert detalle["estado"] == "EN_MORA"
    assert detalle["cuotas"][0]["estado"] == "VENCIDA" and detalle["cuotas"][0]["diasAtraso"] > 0

    mora = api.post(f"/api/v1/creditos/{credito['codCredito']}/cuotas/1/mora", headers=cabeceras(admin),
                    json={"montoCalculado": "12.50"})
    assert mora.status_code == 201, mora.text
    assert (mora.json()["montoCalculado"], mora.json()["vigente"]) == ("12.50", True)
    assert mora.json()["diasAtraso"] > 0
    historia = api.get(f"/api/v1/creditos/{credito['codCredito']}/cuotas/1/mora", headers=cabeceras(token))
    assert historia.status_code == 200 and [m["montoCalculado"] for m in historia.json()] == ["12.50"]

    detalle = api.get(f"/api/v1/creditos/{credito['codCredito']}", headers=cabeceras(token)).json()
    assert detalle["moraVigente"] == "12.50"
    monto = api.get(f"/creditos/{credito['codCredito']}/monto-a-pagar", headers=cabeceras(token)).json()
    assert (monto["moraVigente"], monto["totalAPagar"]) == ("12.50", monto["saldoCapital"])

    # Un nuevo cálculo reemplaza al vigente y conserva el historial.
    assert api.post(f"/api/v1/creditos/{credito['codCredito']}/cuotas/1/mora", headers=cabeceras(admin),
                    json={"montoCalculado": "15.00"}).status_code == 201
    historia = api.get(f"/api/v1/creditos/{credito['codCredito']}/cuotas/1/mora", headers=cabeceras(token)).json()
    assert len(historia) == 2 and [m["vigente"] for m in historia].count(True) == 1
    assert api.get(f"/api/v1/creditos/{credito['codCredito']}", headers=cabeceras(token)).json()["moraVigente"] == "15.00"


def test_conciliacion_de_pagos(api, admin, operador, credito):
    token = operador[0]
    monto = _monto_cuota(credito["cuotas"][0])
    assert pago_nuevo(api, token, credito["codCredito"], credito["numCuenta"], monto, "CONCIL-1").status_code == 201

    conciliacion = api.get("/api/v1/conciliacion", headers=cabeceras(admin))
    assert conciliacion.status_code == 200, conciliacion.text
    filas = [f for f in conciliacion.json() if f["moneda"] == "PEN" and f["canal"] == "VEN"]
    assert filas and filas[0]["pagosConfirmados"] >= 1
    assert float(filas[0]["importeCobrado"]) >= float(monto)
    assert float(filas[0]["importeAplicado"]) >= float(monto)
    dia = api.get("/api/v1/conciliacion", params={"fecha": date.today().isoformat()},
                  headers=cabeceras(admin))
    assert dia.status_code == 200


def test_credito_y_pago_inexistentes(api, admin, operador):
    token = operador[0]
    r = api.get("/api/v1/creditos/CRE-NO-EXISTE", headers=cabeceras(token))
    assert r.status_code == 404 and r.json()["error"]["code"] == "CREDITO_NO_ENCONTRADO"
    r = api.get("/creditos/CRE-NO-EXISTE/monto-a-pagar", headers=cabeceras(token))
    assert r.status_code == 404 and r.json()["error"]["code"] == "CREDITO_NO_ENCONTRADO"
    r = api.get("/api/v1/pagos/REF-NO-EXISTE", headers=cabeceras(token))
    assert r.status_code == 404 and r.json()["error"]["code"] == "PAGO_NO_ENCONTRADO"
    assert api.get("/clientes/C999999/creditos", headers=cabeceras(token)).json() == []
    assert coredb("GET", "/coredb/creditos/CRE-NO-EXISTE", admin).status_code == 404
