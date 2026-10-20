from CORE.services import rbac


def test_catalogo_completo():
    cat = rbac.obtener_catalogo()
    assert "REGISTRAR_MOVIMIENTO" in cat["acciones"]
    assert "GESTIONAR_PERMISOS" in cat["acciones"]
    assert len(cat["acciones"]) == 21


def test_admin_tiene_todo():
    acciones = rbac.acciones_de_rol("ADMINISTRADOR")
    assert set(acciones) == set(rbac.ACCIONES_CORE)


def test_rol_puede():
    assert rbac.rol_puede("OPERADOR", "REGISTRAR_MOVIMIENTO")
    assert not rbac.rol_puede("OPERADOR", "GESTIONAR_PERMISOS")
    assert not rbac.rol_puede("ASESOR", "EVALUAR_CREDITO")


def test_asignar_y_revocar():
    try:
        rbac.asignar_accion("AUDITOR", "CREAR_CLIENTE", actor="test")
        assert rbac.rol_puede("AUDITOR", "CREAR_CLIENTE")
    finally:
        pass
    # La asignación se persiste en el archivo; se revoca para no dejar
    # estado residual en el repo.
    rbac.revocar_accion("AUDITOR", "CREAR_CLIENTE", actor="test")
    assert not rbac.rol_puede("AUDITOR", "CREAR_CLIENTE")
