-- ============================================================================
-- CARGA DE DATOS INICIALES: ROL
-- ============================================================================

INSERT INTO rol (id_rol, nombre_rol, descripcion) VALUES
-- Nivel 1: Superadministradores / Transversales Técnicos (Acceso Total: Permisos 1 al 24)
(1, 'LIDER_CORE', '(Acceso Total) Gestión y administración central del motor del sistema bancario core.'),
(2, 'LIDER_BUS_SERVICIOS', '(Acceso Total) Orquestación, integración y middleware de endpoints y microservicios.'),
(3, 'LIDER_CALIDAD', '(Acceso Total) Pruebas de integración E2E, auditoría de software y aseguramiento de calidad.'),
(4, 'LIDER_PMI', '(Acceso Total) Gobernanza, supervisión y seguimiento de proyectos transversales.'),
(5, 'LIDER_SEGURIDAD', '(Acceso Total) Administración de seguridad lógica, control de accesos, auditoría y prevención de fraudes.'),
(9, 'LIDER_INFRAESTRUCTURA', '(Acceso Total) Administración del entorno técnico, servidores, redes y continuidad operativa.'),

-- Nivel 2: Comités Transversales de Negocio (Acceso Ampliado de Dominio)
(10, 'LIDER_AHORROS', '(Dominio Pasivo) Supervisión transversal de clientes, cuentas, tarjetas y transacciones.'),
(14, 'LIDER_CREDITOS', '(Dominio Activo) Supervisión transversal de captación, solicitudes, evaluación, desembolso y cobranzas.'),

-- Nivel 3: Roles Operativos y Canales Específicos
(6, 'LIDER_CLIENTES', '(CRUD Clientes) Registro, validación biométrica, emisión OTP y actualización KYC.'),
(7, 'LIDER_CUENTAS', '(CRUD Cuentas) Apertura, vinculación de clientes, topes diarios y estados de cuenta.'),
(8, 'LIDER_SOLICITUD_CREDITO', '(CRUD Solicitudes) Registro de solicitudes de crédito, fiadores, garantías y calendarios.'),
(11, 'LIDER_TARJETAS', '(CRUD Tarjetas) Emisión, bloqueo/anulación, vinculación a cuentas y tokens de pago.'),
(12, 'LIDER_CAJERO_ATM', '(Canal ATM) Lectura de cuentas/tarjetas, saldo y ejecución de depósitos y retiros.'),
(13, 'LIDER_HOME_BANKING', '(Canal Digital) Consulta de productos, movimientos y transferencias por banca web/móvil.'),
(15, 'LIDER_BILLETERA_DIGITAL', '(Canal Billetera) Consultas de saldo, pagos rápidos y transferencias digitales.'),
(16, 'LIDER_CAPTACION_CLIENTES', '(Captación) Registro de prospectos (leads), consentimientos y consultas a burós de riesgo.'),
(17, 'LIDER_EVALUACION', '(Evaluación) Ejecución de motor de reglas de riesgo y dictamen crediticio.'),
(18, 'LIDER_DESEMBOLSO', '(Desembolso) Validaciones, ejecuciones de entrega de efectivo y reversiones.'),
(19, 'LIDER_COBRANZA', '(Cobranza) Seguimiento de cuotas, cálculo de mora, gestión de cobros y auditoría.');