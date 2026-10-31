-- Datos de prueba: un flujo completo que recorre las cinco bases (MySQL 8.4).
-- Los mismos de la rama main. Se cargan como root, en una sola transacción;
-- cada asiento se registra completo con core.registrar_asiento.
--
-- Identificadores fijos (para leer las pruebas):
--   clientes  C001 Juan (ACTIVO), C002 Ana (ACTIVO), C003 Luis (ACTIVO),
--             C004 Rosa (BLOQUEADO)
--   cuentas   CTA-PEN-1, CTA-USD-1 y CTA-CONJ de C001; CTA-PEN-2 de C002
--   tarjetas  T1 a...01 (C001), T2 a...02 (C002), T3 a...03 (C003)
--   créditos  solicitud S1 b...01 (C001, PEN 10 000) con evaluación E1,
--             calendario OFICIAL CAL1 d...01, orden confirmada O1 e...01,
--             crédito CR-0001 y pagos P1 (3 100) y P2 (4 000);
--             solicitud S2 b...02 (C002) con E2, CAL2 y órdenes O2
--             (PREPARADA) y O3 (POR_VERIFICAR)
START TRANSACTION;

INSERT INTO core.agencia VALUES ('AQP01', 'Agencia Arequipa Centro', 'Calle Mercaderes 120', 'Cercado', 'Arequipa', 'ACTIVA');
INSERT INTO core.cuenta_contable VALUES ('1101', 'Caja', 'DEUDORA', NULL), ('2101', 'Depósitos de ahorro', 'ACREEDORA', NULL);
INSERT INTO core.terminal VALUES ('ATM-AQP-001', 'Cajero agencia centro', TRUE, 'ATM', 'AQP01'),
                                 ('ATM-AQP-OFF', 'Cajero fuera de servicio', FALSE, 'ATM', 'AQP01');

INSERT INTO clientes.verificacion_captacion (id_verificacion_captacion, estado_habilitante) VALUES
    ('VC-1', 'HABILITADO'), ('VC-2', 'HABILITADO'), ('VC-3', 'HABILITADO'), ('VC-4', 'HABILITADO');
INSERT INTO clientes.cliente (cod_cliente, tipo_documento, numero_documento, nombres, apellido_paterno,
                              apellido_materno, correo, celular, estado_cliente, id_verificacion_captacion,
                              version_contrato) VALUES
    ('C001', 'DNI', '70000001', 'Juan', 'Pérez', 'Quispe', 'juan@example.com', '959000001', 'ACTIVO', 'VC-1', 'v1'),
    ('C002', 'DNI', '70000002', 'Ana', 'Díaz', NULL, 'ana@example.com', '959000002', 'ACTIVO', 'VC-2', 'v1'),
    ('C003', 'DNI', '70000003', 'Luis', 'Torres', NULL, 'luis@example.com', '959000003', 'ACTIVO', 'VC-3', 'v1'),
    ('C004', 'DNI', '70000004', 'Rosa', 'Mamani', NULL, 'rosa@example.com', '959000004', 'BLOQUEADO', 'VC-4', 'v1');

INSERT INTO cuentas.cuenta_ahorro (num_cuenta, cci, moneda, regimen, estado_cuenta, id_agencia) VALUES
    ('CTA-PEN-1', '00219100000000000101', 'PEN', 'INDIVIDUAL', 'ACTIVA', 'AQP01'),
    ('CTA-USD-1', '00219100000000000102', 'USD', 'INDIVIDUAL', 'ACTIVA', 'AQP01'),
    ('CTA-CONJ', '00219100000000000103', 'PEN', 'MANCOMUNADA_CONJUNTA', 'ACTIVA', 'AQP01'),
    ('CTA-PEN-2', '00219100000000000201', 'PEN', 'INDIVIDUAL', 'ACTIVA', 'AQP01');
INSERT INTO cuentas.titularidad (cod_cliente, num_cuenta) VALUES
    ('C001', 'CTA-PEN-1'), ('C001', 'CTA-USD-1'), ('C001', 'CTA-CONJ'), ('C002', 'CTA-CONJ'), ('C002', 'CTA-PEN-2');
CALL prueba.movimiento('CTA-PEN-1', 'DEPOSITO', 5000, 'VEN', NULL, NULL, @m);
CALL prueba.movimiento('CTA-USD-1', 'DEPOSITO', 1000, 'VEN', NULL, NULL, @m);
CALL prueba.movimiento('CTA-CONJ', 'DEPOSITO', 1000, 'VEN', NULL, NULL, @m);
CALL prueba.movimiento('CTA-PEN-2', 'DEPOSITO', 5000, 'VEN', NULL, NULL, @m);

INSERT INTO tarjetas.bin_tarjeta VALUES ('455788', 'FISICA', 'Débito BNA física');
INSERT INTO tarjetas.tarjeta (id_tarjeta, pan_token, bin, ultimos4, fecha_emision, fecha_vencimiento,
                              estado_tarjeta, cod_cliente) VALUES
    (UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'tok-0001', '455788', '1234', '2026-01-10', '2031-01-31', 'ACTIVA', 'C001'),
    (UUID_TO_BIN('a0000000-0000-4000-8000-000000000002'), 'tok-0002', '455788', '5678', '2026-01-10', '2031-01-31', 'ACTIVA', 'C002'),
    (UUID_TO_BIN('a0000000-0000-4000-8000-000000000003'), 'tok-0003', '455788', '9012', '2026-01-10', '2031-01-31', 'ACTIVA', 'C003');
INSERT INTO tarjetas.tarjeta_cuenta (id_tarjeta, num_cuenta, es_principal) VALUES
    (UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-PEN-1', TRUE),
    (UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-USD-1', FALSE),
    (UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-CONJ', FALSE),
    (UUID_TO_BIN('a0000000-0000-4000-8000-000000000002'), 'CTA-PEN-2', TRUE);
INSERT INTO tarjetas.credencial (id_tarjeta, tipo_credencial, hash_credencial, sal) VALUES
    (UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'PIN_ATM', REPEAT('a', 64), REPEAT('b', 32)),
    (UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CLAVE_WEB', REPEAT('c', 64), REPEAT('d', 32)),
    (UUID_TO_BIN('a0000000-0000-4000-8000-000000000002'), 'PIN_ATM', REPEAT('e', 64), REPEAT('f', 32));
INSERT INTO tarjetas.matriz_token (id_matriz, numero_serie, tipo_matriz, sal, estado_matriz, fecha_emision, id_tarjeta)
VALUES (UUID_TO_BIN('a1000000-0000-4000-8000-000000000001'), 'MTZ-0001', 'FISICA', REPEAT('g', 32), 'ACTIVA', '2026-01-10',
        UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'));

INSERT INTO creditos.analista VALUES ('AN01', 'Analista de prueba', 'EMP-001');
INSERT INTO creditos.solicitud_credito (id_solicitud, monto_solicitado, moneda, plazo_meses, estado_solicitud, cod_cliente) VALUES
    (UUID_TO_BIN('b0000000-0000-4000-8000-000000000001'), 10000, 'PEN', 3, 'APROBADA', 'C001'),
    (UUID_TO_BIN('b0000000-0000-4000-8000-000000000002'), 2000, 'PEN', 1, 'APROBADA', 'C002');
INSERT INTO creditos.situacion_financiera (id_consulta, resultado_verificacion, ingreso_mensual, deuda_reportada, cod_cliente) VALUES
    (UUID_TO_BIN('b1000000-0000-4000-8000-000000000001'), 'VERIFICADO', 6000, 0, 'C001'),
    (UUID_TO_BIN('b1000000-0000-4000-8000-000000000002'), 'VERIFICADO', 3000, 0, 'C002');
INSERT INTO creditos.evaluacion (id_evaluacion, ronda, score_calculado, limite_aprobado, id_solicitud, id_consulta,
                                 id_regla, id_analista) VALUES
    (UUID_TO_BIN('c0000000-0000-4000-8000-000000000001'), 1, 720, 10000, UUID_TO_BIN('b0000000-0000-4000-8000-000000000001'),
     UUID_TO_BIN('b1000000-0000-4000-8000-000000000001'), 'R-A', 'AN01'),
    (UUID_TO_BIN('c0000000-0000-4000-8000-000000000002'), 1, 650, 2000, UUID_TO_BIN('b0000000-0000-4000-8000-000000000002'),
     UUID_TO_BIN('b1000000-0000-4000-8000-000000000002'), 'R-A', 'AN01');
INSERT INTO creditos.calendario_pago (id_calendario, version, tipo_calendario, metodo_amortizacion, tasa_aplicada,
                                      estado_calendario, id_solicitud) VALUES
    (UUID_TO_BIN('d0000000-0000-4000-8000-000000000000'), 1, 'PRELIMINAR', 'FRANCES', 0.2200, 'HISTORICO', UUID_TO_BIN('b0000000-0000-4000-8000-000000000001')),
    (UUID_TO_BIN('d0000000-0000-4000-8000-000000000001'), 2, 'OFICIAL', 'FRANCES', 0.2200, 'VIGENTE', UUID_TO_BIN('b0000000-0000-4000-8000-000000000001')),
    (UUID_TO_BIN('d0000000-0000-4000-8000-000000000002'), 1, 'OFICIAL', 'FRANCES', 0.2200, 'VIGENTE', UUID_TO_BIN('b0000000-0000-4000-8000-000000000002'));
INSERT INTO creditos.cuota (id_calendario, numero_cuota, fecha_vencimiento, capital, interes, otros_conceptos,
                            saldo_capital, saldo_pendiente, estado_cuota) VALUES
    (UUID_TO_BIN('d0000000-0000-4000-8000-000000000001'), 1, '2026-11-15', 3000, 100, 0, 7000, 3100, 'PENDIENTE'),
    (UUID_TO_BIN('d0000000-0000-4000-8000-000000000001'), 2, '2026-12-15', 3000, 100, 0, 4000, 3100, 'PENDIENTE'),
    (UUID_TO_BIN('d0000000-0000-4000-8000-000000000001'), 3, '2027-01-15', 4000, 100, 0, 0, 4100, 'PENDIENTE'),
    (UUID_TO_BIN('d0000000-0000-4000-8000-000000000002'), 1, '2026-11-15', 2000, 40, 0, 0, 2040, 'PENDIENTE');

CALL prueba.movimiento('CTA-PEN-1', 'DESEMBOLSO', 10000, 'VEN', NULL, NULL, @abono);
INSERT INTO creditos.orden_desembolso (id_orden, codigo_orden, importe, estado_orden, idempotency_key, request_hash,
                                       usuario_preparacion, usuario_confirmacion, correlation_id, id_evaluacion,
                                       num_cuenta, id_canal, id_agencia, uuid_transaccion_abono)
VALUES (UUID_TO_BIN('e0000000-0000-4000-8000-000000000001'), 'DES-2026-000001', 10000, 'CONFIRMADA', core.uuid_v4(),
        REPEAT('h', 64), 'asesor.prueba', 'operador.prueba', core.uuid_v4(),
        UUID_TO_BIN('c0000000-0000-4000-8000-000000000001'), 'CTA-PEN-1', 'VEN', 'AQP01', @abono);
INSERT INTO creditos.orden_desembolso (id_orden, codigo_orden, importe, estado_orden, idempotency_key, request_hash,
                                       usuario_preparacion, correlation_id, id_evaluacion, num_cuenta, id_canal) VALUES
    (UUID_TO_BIN('e0000000-0000-4000-8000-000000000002'), 'DES-2026-000002', 2000, 'PREPARADA', core.uuid_v4(), REPEAT('i', 64),
     'asesor.prueba', core.uuid_v4(), UUID_TO_BIN('c0000000-0000-4000-8000-000000000002'), 'CTA-PEN-2', 'VEN'),
    (UUID_TO_BIN('e0000000-0000-4000-8000-000000000003'), 'DES-2026-000003', 2000, 'POR_VERIFICAR', core.uuid_v4(), REPEAT('j', 64),
     'asesor.prueba', core.uuid_v4(), UUID_TO_BIN('c0000000-0000-4000-8000-000000000002'), 'CTA-PEN-2', 'VEN');
INSERT INTO creditos.evento_entrega (tipo_evento, version_esquema, payload, estado_entrega, intentos, id_orden) VALUES
    ('desembolso.confirmado', 'v1', '{"orden": "DES-2026-000001"}', 'FALLIDO', 3, UUID_TO_BIN('e0000000-0000-4000-8000-000000000001')),
    ('desembolso.confirmado', 'v1', '{"orden": "DES-2026-000001"}', 'PENDIENTE', 1, UUID_TO_BIN('e0000000-0000-4000-8000-000000000001'));
INSERT INTO creditos.credito VALUES ('CR-0001', 'AL_DIA', UUID_TO_BIN('e0000000-0000-4000-8000-000000000001'),
                                     UUID_TO_BIN('d0000000-0000-4000-8000-000000000001'));
INSERT INTO creditos.pago (id_pago, monto_pago, referencia_transaccion, estado_confirmacion, cod_credito, id_canal) VALUES
    (UUID_TO_BIN('f0000000-0000-4000-8000-000000000001'), 3100, 'OP-0001', 'CONFIRMADO', 'CR-0001', 'VEN'),
    (UUID_TO_BIN('f0000000-0000-4000-8000-000000000002'), 4000, 'OP-0002', 'CONFIRMADO', 'CR-0001', 'HB');
INSERT INTO creditos.entidad_auditada VALUES ('e0000000-0000-4000-8000-000000000001', 'ORDEN');
INSERT INTO creditos.evento_auditoria (modulo_emisor, id_entidad, accion, resultado, actor, correlation_id)
VALUES (13, 'e0000000-0000-4000-8000-000000000001', 'CONFIRMAR_ORDEN', 'OK', 'operador.prueba', core.uuid_v4());
INSERT INTO creditos.historial_estado_solicitud (estado_nuevo, actor, id_solicitud)
VALUES ('APROBADA', 'analista.prueba', UUID_TO_BIN('b0000000-0000-4000-8000-000000000001'));

COMMIT;
