"""Ensayo TCP SOL sintético; ejecutar solo contra compose-e06.yaml aislado.

No imprime cuerpos, cookies ni credenciales. Requiere httpx del entorno SOL.
La clave se lee del archivo temporal externo indicado, nunca de un literal.
"""
import argparse
import copy
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True)
    args = parser.parse_args()
    secrets = dict(line.split("=", 1) for line in Path(args.env_file).read_text().splitlines())
    password = secrets["E06_LOGIN_PASSWORD"]
    checks = []

    def check(name, condition):
        assert condition, name
        checks.append(name)

    backend = "http://127.0.0.1:18016"
    origin = "http://127.0.0.1:13016"
    with httpx.Client(timeout=10) as raw:
        check("backend_ready_mysql", raw.get(backend + "/ready").status_code == 200)
        spec = raw.get(backend + "/openapi.json").json()
        expected = json.loads(Path(__file__).with_name("sol-openapi-e05-simulado.json").read_text())
        # Python 3.11/3.13 cambia solo el nombre HTTPStatus de 422.
        for document in (spec, expected):
            for item in document["paths"].values():
                for operation in item.values():
                    response = operation.get("responses", {}).get("422")
                    if response and response.get("description") in {"Unprocessable Entity", "Unprocessable Content"}:
                        response["description"] = "HTTP 422"
        check("openapi_semantica_igual_e05", spec == expected)
        check("openapi_auth_y_202", len(spec["components"]["securitySchemes"]) == 2 and
              "202" in spec["paths"]["/sol/applications/{identifier}/send"]["post"]["responses"])
        check("backend_sin_sesion_401", raw.get(backend + "/sol/applications").status_code == 401)
        check("callback_sin_servicio_401", raw.post(backend + "/sol/integrations/evaluation-results",
              json={"idSolicitud": "e06-inexistente", "versionSolicitud": 1, "idEvaluacion": "EVA-SINTETICA",
                    "ronda": 1, "idOperacion": "e06-operacion", "idCorrelacion": "e06-correlacion",
                    "decision": "OBSERVADO", "observaciones": "Prueba sintética sin servicio"},
              headers={"X-Correlation-ID": "e06-correlacion", "X-Idempotency-Key": "e06-operacion"}).status_code == 401)
        check("pagina_next_http", raw.get(origin + "/solicitud-credito").status_code == 200)

    for channel, base in [("backend", backend + "/sol"), ("frontend_proxy", origin + "/api/solicitud-credito")]:
        with httpx.Client(base_url=base + "/", timeout=10, headers={"Origin": origin}) as c:
            def req(method, path, status=200, **kwargs):
                r = c.request(method, path, **kwargs)
                check(channel + ":" + method + ":" + path.split("/")[0] + ":" + str(status), r.status_code == status)
                if channel == "frontend_proxy":
                    check(channel + ":no_store", r.headers.get("cache-control") == "no-store")
                return r

            def login(username):
                r = req("POST", "auth/login", json={"username": username, "password": password})
                data = r.json()
                if channel == "backend":
                    c.headers["Authorization"] = "Bearer " + data["token"]
                else:
                    check("proxy_oculta_token_cookie_httponly", "token" not in data and
                          "HttpOnly" in r.headers["set-cookie"] and "bna_sol_session" in c.cookies)

            login("asesor.bna")
            req("GET", "auth/me")
            clients = req("GET", "clients").json()
            check(channel + ":referencias_minimas", "correo_electronico" not in json.dumps(clients) and
                  "fecha_nacimiento" not in json.dumps(clients))
            policy = req("GET", "policy").json()
            check(channel + ":modo_simulado", policy["integracion"] == "SIMULADO")
            payload = {"id_cliente": "0198b000-0000-7009-8000-000000000001",
                       "monto_solicitado": "15000.00", "moneda": "PEN", "plazo_meses": 12,
                       "destino_credito": "Ensayo sintético E06", "fecha_base": datetime.now(ZoneInfo("America/Lima")).date().isoformat(),
                       "garantias": [{"tipo_garantia": "VEHICULAR", "descripcion": "Respaldo sintético E06", "valor_tasacion": "12000.00"}],
                       "fiadores": ["0198b000-0000-7009-8000-000000000002"]}
            preview = req("POST", "preview", json=payload).json()
            rows = preview["calendario"]["cuotas"]
            check(channel + ":calendario_decimal", len(rows) == 12 and rows[-1]["saldo_final"] == "0.00" and
                  sum(Decimal(r["amortizacion"]) for r in rows) == Decimal("15000.00"))
            check(channel + ":fiador_simulado", preview["fiadores"][0]["validacion"] == "SIMULADA")
            d = req("POST", "applications", 201, json=payload).json()
            path = "applications/" + d["id"]
            check(channel + ":persistencia_preview", d["versiones"][0]["expediente"] == preview)
            original_revision = d["revision"]
            payload["monto_solicitado"] = "18000.00"
            d = req("PUT", path, json={**payload, "revision": original_revision}).json()
            req("PUT", path, 409, json={**payload, "revision": original_revision})
            for invalid in [{"pago_doble": True}, {"moneda": "USD"}, {"plazo_meses": 61}, {"fiadores": [payload["id_cliente"]]}]:
                req("POST", "preview", 422, json={**payload, **invalid})
            marker = "E06-VALOR-SENSIBLE-SINTETICO"
            r = req("POST", "preview", 422, json={**payload, marker: marker})
            check(channel + ":422_sin_eco", marker not in r.text)
            op = str(uuid4())
            revision = d["revision"]
            d = req("POST", path + "/send", json={"revision": revision}, headers={"X-Idempotency-Key": op}).json()
            check(channel + ":en_evaluacion_y_congelada", d["estado"] == "EN_EVALUACION" and d["versiones"][0]["congelada"])
            frozen = copy.deepcopy(d["versiones"][0])
            duplicate = req("POST", path + "/send", json={"revision": revision}, headers={"X-Idempotency-Key": op}).json()
            check(channel + ":envio_idempotente", duplicate["reintento_reconocido"] and len(duplicate["envios"]) == 1)
            req("PUT", path, 409, json={**payload, "revision": d["revision"]})
            req("POST", path + "/demo-result", 403, json={"version": 1, "decision": "OBSERVADO", "observaciones": "Observación sintética E06"}, headers={"X-Idempotency-Key": str(uuid4())})
            login("evaluador.demo")
            result_op = str(uuid4())
            result_body = {"version": 1, "decision": "OBSERVADO", "observaciones": "Observación sintética E06"}
            d = req("POST", path + "/demo-result", json=result_body, headers={"X-Idempotency-Key": result_op}).json()
            check(channel + ":observada", d["estado"] == "OBSERVADA")
            check(channel + ":resultado_idempotente", req("POST", path + "/demo-result", json=result_body,
                  headers={"X-Idempotency-Key": result_op}).json()["reintento_reconocido"])
            login("asesor.bna")
            d = req("POST", path + "/revise", json={"revision": d["revision"]}).json()
            check(channel + ":subsanada_version2", d["version"] == 2 and d["estado"] == "BORRADOR")
            d = req("PUT", path, json={**payload, "revision": d["revision"], "destino_credito": "Subsanación sintética E06"}).json()
            d = req("POST", path + "/send", json={"revision": d["revision"]}, headers={"X-Idempotency-Key": str(uuid4())}).json()
            login("evaluador.demo")
            req("POST", path + "/demo-result", 409, json=result_body, headers={"X-Idempotency-Key": str(uuid4())})
            d = req("POST", path + "/demo-result", json={**result_body, "version": 2, "decision": "APROBADO"}, headers={"X-Idempotency-Key": str(uuid4())}).json()
            check(channel + ":historial_inmutable_y_cierre", d["estado"] == "APROBADA" and d["versiones"][0] == frozen and len(d["envios"]) == 2)
            login("auditor.bna")
            req("GET", "ops/pending")
            req("GET", "ops/metrics")
            req("POST", "applications", 403, json=payload)
            req("GET", path)
            req("POST", "auth/logout")
            req("GET", "auth/me", 401)
            if channel == "frontend_proxy":
                check("proxy_cookie_eliminada", "bna_sol_session" not in c.cookies)
                req("POST", "auth/login", 403, json={}, headers={"Origin": "https://externo.invalid"})
                req("POST", "integrations/evaluation-results", 404, json={})

    print(json.dumps({"clasificacion": "TCP real Next/SOL/MySQL; CAP/EVA/Auditoria SIMULADO; sin navegador", "checks": len(checks), "resultados": checks}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
