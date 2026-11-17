import { apiCaptacion as api, mensajeError } from "@/lib/api";

/** Respuesta de CAPTACION (ITIL-02): los datos van en `data`. */
type Sobre<T> = { success: boolean; message?: string; data: T };

export interface Solicitante {
  id_solicitante: string;
  tipo_documento: string;
  numero_documento: string;
  nombres: string;
  apellido_paterno: string;
  apellido_materno: string | null;
  celular: string;
  correo: string;
  cod_cliente: string | null;
  creado_en: string;
}

export interface Caso {
  id_caso: string;
  id_solicitante: string;
  canal: string;
  id_agencia: string | null;
  producto_interes: string | null;
  estado: string;
  observacion: string | null;
  motivo_cierre: string | null;
  cod_cliente: string | null;
  cliente_nuevo: boolean | null;
  id_verificacion_captacion: string | null;
  fecha_verificacion: string | null;
  vigente_hasta: string | null;
  creado_por: string;
  creado_en: string;
  cerrado_en: string | null;
}

export type CasoEnBandeja = Caso & { solicitante: Solicitante };

export interface Consentimiento { tipo: string; aceptado: boolean; medio: string; version: string | null; registrado_por: string; fecha: string }
export interface Validacion { tipo: string; resultado: string; proveedor: string; detalle: string | null; registrado_por: string; fecha: string }
export interface Consulta { central: string; calificacion: string; deuda_total: string; entidades: number; dias_mora: number; fuente: string; fecha: string }
export interface Perfil { puntaje: number; calificacion: string; observacion: string | null; fecha: string }

export type Expediente = Caso & {
  solicitante: Solicitante;
  consentimientos: Consentimiento[];
  validaciones: Validacion[];
  consultas: Consulta[];
  perfil: Perfil | null;
  faltantes: string[];
  listo_para_habilitar: boolean;
};

export interface OtpEnviado { canal: string; destino_enmascarado: string; expira_en: string; codigo_simulado: string | null }
export interface OtpResultado { verificado: boolean; estado_codigo: string; intentos_restantes: number }

/** Lo que Solicitud de Crédito recibe de CAPTACION (contrato CR-INT-01). */
export interface Referencia {
  id_cliente: string;
  cod_tipo_documento: string;
  numero_documento: string;
  nombres: string;
  apellido_paterno: string;
  apellido_materno: string;
  estado_cliente: string;
  id_caso: string;
  id_verificacion: string;
  fecha_verificacion: string;
  vigente_hasta: string;
  estado_habilitante: string;
  version_contrato: string;
  simulado: boolean;
}

export interface NuevoSolicitante {
  tipo_documento: string;
  numero_documento: string;
  nombres: string;
  apellido_paterno: string;
  apellido_materno: string;
  celular: string;
  correo: string;
}

export const TIPOS_DOCUMENTO = ["DNI", "CE", "PTP", "PASAPORTE"] as const;
export const CANALES = ["AGENCIA", "WEB", "MOVIL", "AGENTE", "CAMPANA"] as const;
export const CENTRALES = ["SBS", "INFOCORP", "SENTINEL", "EQUIFAX"] as const;
export const CONSENTIMIENTOS = [
  { tipo: "TRATAMIENTO_DATOS", etiqueta: "Tratamiento de datos personales", requerido: true },
  { tipo: "CONSULTA_BUROS", etiqueta: "Consulta a centrales de riesgo", requerido: true },
  { tipo: "TERMINOS", etiqueta: "Términos y condiciones", requerido: true },
  { tipo: "BIOMETRIA", etiqueta: "Uso de datos biométricos", requerido: false },
] as const;
export const VALIDACIONES = [
  { tipo: "RENIEC", etiqueta: "RENIEC", requerido: true },
  { tipo: "LISTAS_NEGRAS", etiqueta: "Listas restrictivas", requerido: true },
  { tipo: "PEP", etiqueta: "Persona expuesta políticamente", requerido: false },
  { tipo: "BIOMETRIA", etiqueta: "Biometría", requerido: false },
] as const;

export const mensajeDeError = mensajeError;

/** Lo que falta para habilitar, si el error lo trae (ERR-CAP-CASO-NO-LISTO). */
export function faltantesDelError(err: unknown): string[] {
  const datos = (err as { response?: { data?: { details?: { faltantes?: unknown } } } })?.response?.data;
  const faltantes = datos?.details?.faltantes;
  return Array.isArray(faltantes) ? faltantes.map(String) : [];
}

export async function bandeja(estado?: string): Promise<CasoEnBandeja[]> {
  const { data } = await api.get<Sobre<CasoEnBandeja[]>>("/casos", { params: estado ? { estado, limite: 100 } : { limite: 100 } });
  return data.data;
}

export async function expediente(idCaso: string): Promise<Expediente> {
  const { data } = await api.get<Sobre<Expediente>>(`/casos/${encodeURIComponent(idCaso)}`);
  return data.data;
}

export async function registrarSolicitante(datos: NuevoSolicitante) {
  const { data } = await api.post<Sobre<{ solicitante: Solicitante; duplicado: boolean }>>("/solicitantes", {
    ...datos,
    numero_documento: datos.numero_documento.trim().toUpperCase(),
    apellido_materno: datos.apellido_materno.trim() || null,
  });
  return data.data;
}

export async function abrirCaso(idSolicitante: string, canal: string, idAgencia: string, producto: string): Promise<Caso> {
  const { data } = await api.post<Sobre<Caso>>("/casos", {
    id_solicitante: idSolicitante, canal, id_agencia: idAgencia || null, producto_interes: producto || null,
  });
  return data.data;
}

const enCaso = (idCaso: string, ruta: string) => `/casos/${encodeURIComponent(idCaso)}${ruta}`;

export async function registrarConsentimientos(idCaso: string, marcas: Record<string, boolean>, medio: string) {
  await api.post(enCaso(idCaso, "/consentimientos"), {
    consentimientos: CONSENTIMIENTOS.map((c) => ({ tipo: c.tipo, aceptado: !!marcas[c.tipo], medio })),
  });
}

export async function enviarOtp(idCaso: string, canal: string): Promise<OtpEnviado> {
  const { data } = await api.post<Sobre<OtpEnviado>>(enCaso(idCaso, "/otp"), { canal });
  return data.data;
}

export async function verificarOtp(idCaso: string, canal: string, codigo: string): Promise<OtpResultado> {
  const { data } = await api.post<Sobre<OtpResultado>>(enCaso(idCaso, "/otp/verificar"), { canal, codigo });
  return data.data;
}

export async function validar(idCaso: string, tipos: string[]) {
  await api.post(enCaso(idCaso, "/validaciones"), { tipos });
}

export async function validacionManual(idCaso: string, tipo: string, resultado: string, detalle: string) {
  await api.post(enCaso(idCaso, "/validaciones/manual"), { tipo, resultado, detalle });
}

export async function consultarCentral(idCaso: string, central: string) {
  await api.post(enCaso(idCaso, "/consultas-riesgo"), { central });
}

export async function calcularPerfil(idCaso: string) {
  await api.post(enCaso(idCaso, "/perfil"));
}

export async function cambiarEstado(idCaso: string, accion: string, motivo: string) {
  await api.post(enCaso(idCaso, "/estado"), { accion, motivo });
}

export async function habilitar(idCaso: string): Promise<Caso> {
  const { data } = await api.post<Sobre<Caso>>(enCaso(idCaso, "/habilitar"));
  return data.data;
}

export async function referencia(idCaso: string): Promise<Referencia> {
  const { data } = await api.get<Sobre<Referencia>>(enCaso(idCaso, "/referencia"));
  return data.data;
}
