-- =====================================================================
-- Chaski / Billetera Digital BNA — esquema PostgreSQL
-- Tablas 1 a 10: fieles al diagrama entidad-relación del módulo.
-- Tablas de extensión al final (tienda, promos, cupones, seguridad).
-- El script es idempotente: se puede ejecutar varias veces.
-- =====================================================================

-- ---------- Tipos enumerados del diagrama ----------
DO $$ BEGIN CREATE TYPE estado_general AS ENUM ('activo','inactivo','bloqueado'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE estado_transferencia AS ENUM ('pendiente','completada','fallida','revertida'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE estado_solicitud AS ENUM ('pendiente','aceptada','rechazada','cancelada','expirada'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE tipo_qr AS ENUM ('estatico','dinamico'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE estado_pago AS ENUM ('pendiente','completado','fallido'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE tipo_movimiento AS ENUM ('transferencia_enviada','transferencia_recibida','pago_qr','cobro_qr','recarga','compra_tienda','venta_tienda','recarga_celular','pago_servicio'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE estado_envio AS ENUM ('pendiente','enviado','leido','fallido'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ---------- 1. cliente ----------
CREATE TABLE IF NOT EXISTS cliente (
  id_cliente       bigserial PRIMARY KEY,
  tipo_documento   varchar(20)  NOT NULL,
  numero_documento varchar(20)  NOT NULL,
  nombres          varchar(100) NOT NULL,
  apellidos        varchar(100) NOT NULL,
  celular          varchar(20)  NOT NULL UNIQUE,
  email            varchar(150),
  estado           estado_general NOT NULL DEFAULT 'activo',
  UNIQUE (tipo_documento, numero_documento)
);

-- ---------- 2. cuenta ----------
CREATE TABLE IF NOT EXISTS cuenta (
  id_cuenta             bigserial PRIMARY KEY,
  id_cliente            bigint NOT NULL REFERENCES cliente(id_cliente),
  numero_cuenta_virtual varchar(30) NOT NULL UNIQUE,
  saldo_actual          numeric(14,2) NOT NULL DEFAULT 0 CHECK (saldo_actual >= 0),
  moneda                char(3) NOT NULL DEFAULT 'PEN',
  estado                estado_general NOT NULL DEFAULT 'activo',
  fecha_apertura        timestamptz NOT NULL DEFAULT now()
);

-- ---------- 3. comercio ----------
CREATE TABLE IF NOT EXISTS comercio (
  id_comercio      bigserial PRIMARY KEY,
  id_cuenta        bigint NOT NULL REFERENCES cuenta(id_cuenta),
  razon_social     varchar(150) NOT NULL,
  ruc              varchar(20) NOT NULL UNIQUE,
  estado           estado_general NOT NULL DEFAULT 'activo',
  fecha_afiliacion timestamptz NOT NULL DEFAULT now()
);

-- ---------- 4. transferencia ----------
CREATE TABLE IF NOT EXISTS transferencia (
  id_transferencia  bigserial PRIMARY KEY,
  id_cuenta_origen  bigint NOT NULL REFERENCES cuenta(id_cuenta),
  id_cuenta_destino bigint NOT NULL REFERENCES cuenta(id_cuenta),
  monto             numeric(14,2) NOT NULL CHECK (monto > 0),
  estado            estado_transferencia NOT NULL,
  fecha_hora        timestamptz NOT NULL DEFAULT now(),
  referencia        varchar(100),
  CHECK (id_cuenta_origen <> id_cuenta_destino)
);

-- ---------- 5. solicitud_cobro ----------
CREATE TABLE IF NOT EXISTS solicitud_cobro (
  id_solicitud           bigserial PRIMARY KEY,
  id_cliente_solicitante bigint NOT NULL REFERENCES cliente(id_cliente),
  id_cliente_solicitado  bigint NOT NULL REFERENCES cliente(id_cliente),
  monto                  numeric(14,2) NOT NULL CHECK (monto > 0),
  concepto               varchar(150),
  estado                 estado_solicitud NOT NULL DEFAULT 'pendiente',
  fecha_solicitud        timestamptz NOT NULL DEFAULT now(),
  fecha_respuesta        timestamptz,
  id_transferencia       bigint REFERENCES transferencia(id_transferencia)
);

-- ---------- 6. codigo_qr ----------
CREATE TABLE IF NOT EXISTS codigo_qr (
  id_qr            bigserial PRIMARY KEY,
  id_cuenta        bigint REFERENCES cuenta(id_cuenta),
  id_comercio      bigint REFERENCES comercio(id_comercio),
  tipo             tipo_qr NOT NULL,
  monto            numeric(14,2),
  estado           estado_general NOT NULL DEFAULT 'activo',
  fecha_generacion timestamptz NOT NULL DEFAULT now(),
  fecha_expiracion timestamptz
);

-- ---------- 7. pago_qr ----------
CREATE TABLE IF NOT EXISTS pago_qr (
  id_pago          bigserial PRIMARY KEY,
  id_qr            bigint NOT NULL REFERENCES codigo_qr(id_qr),
  id_cuenta_origen bigint NOT NULL REFERENCES cuenta(id_cuenta),
  monto            numeric(14,2) NOT NULL CHECK (monto > 0),
  estado           estado_pago NOT NULL,
  fecha_hora       timestamptz NOT NULL DEFAULT now()
);

-- ---------- 8. notificacion ----------
CREATE TABLE IF NOT EXISTS notificacion (
  id_notificacion bigserial PRIMARY KEY,
  id_cliente      bigint NOT NULL REFERENCES cliente(id_cliente),
  tipo            varchar(50) NOT NULL,
  mensaje         varchar(300) NOT NULL,
  estado_envio    estado_envio NOT NULL DEFAULT 'pendiente',
  fecha_hora      timestamptz NOT NULL DEFAULT now()
);

-- ===== Extensión: tienda, promos, ofertas, recargas y servicios (RF-BD-006/007/008) =====
CREATE TABLE IF NOT EXISTS producto (
  id_producto bigserial PRIMARY KEY,
  id_comercio bigint NOT NULL REFERENCES comercio(id_comercio),
  nombre      varchar(150) NOT NULL,
  descripcion varchar(300),
  categoria   varchar(50),
  emoji       varchar(8),
  precio      numeric(14,2) NOT NULL CHECK (precio > 0),
  stock       int NOT NULL DEFAULT 0 CHECK (stock >= 0),
  estado      estado_general NOT NULL DEFAULT 'activo'
);
CREATE TABLE IF NOT EXISTS promocion (
  id_promocion   bigserial PRIMARY KEY,
  id_comercio    bigint NOT NULL REFERENCES comercio(id_comercio),
  titulo         varchar(150) NOT NULL,
  descripcion    varchar(300),
  porcentaje     numeric(5,2) NOT NULL CHECK (porcentaje > 0 AND porcentaje <= 90),
  tope_descuento numeric(14,2),
  fecha_inicio   timestamptz NOT NULL,
  fecha_fin      timestamptz NOT NULL,
  estado         estado_general NOT NULL DEFAULT 'activo'
);
CREATE TABLE IF NOT EXISTS cupon (
  id_cupon         bigserial PRIMARY KEY,
  id_promocion     bigint NOT NULL REFERENCES promocion(id_promocion),
  id_cliente       bigint NOT NULL REFERENCES cliente(id_cliente),
  codigo           varchar(20) NOT NULL UNIQUE,
  estado           varchar(20) NOT NULL DEFAULT 'vigente' CHECK (estado IN ('vigente','canjeado','vencido')),
  fecha_generacion timestamptz NOT NULL DEFAULT now(),
  UNIQUE (id_promocion, id_cliente)
);
CREATE TABLE IF NOT EXISTS oferta (
  id_oferta     bigserial PRIMARY KEY,
  id_producto   bigint NOT NULL REFERENCES producto(id_producto),
  precio_oferta numeric(14,2) NOT NULL CHECK (precio_oferta > 0),
  stock_oferta  int NOT NULL DEFAULT 0 CHECK (stock_oferta >= 0),
  fecha_fin     timestamptz NOT NULL,
  estado        estado_general NOT NULL DEFAULT 'activo'
);
CREATE TABLE IF NOT EXISTS orden (
  id_orden      bigserial PRIMARY KEY,
  id_cliente    bigint NOT NULL REFERENCES cliente(id_cliente),
  id_comercio   bigint NOT NULL REFERENCES comercio(id_comercio),
  subtotal      numeric(14,2) NOT NULL,
  descuento     numeric(14,2) NOT NULL DEFAULT 0,
  total         numeric(14,2) NOT NULL CHECK (total > 0),
  estado        varchar(20) NOT NULL DEFAULT 'pagada' CHECK (estado IN ('pagada','entregada','cancelada')),
  codigo_recojo varchar(8) NOT NULL,
  fecha_hora    timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS orden_item (
  id_item         bigserial PRIMARY KEY,
  id_orden        bigint NOT NULL REFERENCES orden(id_orden),
  id_producto     bigint NOT NULL REFERENCES producto(id_producto),
  nombre          varchar(150) NOT NULL,
  cantidad        int NOT NULL CHECK (cantidad > 0),
  precio_unitario numeric(14,2) NOT NULL
);
CREATE TABLE IF NOT EXISTS servicio_pago (
  id_pago_servicio bigserial PRIMARY KEY,
  id_cliente       bigint NOT NULL REFERENCES cliente(id_cliente),
  tipo             varchar(20) NOT NULL CHECK (tipo IN ('recarga','servicio')),
  proveedor        varchar(60) NOT NULL,
  referencia       varchar(30) NOT NULL,
  periodo          char(7),
  monto            numeric(14,2) NOT NULL CHECK (monto > 0),
  estado           estado_pago NOT NULL,
  fecha_hora       timestamptz NOT NULL DEFAULT now()
);

-- ---------- 9. movimiento (diagrama + 2 FK opcionales de la extensión) ----------
CREATE TABLE IF NOT EXISTS movimiento (
  id_movimiento    bigserial PRIMARY KEY,
  id_cuenta        bigint NOT NULL REFERENCES cuenta(id_cuenta),
  tipo_movimiento  tipo_movimiento NOT NULL,
  id_transferencia bigint REFERENCES transferencia(id_transferencia),
  id_pago          bigint REFERENCES pago_qr(id_pago),
  id_solicitud     bigint REFERENCES solicitud_cobro(id_solicitud),
  id_orden         bigint REFERENCES orden(id_orden),
  id_pago_servicio bigint REFERENCES servicio_pago(id_pago_servicio),
  monto            numeric(14,2) NOT NULL,
  saldo_resultante numeric(14,2) NOT NULL,
  fecha_hora       timestamptz NOT NULL DEFAULT now(),
  descripcion      varchar(200)
);

-- ===== Extensión de seguridad (no está en el diagrama) =====
-- PIN hasheado, separado de los datos del cliente
CREATE TABLE IF NOT EXISTS credencial (
  id_cliente bigint PRIMARY KEY REFERENCES cliente(id_cliente),
  pin_hash   text NOT NULL
);
-- Idempotencia por uuidTransaccion (RN-BUS-002)
CREATE TABLE IF NOT EXISTS operacion_idempotente (
  uuid_transaccion uuid PRIMARY KEY,
  id_cliente       bigint NOT NULL REFERENCES cliente(id_cliente),
  operacion        varchar(40) NOT NULL,
  respuesta        jsonb NOT NULL,
  fecha_hora       timestamptz NOT NULL DEFAULT now()
);
-- Log de auditoría de operaciones exitosas y rechazadas (INT-13)
CREATE TABLE IF NOT EXISTS auditoria (
  id_auditoria     bigserial PRIMARY KEY,
  id_cliente       bigint REFERENCES cliente(id_cliente),
  operacion        varchar(40) NOT NULL,
  resultado        varchar(20) NOT NULL CHECK (resultado IN ('exitosa','rechazada')),
  detalle          varchar(300),
  uuid_transaccion uuid,
  fecha_hora       timestamptz NOT NULL DEFAULT now()
);

-- ---------- índices ----------
CREATE INDEX IF NOT EXISTS ix_mov_cuenta   ON movimiento (id_cuenta, fecha_hora DESC);
CREATE INDEX IF NOT EXISTS ix_tr_origen    ON transferencia (id_cuenta_origen);
CREATE INDEX IF NOT EXISTS ix_tr_destino   ON transferencia (id_cuenta_destino);
CREATE INDEX IF NOT EXISTS ix_notif        ON notificacion (id_cliente, fecha_hora DESC);
CREATE INDEX IF NOT EXISTS ix_sol_solicit  ON solicitud_cobro (id_cliente_solicitado, estado);
CREATE INDEX IF NOT EXISTS ix_prod_comercio ON producto (id_comercio);
CREATE INDEX IF NOT EXISTS ix_orden_cliente ON orden (id_cliente, fecha_hora DESC);
CREATE INDEX IF NOT EXISTS ix_audit_cliente ON auditoria (id_cliente, fecha_hora DESC);
