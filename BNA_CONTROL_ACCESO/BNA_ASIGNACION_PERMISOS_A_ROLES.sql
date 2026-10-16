USE control_acceso;

SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE rol_permiso;
SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================================
-- 1. ASIGNACIÓN TOTAL (PERMISOS 1 AL 24) A ROLES TÉCNICOS Y DE GOBERNANZA
-- (LIDER_CORE, LIDER_BUS_SERVICIOS, LIDER_CALIDAD, LIDER_PMI, LIDER_SEGURIDAD, LIDER_INFRAESTRUCTURA)
-- ============================================================================
INSERT INTO rol_permiso (id_rol, id_permiso)
SELECT r.id_rol, p.id_permiso
FROM rol r
CROSS JOIN permiso p
WHERE r.id_rol IN (1, 2, 3, 4, 5, 9);

-- ============================================================================
-- 2. ASIGNACIÓN PARA COMITÉS TRANSVERSALES DE NEGOCIO
-- ============================================================================
-- LIDER_AHORROS (Cuentas, Clientes, Tarjetas y Transacciones: Permisos 1 al 11)
INSERT INTO rol_permiso (id_rol, id_permiso) VALUES
(10, 1), (10, 2), (10, 3), (10, 4), (10, 5), (10, 6), (10, 7), (10, 8), (10, 9), (10, 10), (10, 11);

-- LIDER_CREDITOS (Ciclo Crediticio Completo: Permisos 12 al 23)
INSERT INTO rol_permiso (id_rol, id_permiso) VALUES
(14, 12), (14, 13), (14, 14), (14, 15), (14, 16), (14, 17), (14, 18), (14, 19), (14, 20), (14, 21), (14, 22), (14, 23);

-- ============================================================================
-- 3. ASIGNACIÓN PARA ROLES OPERATIVOS Y CANALES ESPECÍFICOS
-- ============================================================================
INSERT INTO rol_permiso (id_rol, id_permiso) VALUES
-- LIDER_CLIENTES (KYC)
(6, 1), (6, 2), (6, 3),

-- LIDER_CUENTAS
(7, 4), (7, 5), (7, 6), (7, 8),

-- LIDER_SOLICITUD_CREDITO
(8, 14), (8, 15), (8, 16),

-- LIDER_TARJETAS
(11, 9), (11, 10), (11, 11),

-- LIDER_CAJERO_ATM
(12, 4), (12, 7), (12, 8), (12, 9),

-- LIDER_HOME_BANKING
(13, 1), (13, 4), (13, 7), (13, 8), (13, 9),

-- LIDER_BILLETERA_DIGITAL
(15, 4), (15, 7), (15, 8), (15, 9),

-- LIDER_CAPTACION_CLIENTES
(16, 1), (16, 2), (16, 12), (16, 13),

-- LIDER_EVALUACION
(17, 17), (17, 18), (17, 19),

-- LIDER_DESEMBOLSO
(18, 20), (18, 21),

-- LIDER_COBRANZA
(19, 22), (19, 23);