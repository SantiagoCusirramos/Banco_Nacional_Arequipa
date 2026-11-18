# Solicitud de Crédito (SOL): empezar aquí

SOL ya no es un laboratorio con base propia: no hay `bna_sol_mvp`, `SOL.manage init`, cuentas de demostración ni modo SIMULADO. Corre con el producto (`./bna up`) y se entra con un usuario de COREDB (ASESOR para preparar y enviar).

1. `./bna up`.
2. Con el administrador (`grep BNA_ADMIN_PASSWORD .env`), crea un usuario ASESOR: `POST /coredb/usuarios` con `"rol": "ASESOR"`.
3. Entra en http://localhost:3000/solicitud-credito con ese usuario. Los clientes son los que CAPTACION habilitó (http://localhost:3000/captacion).

Todo lo demás (flujo, contratos, configuración y la tabla «Qué cambió» con lo que se quitó) está en [`backend/SOL/README.md`](backend/SOL/README.md). La documentación histórica del laboratorio sigue en [`Documents/solicitud-credito/`](Documents/solicitud-credito/).
