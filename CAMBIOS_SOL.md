# Archivos de esta entrega — MVP v2

Base: ZIP Banco_Nacional_Arequipa-main(1). No se descargó ni modificó la rama remota.

El ZIP completo sirve para ejecutar localmente. Cuando se use un clon actualizado, revisar y llevar únicamente los cambios listados; no sobrescribir otros módulos. Los archivos de CORE y los scripts SQL comunes conservan el contenido de la base revisada.

## Actualización v2 respecto al MVP anterior

Ver `Documents/solicitud-credito/CORRECCIONES_V2.md` para la correspondencia con los 14 pedidos y `CONTRATOS_HTTP_V2.md` para coordinar con los demás equipos. `EMPEZAR_AQUI_SOL.md` contiene la actualización sin borrar la base.

Se modifican archivos SOL del backend (API, persistencia, ajustes, servicio, integración, seed, gestión y pruebas), requirements-sol.txt, .env.sol.example, los dos archivos TypeScript de SOL y las guías del módulo. Se añaden clock.py, operations.py, observability.py, migrations.py, simulator.py y test_integration_v2.py. Las evidencias nuevas están en `Documents/solicitud-credito/evidencias-v2/`.

La política, las fórmulas financieras y los archivos de los demás módulos conservan el contenido de v1. El ZIP incluye `PARCHE_SOL_v2.patch` para revisar diferencias respecto a la entrega anterior; no debe aplicarse a ciegas sobre cambios posteriores del equipo.

## Archivos existentes modificados (base v1)

- `.gitignore`
- `README.md`

## Archivos nuevos

- `Documents/solicitud-credito/CONTRATOS_DEMO.md`
- `Documents/solicitud-credito/LECTURA_DEL_CODIGO.md`
- `Documents/solicitud-credito/PROPUESTAS_Y_DECISIONES.md`
- `Documents/solicitud-credito/VALIDACION.md`
- `EMPEZAR_AQUI_SOL.md`
- `backend/.env.sol.example`
- `backend/SOL/__init__.py`
- `backend/SOL/app.py`
- `backend/SOL/config/politica_demo.json`
- `backend/SOL/database.py`
- `backend/SOL/finance.py`
- `backend/SOL/integrations.py`
- `backend/SOL/manage.py`
- `backend/SOL/models.py`
- `backend/SOL/policy.py`
- `backend/SOL/schemas.py`
- `backend/SOL/security.py`
- `backend/SOL/seed.py`
- `backend/SOL/service.py`
- `backend/SOL/settings.py`
- `backend/SOL/tests/conftest.py`
- `backend/SOL/tests/test_workflow.py`
- `backend/requirements-sol.txt`
- `frontend/.env.sol.example`
- `frontend/app/api/solicitud-credito/[...path]/route.ts`
- `frontend/app/solicitud-credito/layout.tsx`
- `frontend/app/solicitud-credito/page.tsx`
- `frontend/app/solicitud-credito/sol.css`

- `CAMBIOS_SOL.md` (este registro).

## Integración posterior

Usar la rama solicitud_credito del clon del repositorio. Verificar primero cambios remotos y acuerdos de propiedad de datos. Los endpoints, tablas locales y simuladores de esta entrega no se activan automáticamente sobre el CORE. No se incluyen tus contraseñas ni archivos de credenciales reales, bases de datos, dependencias instaladas ni compilados.
