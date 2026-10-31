-- Sin esto, el cliente del contenedor lee este archivo como latin1.
SET NAMES utf8mb4;

-- =====================================================================
-- Datos de referencia SOLO PARA DESARROLLO (MySQL 8.4)
-- =====================================================================
-- Se carga después de sql/bna_extension.sql para que una base nueva pueda hacer
-- un depósito. No va en producción: los datos reales los mantiene bna_admin.
-- El periodo es el del mes en curso al crear el volumen: al cambiar de mes hay
-- que recrear el volumen o agregar otro periodo.
SET @hoy = DATE(CONVERT_TZ(UTC_TIMESTAMP(), '+00:00', 'America/Lima'));

INSERT INTO core.periodo_contable (anio, mes, fecha_inicio, fecha_fin, estado)
VALUES (YEAR(@hoy), MONTH(@hoy), DATE_FORMAT(@hoy, '%Y-%m-01'), LAST_DAY(@hoy), 'ABIERTO');

INSERT INTO core.agencia VALUES
    ('AQP01', 'Agencia Arequipa Centro', 'Calle Mercaderes 120', 'Cercado', 'Arequipa', 'ACTIVA');

INSERT INTO core.terminal (id_terminal, descripcion, activo, id_canal, id_agencia) VALUES
    ('DEV-ATM-01', 'Cajero de desarrollo', TRUE, 'ATM', 'AQP01'),
    ('DEV-AGE-01', 'Agente de desarrollo', TRUE, 'AGE', 'AQP01'),
    ('DEV-VEN-01', 'Ventanilla de desarrollo', TRUE, 'VEN', 'AQP01'),
    ('DEV-HB-01', 'Home Banking de desarrollo', TRUE, 'HB', NULL),
    ('DEV-BD-01', 'Billetera Digital de desarrollo', TRUE, 'BD', NULL);

INSERT INTO tarjetas.bin_tarjeta VALUES ('004499', 'FISICA', 'Débito BNA física');

-- Un cliente para abrir la cuenta del depósito.
INSERT INTO clientes.verificacion_captacion (id_verificacion_captacion, estado_habilitante)
VALUES ('VC-DEV-1', 'HABILITADO');
INSERT INTO clientes.cliente (cod_cliente, tipo_documento, numero_documento, nombres, apellido_paterno,
                                     correo, celular, estado_cliente, id_verificacion_captacion, version_contrato)
VALUES ('DEV001', 'DNI', '70000099', 'Cliente', 'Desarrollo', 'dev@example.com', '959000099', 'ACTIVO',
        'VC-DEV-1', 'v1');
