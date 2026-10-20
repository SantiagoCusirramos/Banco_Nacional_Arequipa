-- ============================================================================
-- CARGA DE DATOS INICIALES: PERMISOS (TODOS LOS POSIBLES PERMISOS QUE TENDRA CADA ROL)
-- ============================================================================
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE permiso;
SET FOREIGN_KEY_CHECKS = 1;

INSERT INTO permiso (id_permiso, nombre_permiso, descripcion) VALUES
-- Módulo Clientes (KYC)
(1, 'CLIENTE_LEER', 'Consulta de datos personales, biometría, historial KYC y códigos de verificación (GET)'),
(2, 'CLIENTE_CREAR', 'Registro de nuevos clientes, captura biométrica y emisión de códigos OTP (POST)'),
(3, 'CLIENTE_ACTUALIZAR', 'Modificación de datos de contacto y actualización de estado de validación KYC (PUT/PATCH)'),

-- Módulo Cuentas de Ahorro
(4, 'CUENTA_LEER', 'Consulta de cuentas de ahorro, vinculación de clientes, límites y topes diarios (GET)'),
(5, 'CUENTA_CREAR', 'Apertura de nuevas cuentas de ahorro y vinculación inicial de cliente a cuenta (POST)'),
(6, 'CUENTA_ACTUALIZAR', 'Modificación de topes diarios, cambio de estado (activa/bloqueada) y condiciones (PUT/PATCH)'),

-- Módulo Transacciones y Contabilidad
(7, 'TRANSACCION_EJECUTAR', 'Procesamiento de depósitos, retiros, abonos de intereses y generación de asientos contables (POST)'),
(8, 'TRANSACCION_LEER', 'Consulta de historial de transacciones, intereses generados y detalle de asientos contables (GET)'),

-- Módulo Tarjetas
(9, 'TARJETA_LEER', 'Consulta de tarjetas emitidas, tokens de pago, credenciales y matriz de coordenadas (GET)'),
(10, 'TARJETA_EMITIR', 'Emisión y vinculación de nuevas tarjetas de débito/crédito a cuentas de ahorro (POST)'),
(11, 'TARJETA_GESTIONAR', 'Bloqueo, anulación de tarjetas, autorización de pagos y gestión de tokens (PUT/PATCH)'),

-- Módulo Captación de Clientes
(12, 'CAPTACION_LEER', 'Consulta de prospectos (leads), perfilamiento de riesgo y reportes de buró de crédito (GET)'),
(13, 'CAPTACION_REGISTRAR', 'Ingreso de nuevos prospectos, registro de consentimientos y validación de identidad (POST)'),

-- Módulo Solicitud de Crédito
(14, 'SOLICITUD_LEER', 'Consulta de solicitudes de crédito, fiadores, garantías y calendarios de pago propuestos (GET)'),
(15, 'SOLICITUD_CREAR', 'Registro de solicitudes de crédito, adjunción de fiadores, garantías y simulaciones (POST)'),
(16, 'SOLICITUD_ACTUALIZAR', 'Modificación de datos, actualización de garantías o cambio de estado de solicitudes en curso (PUT/PATCH)'),

-- Módulo Evaluación y Decisión
(17, 'EVALUACION_LEER', 'Consulta del historial de evaluaciones crediticias y reglas del motor de riesgo (GET)'),
(18, 'EVALUACION_EJECUTAR', 'Ejecución del motor de reglas de riesgo y registro del dictamen del analista (POST)'),
(19, 'CREDITO_DECIDIR', 'Registro de la decisión final de aprobación o rechazo formal de la solicitud de crédito (POST/PUT)'),

-- Módulo Desembolso
(20, 'DESEMBOLSO_LEER', 'Consulta de órdenes de desembolso, validaciones y registros de entregas de efectivo (GET)'),
(21, 'DESEMBOLSO_EJECUTAR', 'Autorización y ejecución de entregas de dinero, transferencias y solicitudes de reversión (POST/PUT)'),

-- Módulo Cobranza
(22, 'COBRANZA_LEER', 'Consulta de cuotas pendientes, créditos en mora, historial de pagos y auditoría de cobranza (GET)'),
(23, 'COBRANZA_EJECUTAR', 'Registro de pagos de clientes, aplicación de abonos a cuotas/mora y eventos de recuperación (POST/PUT)'),

-- Transversales y Configuración Base
(24, 'SISTEMA_AUDITORIA', 'Consulta y mantenimiento de catálogos base (agencias, canales, empleados) y logs de auditoría (GET/POST/PUT)');