"""Configuración por ambiente. Variables con prefijo DESEMBOLSO_ (por ejemplo DESEMBOLSO_DATABASE_URL)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DESEMBOLSO_", env_file=".env", env_file_encoding="utf-8",
                                      extra="ignore")

    ambiente: str = "desarrollo"
    database_url: str = "mysql+pymysql://desembolso_user@127.0.0.1:3306/bna_desembolso"
    cors_origenes: str = "http://localhost:3000"

    # Módulos del producto (llamadas directas en la red de Docker; aún no hay Bus de Servicios)
    coredb_url: str = "http://127.0.0.1:8012"
    evaluacion_url: str = "http://127.0.0.1:8015"
    cuentas_url: str = "http://127.0.0.1:8001/api/v1/cuentas"
    # Vacía mientras Cobranza no esté en el producto: las entregas esperan sin gastar intentos.
    cobranza_url: str = ""
    cobranza_api_key: str = ""

    # Usuario de servicio de Desembolso en COREDB (rol SERVICIO, módulo DESEMBOLSO). El secreto
    # viene del entorno o del archivo que deja desembolso-init ({"username", "secreto"}).
    svc_usuario: str = "svc-desembolso"
    svc_secreto: str = ""
    svc_archivo: str = ""

    # Canal con el que se registra el abono en CUENTAS: ventanilla de la agencia.
    canal_cuentas: str = "VEN"
    # COREDB no informa la agencia del usuario: se toma de la instalación.
    agencia_id: str | None = None
    agencia_nombre: str | None = None
    sesion_cache_seg: float = 30.0

    # Integración (RT-04)
    timeout_dependencia_seg: float = 3.0
    timeout_abono_seg: float = 5.0
    reintentos_consulta: int = 2

    # Recuperación de órdenes inciertas (RN-07, RT-06)
    recuperacion_intervalo_seg: float = 10.0
    recuperacion_espera_seg: float = 30.0
    recuperacion_gracia_seg: float = 120.0
    alerta_incierta_min: float = 15.0

    # Entregas a Cobranza y avisos a Evaluación (RN-08)
    entrega_intervalo_seg: float = 5.0
    entrega_max_intentos: int = 10
    entrega_backoff_base_seg: float = 5.0
    entrega_backoff_max_seg: float = 900.0

    # Reglas configurables
    validacion_vigencia_min: int = 30
    # No confirmar si la primera cuota del calendario de SOL vence antes del desembolso:
    # Cobranza marcaría el crédito en mora apenas lo activa.
    validar_calendario: bool = True
    # Seguridad (laboratorio) no ofrece antifraude a los módulos: queda apagado.
    antifraude_habilitado: bool = False
    reversion_habilitada: bool = False
    reversion_plazo_horas: int = 24

    trabajos_habilitados: bool = True
