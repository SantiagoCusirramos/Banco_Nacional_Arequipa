-- ============================================================================
-- CARGA DE DATOS INICIALES: COMITE
-- ============================================================================

INSERT INTO comite (id_comite, nombre_comite, descripcion, estado) VALUES
(1, 'CORE', 'Gestion de operaciones centrales, agencias, canales y contabilidad del banco.', 'ACTIVO'),
(2, 'BUS DE SERVICIOS', 'Administracion de la integracion y comunicacion entre canales y el sistema core.', 'ACTIVO'),
(3, 'COMITE DE CALIDAD', 'Aseguramiento de calidad, pruebas de software y validacion de codigo para produccion.', 'ACTIVO'),
(4, 'COMITE PMI', 'Gestion, planificacion, priorizacion de proyectos y asignacion de recursos.', 'ACTIVO'),
(5, 'SEGURIDAD', 'Gestion de seguridad de la informacion y prevencion de fraudes.', 'ACTIVO'),
(6, 'CLIENTES', 'Gestion del registro, identificacion y validacion de datos de clientes.', 'ACTIVO'),
(7, 'CUENTAS', 'Administracion de productos de deposito, movimientos y calculo de intereses.', 'ACTIVO'),
(8, 'SOLICITUD DE CREDITO', 'Gestion y registro de solicitudes de financiamiento y condiciones crediticias.', 'ACTIVO'),
(9, 'COMITE DE INFRAESTRUCTURA', 'Gestion y administracion de la infraestructura tecnologica, servidores y bases de datos.', 'ACTIVO'),
(10, 'COMITE DE AHORROS (TRANSVERSAL)', 'Diseño, definicion y validacion funcional de productos y servicios de ahorros.', 'ACTIVO'),
(11, 'TARJETAS', 'Gestion de medios de pago, emision, claves, tokens y bloqueos.', 'ACTIVO'),
(12, 'CAJERO ATM', 'Administracion de la red de cajeros automaticos y procesamiento de transacciones.', 'ACTIVO'),
(13, 'HOME BANKING', 'Gestion de la plataforma de banca por internet para clientes.', 'ACTIVO'),
(14, 'COMITE DE CREDITOS (TRANSVERSAL)', 'Diseño, definicion y validacion funcional de productos y servicios crediticios.', 'ACTIVO'),
(15, 'BILLETERA DIGITAL', 'Gestion del servicio de transferencias e interconexion mediante telefonia movil.', 'ACTIVO'),
(16, 'CAPTACION DE CLIENTES', 'Evaluacion de perfil financiero y verificacion en centrales de riesgo.', 'ACTIVO'),
(17, 'EVALUACION', 'Gestion del flujo y politicas de aprobacion de creditos.', 'ACTIVO'),
(18, 'DESEMBOLSO', 'Procesamiento y ejecucion del abono de operaciones crediticias aprobadas.', 'ACTIVO'),
(19, 'COBRANZA', 'Gestion del recaudo de cuotas, seguimiento de pagos y ejecucion de moras.', 'ACTIVO');
