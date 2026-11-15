"""Del expediente a la aprobación: situación financiera, regla, decisión del analista y CR-INT-04."""
from datetime import datetime, timedelta, timezone

import pytest

from EVALUACION.comun import utc_ahora
from EVALUACION.tests.ayudas import aprobada, cabeceras, nuevo_sobre, recibir, registrar_situacion


def _detalle(api, id_evaluacion, token="tok-analista"):
    return api.get(f"/eva/v1/evaluaciones/{id_evaluacion}", headers=cabeceras(token)).json()


def _decidir(api, id_evaluacion, decision, observaciones="Revisado con el sustento del cliente.",
             token="tok-analista"):
    version = _detalle(api, id_evaluacion)["version"]
    return api.post(f"/eva/v1/evaluaciones/{id_evaluacion}/decision", headers=cabeceras(token),
                    json={"decision": decision, "observaciones": observaciones, "version": version})


def _ahora_iso():
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------- Evaluación
def test_aprobado_por_la_regla_crea_la_aprobacion(api):
    acuse = recibir(api, nuevo_sobre()).json()
    d = registrar_situacion(api, acuse["idEvaluacion"], "5000.00").json()
    assert d["estado"] == "APROBADO" and d["decididoPor"] == "MOTOR"
    assert d["motor"] == {"resultado": "APROBADO", "score": 850, "limite": "21000.00", "ratio": "0.7143",
                          "regla": "RN-EVA-002-P · demo v1"}
    assert d["situacionFinanciera"]["registradoPor"] == "ana.analista"
    a = d["aprobacion"]
    assert a["estado"] == "VIGENTE" and a["version"] == 1
    assert a["codCredito"].startswith("CRE-") and len(a["codCredito"]) <= 20
    assert (a["montoAprobado"], a["moneda"], a["plazoMeses"], a["tasaTea"]) == ("15000.00", "PEN", 12, "0.2200")
    vigencia = datetime.fromisoformat(a["vigenteHasta"]) - datetime.now(timezone.utc)
    assert timedelta(days=29, hours=23) < vigencia <= timedelta(days=30)
    assert d["envioSol"]["decision"] == "APROBADO" and d["envioSol"]["estado"] == "PENDIENTE"
    eventos = [h["evento"] for h in d["historial"]]
    assert eventos == ["EXPEDIENTE_RECIBIDO", "SITUACION_REGISTRADA", "RESULTADO_MOTOR", "APROBACION_CREADA",
                       "RESULTADO_POR_ENTREGAR"]


def test_el_calendario_es_el_de_sol_sin_cambios(api):
    sobre = nuevo_sobre(monto="12000.00", plazo_meses=18)
    acuse = recibir(api, sobre).json()
    d = registrar_situacion(api, acuse["idEvaluacion"], "5000.00").json()
    apr = api.get(f"/eva/v1/aprobaciones/{d['aprobacion']['idAprobacion']}", headers=cabeceras("tok-desembolso")).json()
    de_sol = sobre["expediente"]["calendario"]
    campos = ("numero_cuota", "fecha_vencimiento", "saldo_inicial", "amortizacion", "interes", "cuota_total", "saldo_final")
    nuestros = ("numeroCuota", "fechaVencimiento", "saldoInicial", "amortizacion", "interes", "cuotaTotal", "saldoFinal")
    assert [tuple(q[k] for k in nuestros) for q in apr["calendario"]["cuotas"]] == \
           [tuple(q[k] for k in campos) for q in de_sol["cuotas"]]
    assert (apr["calendario"]["totalPagar"], apr["calendario"]["interesesTotales"], apr["calendario"]["estado"]) == \
           (de_sol["total_pagar"], de_sol["intereses_totales"], de_sol["estado"])
    assert apr["calendario"]["origen"] == "SOL" and apr["calendario"]["politica"] == "SOL-DEMO-2026-01"


def test_rechazado_por_la_regla(api):
    acuse = recibir(api, nuevo_sobre()).json()
    d = registrar_situacion(api, acuse["idEvaluacion"], "3000.00").json()
    assert d["estado"] == "RECHAZADO" and d["aprobacion"] is None
    assert d["envioSol"]["decision"] == "RECHAZADO"
    assert d["motivo"].startswith("Rechazado por la regla RN-EVA-002-P")


def test_la_zona_gris_la_decide_el_analista(api):
    acuse = recibir(api, nuevo_sobre()).json()
    d = registrar_situacion(api, acuse["idEvaluacion"], "4000.00").json()
    assert d["estado"] == "EN_REVISION" and d["aprobacion"] is None and d["envioSol"] is None
    r = _decidir(api, acuse["idEvaluacion"], "APROBADO", token="tok-analista-2")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["estado"] == "APROBADO" and d["decididoPor"] == "beto.analista"
    assert d["aprobacion"]["aprobadaPor"] == "beto.analista"
    assert d["envioSol"]["decision"] == "APROBADO"


def test_observar_pide_a_sol_que_corrija(api):
    acuse = recibir(api, nuevo_sobre()).json()
    registrar_situacion(api, acuse["idEvaluacion"], "4000.00")
    d = _decidir(api, acuse["idEvaluacion"], "OBSERVADO", "Precisar el destino declarado.").json()
    assert d["estado"] == "OBSERVADO" and d["aprobacion"] is None
    assert d["envioSol"]["decision"] == "OBSERVADO"
    assert d["motivo"] == "Precisar el destino declarado."


def test_la_situacion_debe_estar_verificada(api):
    acuse = recibir(api, nuevo_sobre()).json()
    r = registrar_situacion(api, acuse["idEvaluacion"], "5000.00", verificada=False)
    assert r.status_code == 422 and r.json()["error"]["code"] == "SITUACION_NO_VERIFICADA"
    assert _detalle(api, acuse["idEvaluacion"])["estado"] == "PENDIENTE"


def test_la_situacion_se_registra_una_sola_vez(api):
    acuse = recibir(api, nuevo_sobre()).json()
    registrar_situacion(api, acuse["idEvaluacion"], "4000.00")
    r = registrar_situacion(api, acuse["idEvaluacion"], "5000.00")
    assert r.status_code == 409 and r.json()["error"]["code"] == "EVALUACION_NO_PENDIENTE"


def test_version_desactualizada(api):
    acuse = recibir(api, nuevo_sobre()).json()
    r = registrar_situacion(api, acuse["idEvaluacion"], "5000.00", version=99)
    assert r.status_code == 409 and r.json()["error"]["code"] == "VERSION_DESACTUALIZADA"


def test_solo_se_decide_un_caso_en_revision(api):
    acuse = recibir(api, nuevo_sobre()).json()
    r = _decidir(api, acuse["idEvaluacion"], "APROBADO")
    assert r.status_code == 409 and r.json()["error"]["code"] == "EVALUACION_NO_EN_REVISION"


def test_bandeja_con_filtros(api):
    a = recibir(api, nuevo_sobre()).json()
    recibir(api, nuevo_sobre(id_cliente="CLI000000002", numero_documento="70000002", nombres="Lucía",
                             apellido_paterno="Torres", apellido_materno="Mamani"))
    registrar_situacion(api, a["idEvaluacion"], "4000.00")
    bandeja = api.get("/eva/v1/evaluaciones", headers=cabeceras("tok-auditor")).json()
    assert bandeja["conteos"] == {"PENDIENTE": 1, "EN_REVISION": 1}
    assert {e["cliente"]["numeroDocumento"] for e in bandeja["items"]} == {"****0001", "****0002"}
    en_revision = api.get("/eva/v1/evaluaciones", params={"estado": "EN_REVISION"}, headers=cabeceras("tok-analista"))
    assert [e["idEvaluacion"] for e in en_revision.json()["items"]] == [a["idEvaluacion"]]
    por_nombre = api.get("/eva/v1/evaluaciones", params={"buscar": "Torres"}, headers=cabeceras("tok-analista"))
    assert [e["cliente"]["nombre"] for e in por_nombre.json()["items"]] == ["Lucía Torres Mamani"]


# ---------------------------------------------------------------------- CR-INT-04
def test_desembolso_busca_por_documento_o_credito(api):
    a = aprobada(api)["aprobacion"]
    por_documento = api.get("/eva/v1/aprobaciones", params={"numeroDocumento": "70000001"},
                            headers=cabeceras("tok-desembolso")).json()["items"]
    assert [x["idAprobacion"] for x in por_documento] == [a["idAprobacion"]]
    assert por_documento[0]["numeroDocumento"] == "70000001"     # Desembolso lo necesita completo
    assert "cuotas" not in por_documento[0]["calendario"]        # la lista no repite el calendario
    por_credito = api.get("/eva/v1/aprobaciones", params={"codCredito": a["codCredito"]},
                          headers=cabeceras("tok-desembolso")).json()["items"]
    assert [x["idAprobacion"] for x in por_credito] == [a["idAprobacion"]]
    sin_filtro = api.get("/eva/v1/aprobaciones", headers=cabeceras("tok-desembolso"))
    assert sin_filtro.status_code == 422 and sin_filtro.json()["error"]["code"] == "FILTRO_REQUERIDO"
    del_auditor = api.get("/eva/v1/aprobaciones", params={"codCredito": a["codCredito"]},
                          headers=cabeceras("tok-auditor")).json()["items"][0]
    assert del_auditor["numeroDocumento"] == "****0001"
    assert api.get("/eva/v1/aprobaciones/APR-0000-000000", headers=cabeceras("tok-desembolso")).status_code == 404


def test_registrar_el_desembolso_es_idempotente(api):
    a = aprobada(api)["aprobacion"]
    ruta = f"/eva/v1/aprobaciones/{a['idAprobacion']}/desembolso"
    cuerpo = {"version": a["version"], "codigoOrden": "DES-2026-000001", "fechaDesembolso": _ahora_iso()}
    primero = api.post(ruta, json=cuerpo, headers=cabeceras("tok-desembolso"))
    assert primero.status_code == 200, primero.text
    marcada = primero.json()
    assert marcada["estado"] == "DESEMBOLSADA" and marcada["version"] == 2
    assert marcada["desembolso"]["codigoOrden"] == "DES-2026-000001"
    assert marcada["desembolso"]["registradoPor"] == "svc-desembolso"
    repetido = api.post(ruta, json=cuerpo, headers=cabeceras("tok-desembolso"))
    assert repetido.status_code == 200 and repetido.json() == marcada
    otra_orden = api.post(ruta, json={**cuerpo, "codigoOrden": "DES-2026-000002"}, headers=cabeceras("tok-desembolso"))
    assert otra_orden.status_code == 409 and otra_orden.json()["error"]["code"] == "APROBACION_YA_DESEMBOLSADA"
    revocar = api.post(f"/eva/v1/aprobaciones/{a['idAprobacion']}/revocacion", headers=cabeceras("tok-analista"),
                       json={"motivo": "Ya no corresponde el crédito.", "version": 2})
    assert revocar.status_code == 409 and revocar.json()["error"]["code"] == "APROBACION_NO_VIGENTE"


def test_el_desembolso_compara_la_version(api):
    a = aprobada(api)["aprobacion"]
    r = api.post(f"/eva/v1/aprobaciones/{a['idAprobacion']}/desembolso", headers=cabeceras("tok-desembolso"),
                 json={"version": 7, "codigoOrden": "DES-2026-000001", "fechaDesembolso": _ahora_iso()})
    assert r.status_code == 409 and r.json()["error"] == {
        "code": "VERSION_DESACTUALIZADA", "message": r.json()["error"]["message"], "details": {"version": 1}}


def test_una_aprobacion_revocada_no_se_desembolsa(api):
    a = aprobada(api)["aprobacion"]
    revocada = api.post(f"/eva/v1/aprobaciones/{a['idAprobacion']}/revocacion", headers=cabeceras("tok-analista"),
                        json={"motivo": "El cliente desistió del crédito.", "version": 1})
    assert revocada.status_code == 200 and revocada.json()["estado"] == "REVOCADA"
    assert revocada.json()["revocacion"]["revocadaPor"] == "ana.analista"
    r = api.post(f"/eva/v1/aprobaciones/{a['idAprobacion']}/desembolso", headers=cabeceras("tok-desembolso"),
                 json={"version": 2, "codigoOrden": "DES-2026-000001", "fechaDesembolso": _ahora_iso()})
    assert r.status_code == 409 and r.json()["error"]["code"] == "APROBACION_REVOCADA"


def test_una_fecha_de_desembolso_futura_se_rechaza(api):
    a = aprobada(api)["aprobacion"]
    futura = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    r = api.post(f"/eva/v1/aprobaciones/{a['idAprobacion']}/desembolso", headers=cabeceras("tok-desembolso"),
                 json={"version": 1, "codigoOrden": "DES-2026-000001", "fechaDesembolso": futura})
    assert r.status_code == 422 and r.json()["error"]["code"] == "FECHA_FUTURA"
    sin_zona = api.post(f"/eva/v1/aprobaciones/{a['idAprobacion']}/desembolso", headers=cabeceras("tok-desembolso"),
                        json={"version": 1, "codigoOrden": "DES-2026-000001", "fechaDesembolso": "2026-11-15T10:00:00"})
    assert sin_zona.status_code == 422


@pytest.fixture
def reloj(monkeypatch):
    """Adelanta el reloj de Evaluación: reloj(31) es "dentro de 31 días" y devuelve esa fecha con zona."""
    inicio = utc_ahora()

    def mover(dias: int) -> datetime:
        monkeypatch.setattr("EVALUACION.servicio.utc_ahora", lambda: inicio + timedelta(days=dias))
        return (inicio + timedelta(days=dias)).replace(tzinfo=timezone.utc)

    return mover


def test_una_aprobacion_vencida(api, reloj):
    a = aprobada(api)["aprobacion"]                     # vigente 30 días
    dentro_de_31 = reloj(31)
    consultada = api.get(f"/eva/v1/aprobaciones/{a['idAprobacion']}", headers=cabeceras("tok-desembolso")).json()
    assert consultada["estado"] == "VENCIDA"
    vencidas = api.get("/eva/v1/aprobaciones", params={"codCredito": a["codCredito"], "estado": "VENCIDA"},
                       headers=cabeceras("tok-desembolso")).json()["items"]
    assert len(vencidas) == 1
    r = api.post(f"/eva/v1/aprobaciones/{a['idAprobacion']}/desembolso", headers=cabeceras("tok-desembolso"),
                 json={"version": 1, "codigoOrden": "DES-2026-000001", "fechaDesembolso": dentro_de_31.isoformat()})
    assert r.status_code == 409 and r.json()["error"]["code"] == "APROBACION_VENCIDA"
    revocar = api.post(f"/eva/v1/aprobaciones/{a['idAprobacion']}/revocacion", headers=cabeceras("tok-analista"),
                       json={"motivo": "Ya no corresponde el crédito.", "version": 1})
    assert revocar.status_code == 409 and revocar.json()["error"]["code"] == "APROBACION_VENCIDA"


def test_un_desembolso_dentro_de_la_vigencia_se_acepta_aunque_se_informe_tarde(api, reloj):
    a = aprobada(api)["aprobacion"]
    confirmada = reloj(1)          # Desembolso confirmó la orden al día siguiente, con la aprobación vigente...
    reloj(31)                      # ...y lo informa cuando ya venció (la entrega se reintentó).
    r = api.post(f"/eva/v1/aprobaciones/{a['idAprobacion']}/desembolso", headers=cabeceras("tok-desembolso"),
                 json={"version": 1, "codigoOrden": "DES-2026-000001", "fechaDesembolso": confirmada.isoformat()})
    assert r.status_code == 200 and r.json()["estado"] == "DESEMBOLSADA"
