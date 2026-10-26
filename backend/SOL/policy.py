"""Lee y valida las políticas desde un único JSON versionado."""

import json
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Policy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    estado_aprobacion: str
    producto_id: str
    producto_nombre: str
    monedas: list[str]
    monto_minimo: Decimal = Field(gt=0)
    monto_maximo: Decimal = Field(gt=0)
    plazo_minimo_meses: int = Field(ge=1)
    plazo_maximo_meses: int = Field(ge=1, le=600)
    tea: Decimal = Field(ge=0, le=5)
    amortizacion: str
    dias_por_periodo: int = Field(ge=1, le=366)
    redondeo: str
    pago_doble_habilitado: bool
    cargos_adicionales: Decimal
    origen_tasa_plazo: str
    origen_montos: str
    nota: str

    @model_validator(mode="after")
    def consistent(self):
        if (
            self.monto_maximo < self.monto_minimo
            or self.plazo_maximo_meses < self.plazo_minimo_meses
        ):
            raise ValueError("Los límites de la política están invertidos.")
        # Evita afirmar soporte a fórmulas que este MVP aún no implementa.
        if self.amortizacion != "FRANCES" or self.redondeo != "ROUND_HALF_UP":
            raise ValueError("Este MVP solo implementa FRANCES y ROUND_HALF_UP.")
        if self.pago_doble_habilitado or self.cargos_adicionales != 0:
            raise ValueError(
                "Pago doble y cargos requieren implementar la regla aprobada."
            )
        if not self.monedas or any(c not in {"PEN", "USD"} for c in self.monedas):
            raise ValueError("Monedas no soportadas por el catálogo local.")
        return self


def load_policy(path) -> Policy:
    """Sin valores de respaldo: un archivo inválido bloquea nuevas operaciones."""
    return Policy.model_validate(json.loads(path.read_text(encoding="utf-8")))
