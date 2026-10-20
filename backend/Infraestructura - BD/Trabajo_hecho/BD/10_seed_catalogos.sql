-- =====================================================================
-- BNA - Script 10: Carga de catalogos (seed)
-- Motor: MySQL 8.0 / 8.4  |  InnoDB  |  utf8mb4
-- Version: v1.0.0   Fecha: 2026-10-15
-- IDs: UUID v7 (CHAR(36)) fijos, para que la carga siga siendo idempotente.
-- Uso: idempotente (INSERT IGNORE / ON DUPLICATE KEY UPDATE).
-- =====================================================================
USE bna;
SET NAMES utf8mb4;

-- Agencias (4 iniciales en Arequipa)
INSERT IGNORE INTO agencia (id_agencia, nombre, direccion, activa) VALUES
 ('0198b000-0000-7001-8000-000000000001','Agencia Arequipa Centro','Calle Mercaderes 120, Arequipa',1),
 ('0198b000-0000-7001-8000-000000000002','Agencia Cayma','Av. Ejercito 505, Cayma, Arequipa',1),
 ('0198b000-0000-7001-8000-000000000003','Agencia Yanahuara','Av. Bolognesi 210, Yanahuara, Arequipa',1),
 ('0198b000-0000-7001-8000-000000000004','Agencia Paucarpata','Av. Goyeneche 850, Paucarpata, Arequipa',1);

-- Tipos de documento
INSERT IGNORE INTO tipo_documento (cod_tipo_documento, descripcion) VALUES
 ('DNI','Documento Nacional de Identidad'),
 ('CE','Carnet de Extranjeria'),
 ('PASAPORTE','Pasaporte'),
 ('PTP','Permiso Temporal de Permanencia'),
 ('RUC','Registro Unico de Contribuyentes');

-- Monedas
INSERT IGNORE INTO moneda (cod_moneda, nombre, simbolo, activa) VALUES
 ('PEN','Sol Peruano','S/',1),
 ('USD','Dolar Estadounidense','$',1);

-- Tipo de cambio de ejemplo
INSERT IGNORE INTO tipo_cambio (id_tipo_cambio, cod_moneda_origen, cod_moneda_destino, fecha, tasa) VALUES
 ('0198b000-0000-7011-8000-000000000001','USD','PEN','2026-10-15',3.750000),
 ('0198b000-0000-7011-8000-000000000002','PEN','USD','2026-10-15',0.266667);

-- Canales de atencion
INSERT IGNORE INTO canal (id_canal, nombre, es_presencial, validacion_requerida, requiere_token_matriz, tipo_integracion, activo) VALUES
 ('ATM','Cajero Automatico',1,'PIN_ATM',0,'BUS_SERVICIOS',1),
 ('AGE','Agente / Ventanilla',1,'PIN_ATM',0,'BUS_SERVICIOS',1),
 ('VEN','Ventanilla',1,'PIN_ATM',0,'BUS_SERVICIOS',1),
 ('HB','Home Banking',0,'CLAVE_WEB',0,'API_REST',1),
 ('BD','Banca por Dispositivo',0,'TOKEN_PAGO',1,'API_REST',1);

-- Topes por canal y moneda (NULL = sin limite)
INSERT IGNORE INTO limite_canal (id_canal, moneda, monto_maximo_diario, habilitado, regla_negocio) VALUES
 ('ATM','PEN',700.00,1,'TOPE_ATM_PEN'),
 ('AGE','PEN',5000.00,1,'TOPE_AGENTE_PEN'),
 ('VEN','PEN',NULL,1,'TOPE_VENTANILLA_PEN'),
 ('HB','PEN',2000.00,1,'TOPE_HB_PEN'),
 ('BD','USD',1500.00,1,'TOPE_BANCADIGITAL_USD');

-- Productos de ahorro
INSERT IGNORE INTO producto_ahorro (id_producto_ahorro, nombre, moneda, tasa_tea, activo) VALUES
 ('0198b000-0000-7004-8000-000000000001','Ahorro Libre',          'PEN',0.0100,1),
 ('0198b000-0000-7004-8000-000000000002','Ahorro Programado',     'PEN',0.0350,1),
 ('0198b000-0000-7004-8000-000000000003','Ahorro Infantil',       'PEN',0.0150,1),
 ('0198b000-0000-7004-8000-000000000004','Ahorro CTS',            'PEN',0.0400,1),
 ('0198b000-0000-7004-8000-000000000005','Ahorro a Plazo Fijo',   'PEN',0.0550,1),
 ('0198b000-0000-7004-8000-000000000006','Ahorro Libre Dolares',  'USD',0.0050,1);

-- Productos de credito
INSERT IGNORE INTO producto_credito (id_producto_credito, nombre, tasa_tea, plazo_min_meses, plazo_max_meses, activo) VALUES
 ('0198b000-0000-7005-8000-000000000001','Credito Personal',        0.2200,6,60,1),
 ('0198b000-0000-7005-8000-000000000002','Credito Microempresa',    0.2800,6,48,1),
 ('0198b000-0000-7005-8000-000000000003','Credito Hipotecario',     0.1050,60,300,1),
 ('0198b000-0000-7005-8000-000000000004','Credito Vehicular',       0.1500,12,72,1);

-- Periodos contables 2026
INSERT IGNORE INTO periodo_contable (id_periodo, anio, mes, fecha_inicio, fecha_fin, estado) VALUES
 ('0198b000-0000-7010-8000-000000000001',2026,1,'2026-01-01','2026-01-31','ABIERTO'),
 ('0198b000-0000-7010-8000-000000000002',2026,2,'2026-02-01','2026-02-28','ABIERTO'),
 ('0198b000-0000-7010-8000-000000000003',2026,3,'2026-03-01','2026-03-31','ABIERTO'),
 ('0198b000-0000-7010-8000-000000000004',2026,4,'2026-04-01','2026-04-30','ABIERTO'),
 ('0198b000-0000-7010-8000-000000000005',2026,5,'2026-05-01','2026-05-31','ABIERTO'),
 ('0198b000-0000-7010-8000-000000000006',2026,6,'2026-06-01','2026-06-30','ABIERTO'),
 ('0198b000-0000-7010-8000-000000000007',2026,7,'2026-07-01','2026-07-31','ABIERTO'),
 ('0198b000-0000-7010-8000-000000000008',2026,8,'2026-08-01','2026-08-31','ABIERTO'),
 ('0198b000-0000-7010-8000-000000000009',2026,9,'2026-09-01','2026-09-30','ABIERTO'),
 ('0198b000-0000-7010-8000-00000000000a',2026,10,'2026-10-01','2026-10-31','ABIERTO'),
 ('0198b000-0000-7010-8000-00000000000b',2026,11,'2026-11-01','2026-11-30','ABIERTO'),
 ('0198b000-0000-7010-8000-00000000000c',2026,12,'2026-12-01','2026-12-31','ABIERTO');

-- Plan de cuentas contables (extracto)
INSERT IGNORE INTO plan_cuenta_contable (cod_cuenta_contable, nombre, naturaleza, codigo_padre, activo) VALUES
 ('1','ACTIVO','DEUDORA',NULL,1),
 ('2','PASIVO','ACREEDORA',NULL,1),
 ('3','PATRIMONIO','ACREEDORA',NULL,1),
 ('4','INGRESOS','ACREEDORA',NULL,1),
 ('5','GASTOS','DEUDORA',NULL,1),
 ('1101','Caja','DEUDORA','1',1),
 ('1102','Fondos en Banco Central','DEUDORA','1',1),
 ('1103','Cuentas por Cobrar','DEUDORA','1',1),
 ('2101','Depositos de Ahorro','ACREEDORA','2',1),
 ('2102','Depositos a Plazo','ACREEDORA','2',1),
 ('2103','Obligaciones con el Publico','ACREEDORA','2',1),
 ('4101','Ingresos por Intereses','ACREEDORA','4',1),
 ('4102','Ingresos por Comisiones','ACREEDORA','4',1),
 ('4103','Ingresos por Mora','ACREEDORA','4',1),
 ('5101','Gastos por Intereses','DEUDORA','5',1),
 ('5102','Gastos Operativos','DEUDORA','5',1),
 ('5103','Provision Custodia','DEUDORA','5',1);

-- Reglas de evaluacion (tramos del informe)
INSERT IGNORE INTO eva_regla (id_regla, nombre, descripcion, variable, operador, valor_min, valor_max, resultado, peso, activa) VALUES
 ('0198b000-0000-7007-8000-000000000001','RATIO_SALUDABLE','Ratio cuota/ingreso hasta 80%','ratio_capacidad','ENTRE',0,0.80,'APROBAR',1.00,1),
 ('0198b000-0000-7007-8000-000000000002','RATIO_LIMITE','Ratio cuota/ingreso hasta 100%','ratio_capacidad','ENTRE',0.80,1.00,'OBSERVAR',1.00,1),
 ('0198b000-0000-7007-8000-000000000003','RATIO_INSUFICIENTE','Ratio cuota/ingreso mayor a 100%','ratio_capacidad','MAYOR',1.00,NULL,'RECHAZAR',1.00,1),
 ('0198b000-0000-7007-8000-000000000004','MORA_RECIENTE','Dias de mayor mora en central','dias_mayor_mora','MAYOR',30,NULL,'OBSERVAR',0.50,1),
 ('0198b000-0000-7007-8000-000000000005','MORA_GRAVE','Dias de mayor mora mayor a 120','dias_mayor_mora','MAYOR',120,NULL,'RECHAZAR',1.00,1);

-- Canales de pago
INSERT IGNORE INTO canal_pago (id_canal_pago, nombre, tipo, activo) VALUES
 ('0198b000-0000-7008-8000-000000000001','Ventanilla Agencia','VENTANILLA',1),
 ('0198b000-0000-7008-8000-000000000002','Agente BNA','AGENTE',1),
 ('0198b000-0000-7008-8000-000000000003','Cajero Automatico','ATM',1),
 ('0198b000-0000-7008-8000-000000000004','Banca por Internet','BANCA_WEB',1),
 ('0198b000-0000-7008-8000-000000000005','App Movil','APP',1),
 ('0198b000-0000-7008-8000-000000000006','Domiciliacion','DOMICILIACION',1),
 ('0198b000-0000-7008-8000-000000000007','Transferencia Interbancaria','TRANSFERENCIA',1);

-- Empleados de ejemplo
INSERT IGNORE INTO empleado (id_empleado, codigo_empleado, nombre_completo, cargo, id_agencia, activo) VALUES
 ('0198b000-0000-7002-8000-000000000001','BNA-0001','Asesor Demo Arequipa','ASESOR_CREDITOS','0198b000-0000-7001-8000-000000000001',1),
 ('0198b000-0000-7002-8000-000000000002','BNA-0002','Analista Demo Arequipa','ANALISTA_CREDITO','0198b000-0000-7001-8000-000000000001',1),
 ('0198b000-0000-7002-8000-000000000003','BNA-0003','Operador Demo Arequipa','OPERADOR','0198b000-0000-7001-8000-000000000001',1),
 ('0198b000-0000-7002-8000-000000000004','BNA-0004','Cajero Demo Arequipa','CAJERO','0198b000-0000-7001-8000-000000000001',1);

-- Usuarios del sistema de ejemplo
INSERT IGNORE INTO usuario_sistema (id_usuario, username, nombre, rol, hash_password, id_empleado, activo) VALUES
 ('0198b000-0000-7003-8000-000000000001','admin.bna','Administrador BNA','ADMINISTRADOR',SHA2('admin123',256),'0198b000-0000-7002-8000-000000000001',1),
 ('0198b000-0000-7003-8000-000000000002','asesor.bna','Asesor Demo','ASESOR',SHA2('asesor123',256),'0198b000-0000-7002-8000-000000000001',1),
 ('0198b000-0000-7003-8000-000000000003','analista.bna','Analista Demo','ANALISTA',SHA2('analista123',256),'0198b000-0000-7002-8000-000000000002',1),
 ('0198b000-0000-7003-8000-000000000004','operador.bna','Operador Demo','OPERADOR',SHA2('operador123',256),'0198b000-0000-7002-8000-000000000003',1),
 ('0198b000-0000-7003-8000-000000000005','auditor.bna','Auditor Demo','AUDITOR',SHA2('auditor123',256),NULL,1);

-- Terminales de ejemplo
INSERT IGNORE INTO terminal (id_terminal, codigo, tipo, ubicacion, id_agencia, activa) VALUES
 ('0198b000-0000-7006-8000-000000000001','ATM-ARQ-001','ATM','Agencia Arequipa Centro','0198b000-0000-7001-8000-000000000001',1),
 ('0198b000-0000-7006-8000-000000000002','ATM-ARQ-002','ATM','Agencia Cayma','0198b000-0000-7001-8000-000000000002',1),
 ('0198b000-0000-7006-8000-000000000003','POS-ARQ-001','POS','Agencia Yanahuara','0198b000-0000-7001-8000-000000000003',1),
 ('0198b000-0000-7006-8000-000000000004','WEB-BNA-001','WEB','Plataforma web',NULL,1),
 ('0198b000-0000-7006-8000-000000000005','MOV-BNA-001','MOVIL','Aplicacion movil',NULL,1);
