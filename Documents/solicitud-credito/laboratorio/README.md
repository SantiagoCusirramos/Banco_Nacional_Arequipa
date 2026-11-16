# Laboratorio CAP/SOL/EVA — preparación sin arranque

Consultar [informe y puertas de autorización](../sol-laboratorio-build.md) antes de usar estos archivos. No hay autorización de build, arranque o SQL en SOL-LAB-BUILD.

- `prepare.py`: captura código permitido y genera secretos sintéticos fuera de Git; no usa Docker ni conexiones de base.
- `compose.yaml`: 12 servicios; proyecto exclusivo, dos MySQL tmpfs, redes internas, sin puertos públicos. Formato JSON, válido como YAML de Compose.
- `compose.audit-sim.yaml`: overlay opcional, 13.º servicio simulador existente. No incorporado por defecto; requiere autorización académica separada.
- `Dockerfile.api`, `Dockerfile.core`: recetas exclusivas; todavía no construidas.
- `guard.py`: gates de escrituras y de auditoría simulada, sin alterar módulos bancarios.
- `bootstrap_sol.py`: bootstrap mínimo exclusivo de SOL; no se ha ejecutado.
- `http_probe.py`: ejecutor futuro de sondas HTTP; no valida por sí solo el flujo de negocio.
- `validate.py`: hashes/AST, secretos, permisos, Compose config y restricciones de aislamiento, sin daemon ni inicialización.
- `test_static.py`: nueve casos negativos del validador en memoria.
- `sources-manifest.json` y `evidencias-http-independientes.json`: salidas locales generadas, excluidas del commit de cierre. `prepare.py` produce un manifiesto nuevo fuera del repositorio; los resultados saneados se conservan en los informes, sin versionar fixtures generadas.

La captura del cierre está en `/tmp/bna-sol-lab-lab20261116d-rd3tyyye`; es temporal. No adjuntar su subdirectorio `runtime/`, ni imprimir `docker compose config` interpolado. Si desaparece, ejecutar una nueva captura y renovar el manifiesto/evidencias.

Validaciones seguras, desde la raíz del repositorio:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 Documents/solicitud-credito/laboratorio/validate.py /tmp/bna-sol-lab-lab20261116d-rd3tyyye
PYTHONDONTWRITEBYTECODE=1 python3 Documents/solicitud-credito/laboratorio/test_static.py /tmp/bna-sol-lab-lab20261116d-rd3tyyye
```

Para otra captura, elegir identificador alfanumérico minúsculo exclusivo de 8–24 caracteres y ejecutar `prepare.py --run-id <identificador>`. Solo imprime la ruta privada. No reutilizar identificadores de un ensayo existente; comprobar colisiones antes de construir o arrancar. No usar `source` sobre archivos externos ni versionar secretos.

Cierre SOL-LAB-CLOSE: ver [entrega](../sol-integracion-entrega-final.md) y [selección exacta del commit](../sol-integracion-archivos-commit.txt). `test_close_contracts.py` comprueba DTO/OpenAPI y caracteriza el riesgo2xx EVA sin SQL ni red. Las fuentes/registros temporales y todo `runtime/` quedan fuera de Git.
