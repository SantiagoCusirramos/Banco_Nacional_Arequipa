import { apiCuentas as api, mensajeError } from "@/lib/api";

export type EstadoCuenta = "ACTIVA" | "BLOQUEADA" | "BLOQUEADA_PREVENTIVA" | "CANCELADA";
export type Regimen = "INDIVIDUAL" | "MANCOMUNADA_INDISTINTA" | "MANCOMUNADA_CONJUNTA";
export type Moneda = "PEN" | "USD";

/** La cuenta como la devuelve CUENTAS, que la toma de COREDB. Los saldos llegan como texto decimal. */
export interface Cuenta {
  num_cuenta: string;
  cci: string;
  moneda: string;
  regimen: string;
  estado_cuenta: string;
  saldo_contable: string;
  saldo_disponible: string;
  id_agencia: string | null;
  titulares: string[];
}

/** Un movimiento de una cuenta. `naturaleza` es D (débito) o C (crédito). */
export interface Movimiento {
  uuid_transaccion: string;
  num_cuenta: string;
  tipo_operacion: string;
  naturaleza: "D" | "C" | "N";
  monto: string;
  moneda: string;
  glosa: string;
  id_canal: string | null;
  estado_transaccion: string;
  fecha_hora: string;
}

export interface OperacionRegistrada {
  uuid_transaccion: string;
  replay: boolean;
}

export interface TransferenciaRegistrada {
  uuid_debito: string;
  uuid_abono: string;
  replay: boolean;
}

export interface Apertura {
  moneda: Moneda;
  regimen: Regimen;
  id_agencia: string;
  titulares: string[];
  num_cuenta?: string;
  cci?: string;
}

// Respuesta de CUENTAS (ITIL-02): los datos van en `data`.
type Sobre<T> = { success: boolean; message?: string; data: T };

export const REGIMENES: [Regimen, ...Regimen[]] = ["INDIVIDUAL", "MANCOMUNADA_INDISTINTA", "MANCOMUNADA_CONJUNTA"];
export const MONEDAS: [Moneda, ...Moneda[]] = ["PEN", "USD"];
export const ESTADOS_CUENTA: EstadoCuenta[] = ["ACTIVA", "BLOQUEADA", "BLOQUEADA_PREVENTIVA", "CANCELADA"];

export const formatoFecha = (fecha: string) => new Date(fecha).toLocaleString("es-PE");
export const formatoMoneda = (monto: string | number, moneda?: string) =>
  `${moneda === "USD" ? "$" : "S/"} ${Number(monto).toFixed(2)}`;

export const mensajeDeError = mensajeError;

function digitos(n: number) {
  return Array.from({ length: n }, () => Math.floor(Math.random() * 10)).join("");
}

// El CORE exige el número de cuenta y el CCI; si el formulario no los trae, se generan.
export async function abrirCuenta(apertura: Apertura): Promise<Cuenta> {
  const { data } = await api.post<Sobre<Cuenta>>("/apertura", {
    num_cuenta: apertura.num_cuenta ?? digitos(14),
    cci: apertura.cci ?? digitos(20),
    moneda: apertura.moneda,
    regimen: apertura.regimen,
    id_agencia: apertura.id_agencia,
    titulares: apertura.titulares.map((id_cliente) => ({ id_cliente })),
  });
  return data.data;
}

export async function verCuenta(numCuenta: string): Promise<Cuenta> {
  const { data } = await api.get<Sobre<Cuenta>>(`/${encodeURIComponent(numCuenta)}`);
  return data.data;
}

export async function cuentasDeCliente(codCliente: string): Promise<Cuenta[]> {
  const { data } = await api.get<Sobre<Cuenta[]>>(`/consolidada/${encodeURIComponent(codCliente)}`);
  return data.data;
}

// Los montos van como texto decimal ("150.00"), igual que los devuelve el CORE.
export async function depositar(numCuenta: string, monto: string): Promise<OperacionRegistrada> {
  const { data } = await api.post<Sobre<OperacionRegistrada>>("/deposito", { num_cuenta: numCuenta, monto });
  return data.data;
}

export async function retirar(numCuenta: string, monto: string): Promise<OperacionRegistrada> {
  const { data } = await api.post<Sobre<OperacionRegistrada>>("/retiro", { num_cuenta: numCuenta, monto });
  return data.data;
}

export async function transferir(origen: string, destino: string, monto: string): Promise<TransferenciaRegistrada> {
  const { data } = await api.post<Sobre<TransferenciaRegistrada>>("/transferencia", {
    num_cuenta_origen: origen, num_cuenta_destino: destino, monto,
  });
  return data.data;
}

export async function movimientosDeCuenta(numCuenta: string): Promise<Movimiento[]> {
  const { data } = await api.get<Sobre<Movimiento[]>>(`/${encodeURIComponent(numCuenta)}/movimientos`);
  return data.data;
}

export async function verMovimiento(uuidTransaccion: string): Promise<Movimiento> {
  const { data } = await api.get<Sobre<Movimiento>>(`/movimiento/${encodeURIComponent(uuidTransaccion)}`);
  return data.data;
}
