"""Panel web del módulo de Clientes: tablas de solicitudes + laboratorio de pruebas (HTTP Basic).

Rutas /panel/*: administrativas, NO son parte del contrato de negocio.
"""
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import HTMLResponse

from shared.biometria import plantillas as bio
from shared.comun import ApiError, requerir_basic
from shared.esquemas import FORMATO_FACIAL, FORMATO_HUELLA, MODULOS_ORIGEN

from . import config, conexiones as con

router = APIRouter(prefix="/panel", tags=["Panel (HTML + API)"],
                   dependencies=[Depends(requerir_basic(config.PANEL_USER, config.PANEL_PASSWORD, "Panel de Clientes BNA"))])


@router.get("", response_class=HTMLResponse, include_in_schema=False)
async def pagina(request: Request):
    return request.app.state.templates.TemplateResponse(request, "panel.html", {"modulos": MODULOS_ORIGEN})


@router.get("/api/estado")
async def estado():
    """Salud de cada pieza vista desde Clientes: Bus -> Core, y RENIEC directo."""
    return {**await con.bus_salud(), "reniec": await con.reniec_salud(), "clientes": "ok"}


@router.get("/api/solicitudes-registro")
async def solicitudes_registro(limite: int = Query(100, ge=1, le=500), orden: Literal["recientes", "antiguas"] = "recientes"):
    return await con.core("GET", "solicitudes-registro", params={"limite": limite, "orden": orden})


@router.get("/api/solicitudes-validacion")
async def solicitudes_validacion(limite: int = Query(100, ge=1, le=500), orden: Literal["recientes", "antiguas"] = "recientes"):
    return await con.core("GET", "solicitudes-validacion", params={"limite": limite, "orden": orden})


# ---------------------------------------------------------------- laboratorio
def _resumir(peticion: dict) -> dict:
    """Para la consola: la plantilla biométrica NUNCA se muestra completa."""
    copia = dict(peticion)
    t = copia.get("template")
    if isinstance(t, list):
        copia["template"] = f"[oculto · {copia.get('formato')} · {len(t)} valores · enviado]"
    elif isinstance(t, str):
        copia["template"] = f"[oculto · {copia.get('formato')} · {len(t)} caracteres Base64 · enviado]"
    return copia


@router.post("/api/lab/extraer-plantilla")
def extraer_plantilla(tipo: Literal["FACIAL", "HUELLA"] = Form(...), archivo: UploadFile = File(...)):
    """Herramienta auxiliar: imagen JPG/PNG -> plantilla (mismo componente que RENIEC). La imagen no se guarda."""
    datos = archivo.file.read(bio.MAX_IMAGE_BYTES + 1)
    try:
        if tipo == "FACIAL":
            plantilla, resumen = bio.extraer_embedding_facial(datos), {"formato": FORMATO_FACIAL}
            resumen["longitud"] = len(plantilla)
        else:
            plantilla, metricas = bio.extraer_plantilla_huella(datos)
            resumen = {"formato": FORMATO_HUELLA, "codificacion": "base64", "longitud": len(plantilla), **metricas}
    except bio.BiometriaError as e:
        raise ApiError(e.status, e.codigo, e.mensaje)
    finally:
        del datos
    return {"correcto": True, "tipo": tipo, "template": plantilla, **resumen}


@router.post("/api/lab/{operacion}")
async def laboratorio(operacion: Literal["registrar", "validar-documento", "validar-biometria"], request: Request):
    """Simula a OTRO módulo del banco: la petición entra por el Bus y sigue el recorrido real hasta el Core."""
    try:
        cuerpo = await request.json()
    except ValueError:
        raise ApiError(422, "JSON_INVALIDO", "El cuerpo debe ser JSON")
    if not isinstance(cuerpo, dict):
        raise ApiError(422, "JSON_INVALIDO", "El cuerpo debe ser un objeto JSON")
    status, respuesta, ms = await con.bus_publico(operacion, cuerpo)
    return {"ruta": f"POST /bus/clientes/{operacion}", "peticion": _resumir(cuerpo), "http": status,
            "ok": status < 400, "ms": ms, "respuesta": respuesta}
