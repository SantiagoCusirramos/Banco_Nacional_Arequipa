"""Aprobación → orden → validación → confirmación, contra COREDB y la base integrada reales.

El operador trabaja con su propio token de COREDB, que Desembolso reenvía: la bitácora de la
orden registra a la persona. La confirmación abona la cuenta, crea el crédito con su calendario
OFICIAL y deja la solicitud DESEMBOLSADA en una sola operación de la base.
"""
from DESEMBOLSO.tests.ayudas import (abrir_cuenta, aprobada, cabeceras, cliente_activo, con_admin_de_la_base, confirmar,
                                     coredb, movimientos, orden_preparada, orden_validada, preparar, saldo,
                                     validar_identidad, verificar)


def test_aprobacion_orden_validacion_y_confirmacion(api, admin, operador):
    token, username = operador
    cod_cliente, documento = cliente_activo(admin)
    id_solicitud, id_evaluacion = aprobada(admin, cod_cliente)
    num_cuenta = abrir_cuenta(admin, cod_cliente)

    # Identidad en ventanilla: COREDB verifica el documento y devuelve la evidencia.
    v = verificar(api, token, documento)
    assert v.status_code == 201, v.text
    verificacion = v.json()
    assert (verificacion["resultado"], verificacion["codCliente"]) == ("APROBADO", cod_cliente)
    assert verificacion["nombre"] == "Cliente De Prueba" and "correo" not in verificacion

    # CR-INT-04: la aprobación se lee de COREDB, no de Evaluación.
    r = api.get("/api/v1/aprobaciones", params={"codCliente": cod_cliente}, headers=cabeceras(token))
    assert r.status_code == 200, r.text
    [aprobacion] = r.json()
    assert (aprobacion["idEvaluacion"], aprobacion["idSolicitud"], aprobacion["monto"]) == (
        id_evaluacion, id_solicitud, "15000.00")
    assert aprobacion["ordenAbierta"] is None

    cuentas = api.get(f"/api/v1/clientes/{cod_cliente}/cuentas", params={"moneda": "PEN"}, headers=cabeceras(token))
    assert cuentas.status_code == 200, cuentas.text
    assert [(c["numCuenta"], c["elegible"]) for c in cuentas.json()] == [(num_cuenta, True)]

    llave = "7a0e7d3a-5d1f-4b8e-9a51-3c1d2e4f5a6b"
    orden = preparar(api, token, id_evaluacion, num_cuenta, llave)
    assert orden.status_code == 201, orden.text
    o = orden.json()
    assert (o["estado"], o["importe"], o["numCuenta"], o["usuarioPreparacion"]) == (
        "PREPARADA", "15000.00", num_cuenta, username)
    assert o["codigoOrden"].startswith("DES-")
    repetida = preparar(api, token, id_evaluacion, num_cuenta, llave)
    assert repetida.status_code == 200 and repetida.json()["idOrden"] == o["idOrden"]
    [aprobacion] = api.get("/api/v1/aprobaciones", params={"idSolicitud": id_solicitud},
                           headers=cabeceras(token)).json()
    assert aprobacion["ordenAbierta"] == {"idOrden": o["idOrden"], "codigoOrden": o["codigoOrden"],
                                          "estado": "PREPARADA"}

    validada = validar_identidad(api, token, o["idOrden"], verificacion["idValidacion"])
    assert validada.status_code == 201 and validada.json()["estado"] == "VALIDADA", validada.text

    assert saldo(admin, num_cuenta) == "0.00"
    c = confirmar(api, token, o["idOrden"])
    assert c.status_code == 201, c.text
    confirmada = c.json()
    assert confirmada["estado"] == "CONFIRMADA" and confirmada["codCredito"].startswith("CRE-")

    # El abono, una sola vez.
    assert saldo(admin, num_cuenta) == "15000.00"
    abonos = [m for m in movimientos(admin, num_cuenta) if m["uuid_transaccion"] == confirmada["uuidTransaccionAbono"]]
    assert len(abonos) == 1 and abonos[0]["monto"] == "15000.00"

    # El crédito con su calendario OFICIAL, copia del PRELIMINAR, y la solicitud DESEMBOLSADA.
    credito = coredb("GET", f"/coredb/creditos/{confirmada['codCredito']}", admin, 200).json()
    assert credito["estado"] == "AL_DIA" and credito["codCliente"] == cod_cliente
    assert len(credito["cuotas"]) == 12
    solicitud = coredb("GET", f"/coredb/creditos/solicitudes/{id_solicitud}", admin, 200).json()
    assert solicitud["estado"] == "DESEMBOLSADA"
    assert solicitud["calendario"]["tipo"] == "OFICIAL" and len(solicitud["calendario"]["cuotas"]) == 12
    assert api.get("/api/v1/aprobaciones", params={"codCliente": cod_cliente}, headers=cabeceras(token)).json() == []

    # El detalle que muestra la pantalla: la orden, su calendario y la persona que confirmó.
    d = api.get(f"/api/v1/ordenes/{o['idOrden']}", headers=cabeceras(token))
    assert d.status_code == 200, d.text
    detalle = d.json()
    assert (detalle["estado"], detalle["codCredito"], detalle["usuarioConfirmacion"]) == (
        "CONFIRMADA", confirmada["codCredito"], username)
    assert detalle["calendario"]["tipo"] == "OFICIAL" and len(detalle["calendario"]["cuotas"]) == 12
    assert {v["tipo"] for v in detalle["validaciones"]} == {"IDENTIDAD", "CUENTA"}
    assert {e["actor"] for e in detalle["eventos"]} == {username}


def test_confirmar_otra_vez_devuelve_lo_mismo_sin_otro_abono(api, admin, operador):
    token = operador[0]
    datos = orden_validada(api, admin, token)
    id_orden = datos["orden"]["idOrden"]
    primera = confirmar(api, token, id_orden)
    assert primera.status_code == 201, primera.text
    otra = confirmar(api, token, id_orden)
    assert otra.status_code == 200, otra.text
    for campo in ("idOrden", "codigoOrden", "estado", "codCredito", "uuidTransaccionAbono"):
        assert otra.json()[campo] == primera.json()[campo]
    assert saldo(admin, datos["numCuenta"]) == "15000.00"
    assert len(movimientos(admin, datos["numCuenta"])) == 1
    creditos = coredb("GET", f"/coredb/creditos?codCliente={datos['codCliente']}", admin, 200).json()
    assert [c["codCredito"] for c in creditos] == [primera.json()["codCredito"]]


def test_una_cuenta_no_individual_se_rechaza(api, admin, operador):
    token = operador[0]
    cod_cliente, documento = cliente_activo(admin)
    otro, _ = cliente_activo(admin)
    _, id_evaluacion = aprobada(admin, cod_cliente)
    mancomunada = abrir_cuenta(admin, cod_cliente, otro, regimen="MANCOMUNADA_INDISTINTA")
    individual = abrir_cuenta(admin, cod_cliente)

    cuentas = {c["numCuenta"]: c for c in api.get(f"/api/v1/clientes/{cod_cliente}/cuentas",
                                                  params={"moneda": "PEN"}, headers=cabeceras(token)).json()}
    assert (cuentas[mancomunada]["elegible"], cuentas[mancomunada]["motivo"]) == (False, "CUENTA_MANCOMUNADA")
    assert cuentas[individual]["elegible"] is True

    r = preparar(api, token, id_evaluacion, mancomunada)
    assert r.status_code == 422 and r.json()["error"]["code"] == "CUENTA_NO_ELEGIBLE", r.text
    assert mancomunada not in r.text and cod_cliente not in r.text
    assert api.get("/api/v1/ordenes", params={"codCliente": cod_cliente}, headers=cabeceras(token)).json() == []

    # Tampoco se puede cambiar a ella después.
    orden = preparar(api, token, id_evaluacion, individual).json()
    r = api.put(f"/api/v1/ordenes/{orden['idOrden']}/cuenta", headers=cabeceras(token), json={"numCuenta": mancomunada})
    assert r.status_code == 422 and r.json()["error"]["code"] == "CUENTA_NO_ELEGIBLE"
    assert verificar(api, token, documento).json()["resultado"] == "APROBADO"


def test_una_verificacion_de_otro_dia_no_valida_la_orden(api, admin, operador):
    """T7 por omisión: la identidad se verifica el mismo día hábil (fecha de Lima) del desembolso."""
    token = operador[0]
    datos = orden_preparada(api, admin, token)
    filas = con_admin_de_la_base(
        "UPDATE clientes.validacion_identidad SET fecha_evento = fecha_evento - INTERVAL 1 DAY "
        "WHERE id_validacion = %s", (datos["idValidacion"],))
    assert filas == 1
    r = validar_identidad(api, token, datos["orden"]["idOrden"], datos["idValidacion"])
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDACION_NO_ADMITIDA", r.text
    detalle = api.get(f"/api/v1/ordenes/{datos['orden']['idOrden']}", headers=cabeceras(token)).json()
    assert detalle["estado"] == "PREPARADA"


def test_una_identidad_vencida_no_se_confirma(api, admin, operador):
    """Validada ayer: la confirmación de hoy se rechaza, sin abono ni crédito."""
    token = operador[0]
    datos = orden_validada(api, admin, token)
    id_orden = datos["orden"]["idOrden"]
    filas = con_admin_de_la_base(
        "UPDATE creditos.validacion_desembolso SET creado_en = creado_en - INTERVAL 1 DAY "
        "WHERE id_orden = UUID_TO_BIN(%s) AND tipo_validacion = 'IDENTIDAD'", (id_orden,))
    assert filas == 1
    r = confirmar(api, token, id_orden)
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDACION_NO_ADMITIDA", r.text
    assert saldo(admin, datos["numCuenta"]) == "0.00"
    solicitud = coredb("GET", f"/coredb/creditos/solicitudes/{datos['idSolicitud']}", admin, 200).json()
    assert solicitud["estado"] == "APROBADA"
    assert coredb("GET", f"/coredb/creditos?codCliente={datos['codCliente']}", admin, 200).json() == []

    # Con una verificación de hoy, la misma orden se confirma.
    nueva = verificar(api, token, datos["documento"]).json()["idValidacion"]
    assert validar_identidad(api, token, id_orden, nueva).status_code == 201
    assert confirmar(api, token, id_orden).status_code == 201
    assert saldo(admin, datos["numCuenta"]) == "15000.00"


def test_un_documento_no_verificado_no_sirve_de_evidencia(api, admin, operador):
    token = operador[0]
    datos = orden_preparada(api, admin, token)
    rechazada = verificar(api, token, datos["documento"], verificada=False).json()
    assert rechazada["resultado"] == "RECHAZADO"
    r = validar_identidad(api, token, datos["orden"]["idOrden"], rechazada["idValidacion"])
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDACION_NO_ADMITIDA"
    r = confirmar(api, token, datos["orden"]["idOrden"])
    assert r.status_code == 422 and r.json()["error"]["code"] == "ORDEN_NO_ADMITIDA"


def test_rechazar_una_orden_deja_libre_la_aprobacion(api, admin, operador):
    token = operador[0]
    datos = orden_preparada(api, admin, token)
    r = api.post(f"/api/v1/ordenes/{datos['orden']['idOrden']}/rechazo", headers=cabeceras(token),
                 json={"motivo": "El cliente pidió otra cuenta."})
    assert r.status_code == 200 and r.json()["estado"] == "RECHAZADA", r.text
    [aprobacion] = api.get("/api/v1/aprobaciones", params={"idSolicitud": datos["idSolicitud"]},
                           headers=cabeceras(token)).json()
    assert aprobacion["ordenAbierta"] is None
    assert preparar(api, token, datos["idEvaluacion"], datos["numCuenta"]).status_code == 201


def test_monitor_y_conciliacion(api, admin, operador):
    token = operador[0]
    datos = orden_validada(api, admin, token)
    confirmada = confirmar(api, token, datos["orden"]["idOrden"]).json()
    ordenes = api.get("/api/v1/ordenes", params={"codCliente": datos["codCliente"]}, headers=cabeceras(token))
    assert ordenes.status_code == 200
    assert [(o["idOrden"], o["estado"]) for o in ordenes.json()] == [(confirmada["idOrden"], "CONFIRMADA")]
    filtradas = api.get("/api/v1/ordenes", params={"estado": "CONFIRMADA", "idSolicitud": datos["idSolicitud"]},
                        headers=cabeceras(token)).json()
    assert [o["idOrden"] for o in filtradas] == [confirmada["idOrden"]]

    conciliacion = api.get("/api/v1/conciliacion", headers=cabeceras(admin))
    assert conciliacion.status_code == 200, conciliacion.text
    pen = [f for f in conciliacion.json() if f["moneda"] == "PEN"]
    assert pen and pen[0]["ordenesSinAbono"] == 0 and pen[0]["importeOrdenes"] == pen[0]["importeAbonado"]
    # La conciliación es del supervisor y del auditor (GENERAR_REPORTES), no del operador.
    r = api.get("/api/v1/conciliacion", headers=cabeceras(token))
    assert r.status_code == 403 and r.json()["error"]["code"] == "PERMISO_DENEGADO"


def test_orden_inexistente_y_ids_mal_formados(api, operador):
    token = operador[0]
    r = api.get("/api/v1/ordenes/00000000-0000-4000-8000-000000000000", headers=cabeceras(token))
    assert r.status_code == 404 and r.json()["error"]["code"] == "ORDEN_NO_ENCONTRADA"
    assert api.get("/api/v1/ordenes/no-es-un-uuid", headers=cabeceras(token)).status_code == 422
    r = api.get("/api/v1/aprobaciones", headers=cabeceras(token))
    assert r.status_code == 422 and r.json()["error"]["code"] == "FILTRO_REQUERIDO"
