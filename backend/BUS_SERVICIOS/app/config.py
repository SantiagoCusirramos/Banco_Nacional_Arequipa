
import os
from dotenv import load_dotenv

load_dotenv()

# Autenticación de la API actual
API_KEY = os.getenv(
    "BNA_API_KEY",
    "bna-clave-local-cambiar",
)

# Direcciones de los módulos
SERVICIOS = {
    "seguridad": os.getenv("SEGURIDAD_URL", "http://bna-seguridad:8000"),
    "billetera": os.getenv(
        "BILLETERA_URL",
        "http://host.docker.internal:3000/api",
    ),
    "clientes": os.getenv(
        "CLIENTES_URL",
        "http://clientes:8000",
    ),
    "cuentas": os.getenv(
        "CUENTAS_URL",
        "http://host.docker.internal:8002",
    ),
    "tarjetas": os.getenv(
        "TARJETAS_URL",
        "http://host.docker.internal:8003",
    ),
    "core": os.getenv(
        "CORE_URL",
        "http://core:8000",
    ),
}

# Credenciales de integración
BUS_TOKEN = os.getenv("BUS_TOKEN")
BUS_CORE_TOKEN = os.getenv("BUS_CORE_TOKEN")

CLIENTES_TOKEN = os.getenv("CLIENTES_TOKEN")
CORE_TOKEN = os.getenv("CORE_TOKEN")

# Tokens opcionales para módulos consumidores
BUS_TOKENS_MODULOS = os.getenv(
    "BUS_TOKENS_MODULOS",
    "",
)

# Tiempo máximo de espera: 30 segundos
BUS_TIMEOUT_SEG = float(
    os.getenv("BUS_TIMEOUT_SEG", "30")
)
