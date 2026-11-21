import { readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { waitFor } from "@testing-library/react";

// Transferencias desde el Home Banking (transferencias.html). Antes, «Continuar con Token Matriz»
// transfería en el acto, sin resumen ni código; el comprobante mostraba «S/ 0.00» si faltaba el
// saldo (`|| 0`) y la fecha del navegador. Ahora, como el pago de cuota (#138): resumen con el
// titular de destino enmascarado y «Cancelar», código SIMULADO que bloquea el envío, una llave por
// intento (la misma en cada reintento), botón deshabilitado y comprobante solo con lo que devuelve
// CUENTAS (o un error con el número de operación si falta algo).
const HB = resolve(process.cwd(), "public/homebanking"); // vitest corre en frontend/
const leer = (f: string) => readFileSync(join(HB, f), "utf8");

const CLIENTE = "CLI000000003";
const ORIGEN = "18250122240575";
const PROPIA = "18250122240576";
const TERCERO = "62307291722448";
const TITULAR_PROPIA = "Lu*** Ra*** Ti***";
const TITULAR_TERCERO = "Te*** Ma*** Qu***";

type Respuesta = { status: number; body: unknown } | "red";
type Cuerpo = { num_cuenta_origen: string; num_cuenta_destino: string; monto: string; glosa?: string };
let llamadas: { url: string; init: RequestInit }[];
let saldos: Record<string, number>;
// Lo que haría COREDB: la misma llave devuelve la misma transferencia sin otro débito.
let operaciones: Map<string, { n: number; cuerpo: Cuerpo }>;
let respuestaTransferencia: (cuerpo: Cuerpo, llave: string) => Respuesta;

const sobre = (data: unknown, status = 200) => ({ status, body: { success: true, status_code: status, data } });
const errorCuentas = (status: number, error_code: string, message: string) =>
  ({ status, body: { success: false, status_code: status, error_code, message, details: {} } });

function transferirComoElServidor(cuerpo: Cuerpo, llave: string, extra: Record<string, unknown> = {}): Respuesta {
  const previa = operaciones.get(llave);
  if (!previa) {
    operaciones.set(llave, { n: operaciones.size + 1, cuerpo });
    saldos[cuerpo.num_cuenta_origen] -= Number(cuerpo.monto);
    saldos[cuerpo.num_cuenta_destino] = (saldos[cuerpo.num_cuenta_destino] ?? 0) + Number(cuerpo.monto);
  }
  const { n, cuerpo: original } = operaciones.get(llave)!;
  return sobre({
    uuid_debito: `deb-${n}`, uuid_abono: `abo-${n}`, replay: !!previa,
    num_cuenta_origen: original.num_cuenta_origen, num_cuenta_destino: original.num_cuenta_destino,
    monto: original.monto, moneda: "PEN", fecha_hora: "2026-11-21T15:04:05Z", estado: "APROBADO",
    saldo_disponible_origen: saldos[original.num_cuenta_origen].toFixed(2),
    titular_destino: original.num_cuenta_destino === TERCERO ? TITULAR_TERCERO : TITULAR_PROPIA,
    ...extra,
  }, 201);
}

const cuentaCuentas = (num: string, moneda = "PEN") => ({
  num_cuenta: num, cci: "0".repeat(20), moneda, regimen: "INDIVIDUAL", estado_cuenta: "ACTIVA",
  saldo_contable: saldos[num].toFixed(2), saldo_disponible: saldos[num].toFixed(2), titulares: [CLIENTE],
});

function cargarPagina() {
  const html = leer("transferencias.html");
  document.body.innerHTML = html.slice(html.indexOf("<body"), html.lastIndexOf("</body>"))
    .replace(/^<body[^>]*>/, "").replace(/<script[\s\S]*?<\/script>/g, "");
  const scripts = [...html.matchAll(/<script src="([^"]+)"/g)].map((m) => m[1]);
  (0, eval)(scripts.map(leer).join("\n;\n"));
}

beforeEach(() => {
  llamadas = [];
  saldos = { [ORIGEN]: 1200, [PROPIA]: 50, [TERCERO]: 300 };
  operaciones = new Map();
  respuestaTransferencia = (cuerpo, llave) => transferirComoElServidor(cuerpo, llave);
  sessionStorage.setItem("hb_sesion_bna", JSON.stringify({ codCliente: CLIENTE, nombres: "Operador", dni: "operador" }));
  localStorage.setItem("bna_access_token", "token-de-coredb");
  vi.stubGlobal("fetch", vi.fn(async (url: string, init: RequestInit = {}) => {
    llamadas.push({ url, init });
    const h = (init.headers || {}) as Record<string, string>;
    let r: Respuesta;
    if (url === "/api/cuenta/transferencia") {
      r = respuestaTransferencia(JSON.parse(init.body as string), h["X-Idempotency-Key"]);
    } else if (url === `/api/cuenta/consolidada/${CLIENTE}`) {
      r = sobre([cuentaCuentas(ORIGEN), cuentaCuentas(PROPIA)]);
    } else if (url === `/api/cuenta/${PROPIA}/destino`) {
      r = sobre({ num_cuenta: PROPIA, moneda: "PEN", estado_cuenta: "ACTIVA", titular: TITULAR_PROPIA });
    } else if (url === `/api/cuenta/${TERCERO}/destino`) {
      r = sobre({ num_cuenta: TERCERO, moneda: "PEN", estado_cuenta: "ACTIVA", titular: TITULAR_TERCERO });
    } else if (url.endsWith("/destino")) {
      r = errorCuentas(404, "ERR-CTA-NO-ENCONTRADA", "La cuenta 999 no existe.");
    } else r = { status: 404, body: { detail: "no simulado" } };
    if (r === "red") throw new TypeError("Failed to fetch");
    return new Response(JSON.stringify(r.body), { status: r.status, headers: { "Content-Type": "application/json" } });
  }));
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  sessionStorage.clear();
  localStorage.clear();
  document.body.innerHTML = "";
});

const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const envios = () => llamadas.filter((l) => l.url === "/api/cuenta/transferencia");
const llaves = () => envios().map((l) => (l.init.headers as Record<string, string>)["X-Idempotency-Key"]);
const dialogo = () => document.querySelector<HTMLElement>("[role=dialog]");
const mensaje = () => $("msgTrans");

function escribir(id: string, valor: string) {
  const campo = $<HTMLInputElement>(id);
  campo.value = valor;
  campo.dispatchEvent(new Event("input", { bubbles: true }));
}

async function llenar({ monto = "150.00", tercero }: { monto?: string; tercero?: string } = {}) {
  await waitFor(() => expect($<HTMLSelectElement>("selDestinoPropia").value).toBe(PROPIA));
  if (tercero) {
    document.querySelector<HTMLElement>('.tab[data-tipo="TERCERO"]')!.click();
    escribir("ctaTercero", tercero);
  }
  escribir("monto", monto);
}

async function abrirConfirmacion(datos?: { monto?: string; tercero?: string }) {
  await llenar(datos);
  $("btnTransferir").click();
  await waitFor(() => expect(dialogo()).not.toBeNull());
}

function escribirCodigo(codigo?: string) {
  const correcto = $("codigoSimulado").textContent!.trim();
  escribir("codigoIngresado", codigo ?? correcto);
  return correcto;
}

async function confirmar() {
  escribirCodigo();
  $("btnConfirmarPago").click();
  await waitFor(() => expect(dialogo()).toBeNull());
}

async function transferir(datos?: { monto?: string; tercero?: string }) {
  await abrirConfirmacion(datos);
  await confirmar();
}

describe("Home Banking: transferir", () => {
  it("HB-19 «Revisar y transferir» solo abre un resumen (monto, origen, destino, titular enmascarado); nada se envía antes", async () => {
    cargarPagina();
    expect($("btnTransferir").textContent).not.toMatch(/Token Matriz/i);
    await abrirConfirmacion({ tercero: TERCERO });
    const texto = dialogo()!.textContent!;
    expect(texto).toContain("S/ 150.00");
    expect(texto).toContain(ORIGEN);
    expect(texto).toContain(TERCERO);
    expect(texto).toContain(TITULAR_TERCERO);
    expect(texto).toMatch(/no se mueve dinero/i);
    expect(envios()).toEqual([]);
  });

  it("HB-20 Cancelar (botón o Escape) no transfiere y lo dice", async () => {
    cargarPagina();
    await abrirConfirmacion();
    $("btnCancelarPago").click();
    await waitFor(() => expect(dialogo()).toBeNull());
    expect(mensaje().textContent).toMatch(/no se movió dinero/i);
    expect($<HTMLButtonElement>("btnTransferir").disabled).toBe(false);

    $("btnTransferir").click();
    await waitFor(() => expect(dialogo()).not.toBeNull());
    dialogo()!.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await waitFor(() => expect(dialogo()).toBeNull());
    expect(envios()).toEqual([]);
    expect(operaciones.size).toBe(0);
  });

  it("HB-21 El código está rotulado como SIMULACIÓN; uno incorrecto bloquea el envío y tres lo cancelan", async () => {
    cargarPagina();
    await abrirConfirmacion();
    expect(dialogo()!.textContent).toMatch(/simulaci[oó]n/i);
    expect(dialogo()!.textContent).toMatch(/no es un segundo factor real/i);
    const correcto = escribirCodigo();
    expect(correcto).toMatch(/^\d{6}$/);
    const errado = correcto.replace(/^./, (d) => String((Number(d) + 1) % 10));
    escribirCodigo("");
    $("btnConfirmarPago").click();
    expect(envios()).toEqual([]);
    for (let i = 0; i < 2; i++) {
      escribirCodigo(errado);
      $("btnConfirmarPago").click();
      await waitFor(() => expect($("confirmacionError").textContent).toMatch(/incorrecto/i));
      expect(dialogo()).not.toBeNull();
    }
    escribirCodigo(errado);
    $("btnConfirmarPago").click();
    await waitFor(() => expect(dialogo()).toBeNull());
    expect(mensaje().textContent).toMatch(/no se movió dinero/i);
    expect(envios()).toEqual([]);
  });

  it("HB-22 Doble clic: un solo diálogo, un solo envío y el botón queda deshabilitado mientras se procesa", async () => {
    let soltar!: () => void;
    const pendiente = new Promise<void>((r) => { soltar = r; });
    cargarPagina();
    await llenar();
    $("btnTransferir").click();
    $("btnTransferir").click();
    await waitFor(() => expect(dialogo()).not.toBeNull());
    expect(document.querySelectorAll("[role=dialog]")).toHaveLength(1);

    const fetchReal = globalThis.fetch as unknown as (u: string, i?: RequestInit) => Promise<Response>;
    vi.stubGlobal("fetch", vi.fn(async (url: string, init: RequestInit = {}) => {
      if (url === "/api/cuenta/transferencia") await pendiente;
      return fetchReal(url, init);
    }));
    escribirCodigo();
    const boton = $<HTMLButtonElement>("btnConfirmarPago");
    boton.click();
    boton.click();
    await waitFor(() => expect(dialogo()).toBeNull());
    expect($<HTMLButtonElement>("btnTransferir").disabled).toBe(true);
    $("btnTransferir").click();
    expect(dialogo()).toBeNull();
    soltar();
    await waitFor(() => expect(mensaje().className).toContain("ok"));
    expect(envios()).toHaveLength(1);
    expect(operaciones.size).toBe(1);
    expect($<HTMLButtonElement>("btnTransferir").disabled).toBe(false);
  });

  it("HB-23 Si la respuesta se pierde, el reintento lleva la misma llave (un solo débito); cambiar un dato o una nueva, otra", async () => {
    respuestaTransferencia = (cuerpo, llave) => { transferirComoElServidor(cuerpo, llave); return "red"; };
    cargarPagina();
    await transferir();
    await waitFor(() => expect(mensaje().className).toContain("warn"));
    expect(mensaje().textContent).toMatch(/no se transferirá dos veces/i);
    expect($("resultado").hidden).toBe(true);

    respuestaTransferencia = (cuerpo, llave) => transferirComoElServidor(cuerpo, llave);
    $("btnTransferir").click();
    await waitFor(() => expect(dialogo()).not.toBeNull());
    await confirmar();
    await waitFor(() => expect(mensaje().className).toContain("ok"));
    expect(llaves()).toHaveLength(2);
    expect(llaves()[1]).toBe(llaves()[0]);
    expect(operaciones.size).toBe(1);
    expect(saldos[ORIGEN]).toBe(1050);
    expect($("resultado").textContent).toMatch(/ya estaba registrada/i);

    // Otra transferencia es otro intento: otra llave.
    $("btnNuevaTrans").click();
    await transferir({ monto: "10.00" });
    await waitFor(() => expect(operaciones.size).toBe(2));
    expect(new Set(llaves()).size).toBe(2);

    // Una respuesta perdida y luego otro monto: no reutiliza la llave del intento anterior.
    respuestaTransferencia = () => "red";
    $("btnNuevaTrans").click();
    await transferir({ monto: "20.00" });
    await waitFor(() => expect(mensaje().className).toContain("warn"));
    respuestaTransferencia = (cuerpo, llave) => transferirComoElServidor(cuerpo, llave);
    await transferir({ monto: "21.00" });
    await waitFor(() => expect(mensaje().className).toContain("ok"));
    expect(new Set(llaves()).size).toBe(4);
  });

  it("HB-24 El comprobante muestra lo que devuelve el servidor (canal Home Banking, glosa enviada)", async () => {
    cargarPagina();
    await llenar({ tercero: TERCERO });
    escribir("glosa", "Pago de alquiler");
    $("btnTransferir").click();
    await waitFor(() => expect(dialogo()).not.toBeNull());
    await confirmar();
    await waitFor(() => expect(mensaje().className).toContain("ok"));
    const envio = envios()[0];
    expect(JSON.parse(envio.init.body as string)).toEqual({
      num_cuenta_origen: ORIGEN, num_cuenta_destino: TERCERO, monto: "150.00", glosa: "Pago de alquiler" });
    expect((envio.init.headers as Record<string, string>)["X-Channel-ID"]).toBe("WEB");
    const r = $("resultado");
    expect(r.hidden).toBe(false);
    expect(r.textContent).toContain("S/ 150.00");
    expect(r.textContent).toContain("S/ 1,050.00");
    expect(r.textContent).toContain(ORIGEN);
    expect(r.textContent).toContain(TERCERO);
    expect(r.textContent).toContain(TITULAR_TERCERO);
    expect(r.textContent).toContain("deb-1");
    expect(r.textContent).not.toMatch(/null|undefined|NaN|S\/ 0\.00|N\/D/);
  });

  it("HB-25 Si al servidor le falta un dato del comprobante, error con el número de operación y sin comprobante", async () => {
    respuestaTransferencia = (cuerpo, llave) => transferirComoElServidor(cuerpo, llave,
      { saldo_disponible_origen: null, fecha_hora: undefined });
    cargarPagina();
    await transferir();
    await waitFor(() => expect(mensaje().className).toContain("error"));
    expect(mensaje().textContent).toMatch(/deb-1/);
    expect(mensaje().textContent).toMatch(/saldo/i);
    expect(mensaje().textContent).toMatch(/fecha/i);
    expect($("resultado").hidden).toBe(true);
    expect(document.body.textContent).not.toMatch(/\bnull\b|undefined|S\/ 0\.00/);
  });

  it("HB-26 Si el monto o la cuenta registrados no son los pedidos, no se muestra como transferencia correcta", async () => {
    respuestaTransferencia = (cuerpo, llave) => transferirComoElServidor(cuerpo, llave, { monto: "15.00" });
    cargarPagina();
    await transferir();
    await waitFor(() => expect(mensaje().className).toContain("error"));
    expect(mensaje().textContent).toMatch(/monto/i);
    expect(mensaje().textContent).toMatch(/deb-1/);
    expect($("resultado").hidden).toBe(true);
  });

  it("HB-27 Rechazo del banco: dice el motivo, sin comprobante, y el intento siguiente lleva otra llave", async () => {
    respuestaTransferencia = () => errorCuentas(400, "ERR-CTA-TOPE-EXCEDIDO",
      "RN-TOP-001: tope diario de HB excedido en 18250122240575");
    cargarPagina();
    await transferir();
    await waitFor(() => expect(mensaje().className).toContain("error"));
    expect(mensaje().textContent).toMatch(/tope diario/i);
    expect(mensaje().textContent).toMatch(/no se movió dinero/i);
    expect(mensaje().textContent).not.toMatch(/RN-TOP-001/);
    expect($("resultado").hidden).toBe(true);
    respuestaTransferencia = (cuerpo, llave) => transferirComoElServidor(cuerpo, llave);
    $("btnTransferir").click();
    await waitFor(() => expect(dialogo()).not.toBeNull());
    await confirmar();
    await waitFor(() => expect(mensaje().className).toContain("ok"));
    expect(new Set(llaves()).size).toBe(2);
  });

  it("HB-28 Una cuenta de destino que no existe se avisa antes de confirmar y no se envía nada", async () => {
    cargarPagina();
    await llenar({ tercero: "99999999999999" });
    $("btnTransferir").click();
    await waitFor(() => expect(mensaje().className).toContain("error"));
    expect(mensaje().textContent).toMatch(/no existe/i);
    expect(dialogo()).toBeNull();
    expect(envios()).toEqual([]);
    expect($<HTMLButtonElement>("btnTransferir").disabled).toBe(false);
  });
});

describe("Home Banking: Transferencias sin promesas falsas", () => {
  it("HB-29 La página no promete Token Matriz, riesgo, topes fijos ni interbancarias, ni muestra códigos internos", () => {
    const pagina = leer("transferencias.html");
    expect(pagina).not.toMatch(/Token Matriz|INT-\d|RN-[A-Z]+-\d|RF-HB|Interbancaria|BCP|Se valida en el Bus/);
    const script = leer("js/transferencias.js");
    expect(script).not.toMatch(/Token Matriz|190\.12\.44\.107|LIMITE_DIARIO|\|\| 0\b/);
    expect(leer("js/bus.js")).not.toMatch(/toLocaleString\("es-PE"\)|entidadDestino: "BNA"/);
  });
});
