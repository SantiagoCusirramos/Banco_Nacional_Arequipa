# Cajero ATM · Prototipo v0.2

Pantalla de un cajero que autentica la tarjeta, consulta saldo y retira efectivo a través
del Bus de Servicios, con extorno automático si el efectivo no se entrega.
Todo es simulado y local: saldos, tarjetas, Cuentas y Tarjetas son de prueba.

    cajero (8000) → Bus de Servicios (8001) → Tarjetas (8003)
                                            → Cuentas  (8002)

## Ejecutar

Requiere Python 3.11 o superior. Desde la carpeta del proyecto:

    python3 iniciar.py            # demostración
    python3 iniciar.py pruebas    # demostración con el panel de pruebas visible

Abrir http://localhost:8000. Ctrl+C detiene todo.
En Windows, si `python3` no funciona, usar `python iniciar.py`.

Cada pieza también puede levantarse por separado, cada una en su terminal:

    python3 cuentas/cuentas_sim.py
    python3 tarjetas/tarjetas_sim.py
    python3 bus/bus_servicios.py
    python3 atm/servidor_atm.py

## Puertos

| Parte | Puerto |
|---|---|
| Pantalla y servidor del cajero | 8000 |
| Bus de Servicios | 8001 |
| Cuentas (simulado) | 8002 |
| Tarjetas (simulado) | 8003 |

## Tarjetas y claves de prueba

| Tarjeta | Clave | Qué ofrece |
|---|---|---|
| 4821 | 1234 | Dos cuentas habilitadas (PEN y USD). Una tercera, conjunta, no se muestra |
| 7730 | 5678 | Una cuenta en soles |
| 0000 | 0000 | Sin cuentas habilitadas (cuenta bloqueada) |
| 5555 | 5555 | Cuentas para probar saldo insuficiente (S/ 80) y tope diario; sirve también para probar el bloqueo (tres claves erróneas) |

Tres claves incorrectas bloquean la tarjeta. La sesión dura 120 s y solo sirve para la tarjeta que la abrió.
Tope diario de retiro: S/ 1,500 o US$ 500. Los montos son múltiplos de 10.

## Flujo de demostración

1. Elegir la tarjeta 4821 en el selector e ingresar la clave 1234 con el teclado.
2. Elegir «Retirar efectivo», la cuenta en soles y un monto (por ejemplo S/ 270).
3. El cajero entrega los billetes y muestra el comprobante; las bandejas descuentan lo entregado.
4. Elegir «Consultar saldo» para ver el saldo ya descontado.

## Panel de pruebas (`python3 iniciar.py pruebas`)

Permite provocar una falla del dispensador (atasco o sin respuesta), la pérdida de una respuesta del Bus,
reponer billetes, conciliar operaciones pendientes y reiniciar los saldos. Con el atasco activado, un
retiro termina en extorno automático y el cliente no pierde dinero.

## Pruebas automáticas

    python3 -m pytest tests -v

Son 40 pruebas (consulta, clave, retiro, extorno, idempotencia, conciliación, latencia y datos sensibles).
Cada prueba levanta sus propios servicios en puertos de prueba. Los resultados se guardan en `tests/salida/`.

## Rutas del cajero

| Ruta | Uso |
|---|---|
| POST /api/retiro | Retiro completo: autoriza, dispensa y confirma, o extorna |
| GET /api/estado | Bandejas de billetes y operaciones pendientes |
| POST /api/reponer | Repone las bandejas |
| POST /api/conciliar | Reintenta las reversiones pendientes |
| POST /api/pruebas | Modo de prueba (solo con `pruebas`) |

## Dos laptops

Bus, Cuentas y Tarjetas en una laptop y la pantalla en la otra. En la pantalla, abrir «Conexión» y cambiar
localhost por la IP de la laptop del Bus, por ejemplo http://192.168.1.10:8001.

## Registro

El cajero guarda `registro_operaciones.jsonl` con cada paso de una operación, su correlación y la tarjeta
enmascarada; no guarda clave, token ni número de tarjeta completo.

## Logo

La pantalla toma el logo de `atm/logo.png`.
