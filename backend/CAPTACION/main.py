from fastapi import FastAPI
from fastapi.responses import JSONResponse

from CAPTACION.api import montar_en
from CAPTACION.config import settings
from CAPTACION.core_client import coredb

app = FastAPI(
    title="BNA - Captación de Clientes",
    description=(
        "Registra al solicitante, verifica su identidad (consentimientos, OTP, RENIEC, listas "
        "restrictivas, PEP), consulta centrales de riesgo, calcula su perfil y lo **habilita**: "
        "lo registra en COREDB como cliente y deja la referencia que consulta Solicitud de "
        "Crédito (contrato CR-INT-01). No tiene base propia: el expediente vive en la base "
        "integrada y se trabaja por COREDB.\n\n"
        "**Cómo probar desde /docs**\n"
        "1. Token en COREDB: `POST http://127.0.0.1:8012/coredb/auth/login` con un usuario "
        "ADMINISTRADOR o ASESOR.\n"
        "2. **Authorize** (candado) y pegar solo el `access_token`.\n"
        "3. Seguir los pasos en orden: solicitante → caso → consentimientos → OTP → "
        "validaciones → consulta de riesgo → perfil → habilitar.\n\n"
        "Las rutas `/cap/references` son solo para Solicitud de Crédito y usan `CAP_SOL_TOKEN`."
    ),
    version="1.0.0",
    swagger_ui_parameters={"persistAuthorization": True},
)

montar_en(app)


@app.get("/health", tags=["Salud"])
def health():
    return {"status": "healthy", "modulo": "captacion"}


@app.get("/ready", tags=["Salud"])
def ready():
    """503 si COREDB no responde o si falta la credencial de servicio. CAPTACION no tiene
    base propia: el expediente vive en la base integrada."""
    problemas = []
    if not coredb().salud():
        problemas.append("coredb")
    if not settings.cap_core_secreto:
        problemas.append("credencial_coredb")
    if problemas:
        return JSONResponse(status_code=503, content={"status": "not_ready", "faltan": problemas})
    return {"status": "ready", "modulo": "captacion"}
