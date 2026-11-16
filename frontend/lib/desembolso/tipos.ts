// Contratos de DESEMBOLSO (backend/DESEMBOLSO), que devuelve lo que responde COREDB
// (backend/COREDB/CONTRATO_CREDITOS.md §4). Los montos llegan como texto decimal ("15000.00").

export type EstadoOrden =
  | "PREPARADA" | "VALIDADA" | "EN_PROCESO" | "POR_VERIFICAR" | "CONFIRMADA" | "RECHAZADA" | "REVERTIDA";

/** Perfil según el rol de COREDB: ADMINISTRADOR hace de supervisor (T6). */
export interface Sesion {
  usuario: string;
  rol: string;
  perfil: "OPERADOR" | "SUPERVISOR" | "AUDITOR" | "CONSULTA";
  puedeOperar: boolean;
  puedeConciliar: boolean;
}

/** Verificación del documento en ventanilla: `idValidacion` es la evidencia IDENTIDAD de la orden. */
export interface Verificacion {
  idValidacion: number;
  resultado: "APROBADO" | "RECHAZADO";
  motivo: string | null;
  codCliente: string | null;
  nombre: string | null;
  estadoCliente: string | null;
}

export interface Aprobacion {
  idEvaluacion: string;
  idSolicitud: string;
  codCliente: string;
  ronda: number;
  monto: string;
  moneda: string;
  plazoMeses: number;
  limiteAprobado: string;
  fechaAprobacion: string;
  vigenteHasta: string;
  idCalendario: string | null;
  ordenAbierta: { idOrden: string; codigoOrden: string; estado: EstadoOrden } | null;
}

export interface Cuenta {
  numCuenta: string;
  moneda: string;
  regimen: string;
  estadoCuenta: string;
  elegible: boolean;
  motivo: string | null;
}

export interface Orden {
  idOrden: string;
  codigoOrden: string;
  estado: EstadoOrden;
  motivoRechazo: string | null;
  importe: string;
  moneda: string;
  numCuenta: string;
  canal: string;
  idAgencia: string | null;
  idEvaluacion: string;
  idSolicitud: string;
  codCliente: string;
  usuarioPreparacion: string;
  usuarioConfirmacion: string | null;
  uuidTransaccionAbono: string | null;
  codCredito: string | null;
  fechaCreacion: string;
  fechaActualizacion: string;
}

export interface Validacion {
  idValidacion: string;
  tipo: string;
  resultado: string;
  referenciaEvidencia: string;
  detalle: string | null;
  venceEn: string | null;
  fecha: string;
}

export interface Evento {
  accion: string;
  resultado: string | null;
  actor: string;
  correlationId: string | null;
  fechaHora: string;
}

export interface Cuota {
  numeroCuota: number;
  fechaVencimiento: string;
  capital: string;
  interes: string;
  cuotaTotal: string;
  saldoCapital: string;
}

export interface Calendario {
  idCalendario: string;
  tipo: "PRELIMINAR" | "OFICIAL";
  metodo: string;
  tasa: string;
  cuotas: Cuota[];
}

export interface OrdenDetalle extends Orden {
  validaciones: Validacion[];
  eventos: Evento[];
  estadoSolicitud: string;
  plazoMeses: number;
  calendario: Calendario | null;
}

export interface Confirmada {
  idOrden: string;
  codigoOrden: string;
  estado: EstadoOrden;
  codCredito: string;
  uuidTransaccionAbono: string;
  fechaEfectiva: string;
}

export interface Conciliacion {
  fecha: string;
  moneda: string;
  ordenesConfirmadas: number;
  importeOrdenes: string;
  importeAbonado: string;
  ordenesSinAbono: number;
}
