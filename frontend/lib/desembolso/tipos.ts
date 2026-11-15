export type EstadoOrden =
  | "PREPARADA" | "VALIDADA" | "EN_PROCESO" | "POR_VERIFICAR" | "CONFIRMADA" | "RECHAZADA" | "REVERTIDA";

export interface Sesion {
  usuario: string;
  nombre: string;
  rol: string;
  permisos: string[];
  agencia_id: string | null;
  agencia_nombre: string | null;
  reversion_habilitada: boolean;
}

export interface Aprobacion {
  aprobacion_id: string;
  version: number;
  credito_id: string;
  cliente_id: string;
  cliente_nombre: string;
  cliente_documento: string | null;
  producto: string;
  importe: string;
  moneda: string;
  plazo_meses: number | null;
  tasa_tea: string | null;
  estado: string;
  vigente_hasta: string | null;
}

export interface CreditoHabilitado extends Aprobacion {
  habilitada: boolean;
  motivo: string | null;
  orden_existente: { id: string; codigo_orden: string; estado: EstadoOrden } | null;
}

export interface Validacion {
  id: string;
  tipo: string;
  fase: string;
  proveedor: string;
  referencia_evidencia: string;
  resultado: string;
  detalle: string | null;
  vence_en: string | null;
  creado_en: string | null;
}

export interface EventoEntrega {
  id: string;
  tipo: string;
  estado: string;
  intentos: number;
  siguiente_intento: string | null;
  confirmacion_id: string | null;
  ultimo_error: string | null;
  creado_en: string | null;
}

export interface Reversion {
  id: string;
  orden_id: string;
  codigo_orden?: string | null;
  motivo: string;
  origen: string;
  estado: string;
  solicitante_id: string;
  autorizador_id: string | null;
  motivo_rechazo: string | null;
  reversion_financiera_id: string | null;
  creado_en: string | null;
}

export interface OrdenResumen {
  id: string;
  codigo_orden: string;
  estado: EstadoOrden;
  entrega_estado: string;
  motivo_rechazo: string | null;
  aprobacion_id: string;
  aprobacion_version: number;
  credito_id: string;
  cliente_id: string;
  cuenta_id: string | null;
  importe: string;
  moneda: string;
  operacion_financiera_id: string | null;
  fecha_efectiva: string | null;
  idempotency_key: string;
  usuario_preparacion: string;
  usuario_confirmacion: string | null;
  correlation_id: string;
  version: number;
  creado_en: string | null;
  actualizado_en: string | null;
}

/** Una cuota del calendario de Solicitud (RN-SOL-006), como llegó con la aprobación. */
export interface Cuota {
  numeroCuota: number;
  fechaVencimiento: string;
  amortizacion: string | null;
  interes: string | null;
  cuotaTotal: string;
  saldoFinal: string | null;
}

export interface OrdenDetalle extends OrdenResumen {
  cuenta_enmascarada: string | null;
  identidad: { resultado: string; vence_en: string | null; detalle: string | null } | null;
  aprobacion: Aprobacion | null;
  solicitud_id: string | null;
  calendario: Cuota[];
  validaciones: Validacion[];
  eventos: EventoEntrega[];
  reversiones: Reversion[];
  acciones: string[];
}

export interface CuentaElegible {
  cuenta_id: string;
  numero_enmascarado: string;
  producto: string;
  moneda: string;
  estado: string;
  titularidad: string;
  elegible: boolean;
  motivo: string | null;
}
