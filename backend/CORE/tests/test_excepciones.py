import pytest

from CORE.exceptions import (
    BlockedAccountError,
    CoreError,
    InsufficientFundsError,
    NotFoundError,
)


def test_core_error_codes():
    err = CoreError("MI_CODIGO", "mensaje", status_code=418, details={"k": 1})
    assert err.code == "MI_CODIGO"
    assert err.status_code == 418
    assert err.details == {"k": 1}


def test_not_found_es_404():
    err = NotFoundError("X", "y")
    assert err.status_code == 404


def test_saldo_insuficiente():
    err = InsufficientFundsError("100.00", "250.00")
    assert err.code == "SALDO_INSUFICIENTE"
    assert err.details["monto_solicitado"] == "250.00"


def test_cuenta_bloqueada():
    err = BlockedAccountError("20260115000001", "BLOQUEADA")
    assert err.code == "CUENTA_NO_OPERATIVA"
    assert "RGN-09" in err.message
