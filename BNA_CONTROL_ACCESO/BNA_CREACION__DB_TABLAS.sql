-- ============================================================================
-- CONTROL DE ACCESO - MODELO RBAC PARA LIDERES DE COMITE (BNA)
-- ============================================================================

-- 1. Creacion de base de datos 'control_acceso'

CREATE DATABASE control_acceso
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE control_acceso;

-- 2. Creacion de Tablas
CREATE TABLE comite (
  id_comite BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  nombre_comite VARCHAR(100) NOT NULL,
  descripcion VARCHAR(255) NULL,
  estado ENUM('ACTIVO', 'INACTIVO') NOT NULL DEFAULT 'ACTIVO',
  PRIMARY KEY (id_comite),
  UNIQUE KEY uk_comite_nombre (nombre_comite)
) ENGINE=InnoDB;

CREATE TABLE rol (
  id_rol BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  nombre_rol VARCHAR(100) NOT NULL,
  descripcion VARCHAR(255) NULL,
  PRIMARY KEY (id_rol),
  UNIQUE KEY uk_rol_nombre (nombre_rol)
) ENGINE=InnoDB;

CREATE TABLE permiso (
  id_permiso BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  nombre_permiso VARCHAR(100) CHARACTER SET ascii COLLATE ascii_bin
    NOT NULL COMMENT 'Codigo estable y unico de la accion; comparacion exacta',
  descripcion VARCHAR(255) NULL,
  PRIMARY KEY (id_permiso),
  UNIQUE KEY uk_permiso_nombre (nombre_permiso)
) ENGINE=InnoDB;

CREATE TABLE usuario (
  id_usuario BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(100) NOT NULL,
  apellido VARCHAR(100) NOT NULL,
  correo VARCHAR(254) NOT NULL,
  contrasena VARCHAR(255) CHARACTER SET ascii COLLATE ascii_bin
    NOT NULL COMMENT 'Hash generado por la API; nunca guardar la contrasena en claro',
  estado ENUM('ACTIVO', 'INACTIVO') NOT NULL DEFAULT 'ACTIVO',
  id_comite BIGINT UNSIGNED NOT NULL,
  id_rol BIGINT UNSIGNED NOT NULL,
  PRIMARY KEY (id_usuario),
  UNIQUE KEY uk_usuario_correo (correo),
  UNIQUE KEY uk_usuario_comite (id_comite),
  UNIQUE KEY uk_usuario_rol (id_rol),
  CONSTRAINT fk_usuario_comite
    FOREIGN KEY (id_comite) REFERENCES comite (id_comite)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_usuario_rol
    FOREIGN KEY (id_rol) REFERENCES rol (id_rol)
    ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE rol_permiso (
  id_rol BIGINT UNSIGNED NOT NULL,
  id_permiso BIGINT UNSIGNED NOT NULL,
  PRIMARY KEY (id_rol, id_permiso),
  KEY ix_rol_permiso_permiso (id_permiso),
  CONSTRAINT fk_rol_permiso_rol
    FOREIGN KEY (id_rol) REFERENCES rol (id_rol)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_rol_permiso_permiso
    FOREIGN KEY (id_permiso) REFERENCES permiso (id_permiso)
    ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB;

