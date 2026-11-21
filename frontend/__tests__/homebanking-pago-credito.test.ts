import { readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { waitFor } from "@testing-library/react";

// Pago de cuota desde el Home Banking (creditos.html). Antes, «Continuar con Token Matriz» pagaba
// en el acto, sin confirmación ni código, y el comprobante mostraba S/ 0.00 y «null» porque los
// datos se ponían a mano. Ahora: resumen y confirmación explícita, código SIMULADO que bloquea el
// pago si no coincide, una llave por intento (la misma en cada reintento), botón deshabilitado y
// comprobante solo con lo que devuelve COBRANZA (o un error claro si falta algo).
const HB = resolve(process.cwd(), "public/homebanking"); // vitest corre en frontend/
const leer = (f: string) => readFileSync(join(HB, f), "utf8");

const CLIENTE = "CLI000000003";
const CREDITO = "CRE-2026-000001";
const CUENTA = "18250122240575";
const CUOTA = "176.55";

// Cronograma del crédito de 1000 a 6 meses de la revisión de usabilidad (forma de COBRANZA).
const cuotas = (pagadas: number) => Array.from({ length: 6 }, (_, i) => {
  const monto = i === 5 ? "176.54" : CUOTA;
  return {
    idCuota: `${CREDITO}-${i + 1}`, numeroCuota: i + 1, fechaVencimiento: `2026-${String(12 + i).padStart(2, "0")}-21`,
    montoCuota: monto, saldoPendiente: i < pagadas ? "0.00" : monto, moraPendiente: "0.00",
    totalAdeudado: i < pagadas ? "0.00" : monto, estadoCuota: i < pagadas ? "PAGADA" : "PENDIENTE",
  };
});

type Respuesta = { status: number; body: unknown } | "red";
let llamadas: { url: string; init: RequestInit }[];
let debitos: Map<string, number>; // referencia → número de cuota pagada (lo que haría COREDB)
let saldoCuenta: number;
let respuestaPago: (cuerpo: Record<string, string>) => Respuesta;

const saldoCredito = () => (1059.29 - debitos.size * 176.55).toFixed(2);

// COBRANZA real: la misma referencia devuelve el mismo pago sin otro débito.
function cobrarComoElServidor(cuerpo: Record<string, string>, extra: Record<string, unknown> = {}): Respuesta {
  const repetido = debitos.has(cuerpo.referenciaTransaccion);
  if (!repetido) {
    debitos.set(cuerpo.referenciaTransaccion, debitos.size + 1);
    saldoCuenta -= Number(cuerpo.montoPago);
  }
  const numero = debitos.get(cuerpo.referenciaTransaccion)!;
  return {
    status: repetido ? 200 : 201,
    body: {
      idPago: `pago-${numero}`, referenciaTransaccion: cuerpo.referenciaTransaccion, estado: "CONFIRMADO",
      idempotente: repetido, motivo: null, codCredito: CREDITO, idCanal: "HB", montoPago: cuerpo.montoPago,
      fechaHora: "2026-11-21T12:40:00Z", estadoCredito: "AL_DIA",
      aplicacion: { idCuota: `${CREDITO}-${numero}`, numeroCuota: numero, montoAplicado: cuerpo.montoPago },
      saldoCredito: saldoCredito(), cuotasPendientes: 6 - debitos.size, cuotasPagadas: [numero],
      numCuenta: cuerpo.cuentaOrigen, moneda: "PEN", montoAplicado: cuerpo.montoPago,
      uuidTransaccion: `mov-${numero}`, ...extra,
    },
  };
}

function cargarPagina() {
  const html = leer("creditos.html");
  document.body.innerHTML = html.slice(html.indexOf("<body"), html.lastIndexOf("</body>"))
    .replace(/^<body[^>]*>/, "").replace(/<script[\s\S]*?<\/script>/g, "");
  // Los scripts de la página, en su orden y en un solo ámbito (como en el navegador).
  const scripts = [...html.matchAll(/<script src="([^"]+)"/g)].map((m) => m[1]);
  (0, eval)(scripts.map(leer).join("\n;\n"));
}

beforeEach(() => {
  llamadas = [];
  debitos = new Map();
  saldoCuenta = 1200;
  respuestaPago = (cuerpo) => cobrarComoElServidor(cuerpo);
  sessionStorage.setItem("hb_sesion_bna", JSON.stringify({ codCliente: CLIENTE, nombres: "Operador", dni: "operador" }));
  localStorage.setItem("bna_access_token", "token-de-coredb");
  vi.stubGlobal("fetch", vi.fn(async (url: string, init: RequestInit = {}) => {
    llamadas.push({ url, init });
    let r: Respuesta;
    if (url === "/api/cobranza/cr-int-08/pagos") r = respuestaPago(JSON.parse(init.body as string));
    else if (url === `/api/cobranza/clientes/${CLIENTE}/creditos`) {
      r = { status: 200, body: [{ codCredito: CREDITO, idCliente: CLIENTE, montoAprobado: "1000.00", moneda: "PEN",
        estadoCredito: "AL_DIA", saldoTotalPendiente: saldoCredito(), cuotas: cuotas(debitos.size) }] };
    } else if (url === `/api/cuenta/consolidada/${CLIENTE}`) {
      const s = saldoCuenta.toFixed(2);
      r = { status: 200, body: { success: true, data: [{ num_cuenta: CUENTA, moneda: "PEN", saldo_contable: s,
        saldo_disponible: s, regimen: "INDIVIDUAL", estado_cuenta: "ACTIVA" }] } };
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
const pagos = () => llamadas.filter((l) => l.url === "/api/cobranza/cr-int-08/pagos");
const referencias = () => pagos().map((l) => JSON.parse(l.init.body as string).referenciaTransaccion);
const dialogo = () => document.querySelector<HTMLElement>("[role=dialog]");
const mensaje = () => $("msgCredito");

async function abrirConfirmacion() {
  await waitFor(() => expect($<HTMLSelectElement>("selCuenta").value).toBe(CUENTA));
  $("btnPagar").click();
  await waitFor(() => expect(dialogo()).not.toBeNull());
}

function escribirCodigo(codigo?: string) {
  const correcto = $("codigoSimulado").textContent!.trim();
  const campo = $<HTMLInputElement>("codigoIngresado");
  campo.value = codigo ?? correcto;
  campo.dispatchEvent(new Event("input", { bubbles: true }));
  return correcto;
}

async function pagar() {
  await abrirConfirmacion();
  escribirCodigo();
  $("btnConfirmarPago").click();
  await waitFor(() => expect(dialogo()).toBeNull());
}

describe("Home Banking: pagar una cuota", () => {
  it("HB-09 «Pagar» solo abre un resumen (monto, cuota, crédito, cuenta de origen); nada se envía antes de confirmar", async () => {
    cargarPagina();
    expect($("btnPagar").textContent).not.toMatch(/Token Matriz/i);
    await abrirConfirmacion();
    const texto = dialogo()!.textContent!;
    expect(texto).toContain("S/ 176.55");
    expect(texto).toMatch(/cuota 1\b/i);
    expect(texto).toContain(CREDITO);
    expect(texto).toContain(CUENTA);
    expect(pagos()).toEqual([]);
  });

  it("HB-10 Cancelar (botón o Escape) no cobra y lo dice", async () => {
    cargarPagina();
    await abrirConfirmacion();
    $("btnCancelarPago").click();
    await waitFor(() => expect(dialogo()).toBeNull());
    expect(mensaje().textContent).toMatch(/no se cobró/i);
    expect($<HTMLButtonElement>("btnPagar").disabled).toBe(false);

    $("btnPagar").click();
    await waitFor(() => expect(dialogo()).not.toBeNull());
    dialogo()!.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await waitFor(() => expect(dialogo()).toBeNull());
    expect(pagos()).toEqual([]);
    expect(debitos.size).toBe(0);
  });

  it("HB-11 El código está rotulado como SIMULACIÓN; uno incorrecto bloquea el pago y tres lo cancelan", async () => {
    cargarPagina();
    await abrirConfirmacion();
    expect(dialogo()!.textContent).toMatch(/simulaci[oó]n/i);
    expect(dialogo()!.textContent).toMatch(/no es un segundo factor real/i);
    const correcto = escribirCodigo();
    expect(correcto).toMatch(/^\d{6}$/);
    const errado = correcto.replace(/^./, (d) => String((Number(d) + 1) % 10));
    // Sin código no se puede confirmar.
    escribirCodigo("");
    $("btnConfirmarPago").click();
    expect(pagos()).toEqual([]);
    for (let i = 0; i < 2; i++) {
      escribirCodigo(errado);
      $("btnConfirmarPago").click();
      await waitFor(() => expect($("confirmacionError").textContent).toMatch(/incorrecto/i));
      expect(dialogo()).not.toBeNull();
    }
    escribirCodigo(errado);
    $("btnConfirmarPago").click();
    await waitFor(() => expect(dialogo()).toBeNull());
    expect(mensaje().textContent).toMatch(/no se cobró/i);
    expect(pagos()).toEqual([]);
  });

  it("HB-12 Doble clic: un solo diálogo, un solo pago y el botón queda deshabilitado mientras se procesa", async () => {
    let soltar!: () => void;
    const pendiente = new Promise<void>((r) => { soltar = r; });
    respuestaPago = (cuerpo) => cobrarComoElServidor(cuerpo);
    cargarPagina();
    await waitFor(() => expect($<HTMLSelectElement>("selCuenta").value).toBe(CUENTA));
    $("btnPagar").click();
    $("btnPagar").click();
    await waitFor(() => expect(dialogo()).not.toBeNull());
    expect(document.querySelectorAll("[role=dialog]")).toHaveLength(1);

    const fetchReal = globalThis.fetch as unknown as (u: string, i?: RequestInit) => Promise<Response>;
    vi.stubGlobal("fetch", vi.fn(async (url: string, init: RequestInit = {}) => {
      if (url === "/api/cobranza/cr-int-08/pagos") await pendiente;
      return fetchReal(url, init);
    }));
    escribirCodigo();
    const confirmar = $<HTMLButtonElement>("btnConfirmarPago");
    confirmar.click();
    confirmar.click();
    await waitFor(() => expect(dialogo()).toBeNull());
    expect($<HTMLButtonElement>("btnPagar").disabled).toBe(true);
    $("btnPagar").click();
    expect(dialogo()).toBeNull();
    soltar();
    await waitFor(() => expect(mensaje().className).toContain("ok"));
    expect(pagos()).toHaveLength(1);
    expect(debitos.size).toBe(1);
    expect($<HTMLButtonElement>("btnPagar").disabled).toBe(false);
  });

  it("HB-13 Si la respuesta se pierde, el reintento lleva la misma llave (un solo débito); el pago siguiente, otra", async () => {
    // El servidor cobra, pero la respuesta no llega (corte de red).
    respuestaPago = (cuerpo) => { cobrarComoElServidor(cuerpo); return "red"; };
    cargarPagina();
    await pagar();
    await waitFor(() => expect(mensaje().className).toContain("warn"));
    expect(mensaje().textContent).toMatch(/no se cobrará dos veces/i);
    expect($("resultadoCredito").hidden).toBe(true);

    respuestaPago = (cuerpo) => cobrarComoElServidor(cuerpo);
    await pagar();
    await waitFor(() => expect(mensaje().className).toContain("ok"));
    expect(referencias()).toHaveLength(2);
    expect(referencias()[1]).toBe(referencias()[0]);
    expect(debitos.size).toBe(1);
    expect($("resultadoCredito").textContent).toMatch(/ya estaba registrado/i);

    // Un pago nuevo (la cuota 2) es otro intento: otra llave.
    $("btnNuevoPago").click();
    await pagar();
    await waitFor(() => expect(debitos.size).toBe(2));
    expect(new Set(referencias()).size).toBe(2);
  });

  it("HB-14 El comprobante muestra lo que devuelve el servidor: saldo del crédito, cuotas pendientes, cuota y cuenta", async () => {
    cargarPagina();
    await pagar();
    await waitFor(() => expect(mensaje().className).toContain("ok"));
    const cuerpo = JSON.parse(pagos()[0].init.body as string);
    expect(cuerpo).toMatchObject({ codCliente: CLIENTE, codCredito: CREDITO, montoPago: CUOTA, cuentaOrigen: CUENTA });
    const r = $("resultadoCredito");
    expect(r.hidden).toBe(false);
    await waitFor(() => expect(r.textContent).toContain("S/ 1,023.45"));
    expect(r.textContent).toContain("S/ 176.55");
    expect(r.textContent).toContain("S/ 882.74");
    expect(r.textContent).toMatch(/Cuotas pendientes\s*5(?!\d)/);
    expect(r.textContent).toMatch(/Cuota pagada\s*1(?!\d)/);
    expect(r.textContent).toContain(CUENTA);
    expect(r.textContent).not.toMatch(/null|undefined|NaN|S\/ 0\.00/);
  });

  it("HB-15 Si al servidor le falta un dato del comprobante, error claro y ningún valor inventado", async () => {
    respuestaPago = (cuerpo) => cobrarComoElServidor(cuerpo, { saldoCredito: undefined, cuotasPendientes: null });
    cargarPagina();
    await pagar();
    await waitFor(() => expect(mensaje().className).toContain("error"));
    expect(mensaje().textContent).toMatch(/pago-1/);
    expect(mensaje().textContent).toMatch(/saldo del crédito/i);
    expect(mensaje().textContent).toMatch(/cuotas pendientes/i);
    expect($("resultadoCredito").hidden).toBe(true);
    expect(document.body.textContent).not.toMatch(/\bnull\b|undefined/);
  });

  it("HB-16 Si el monto registrado no es el pedido, no se muestra como pago correcto", async () => {
    respuestaPago = (cuerpo) => cobrarComoElServidor(cuerpo, { montoPago: "17.65" });
    cargarPagina();
    await pagar();
    await waitFor(() => expect(mensaje().className).toContain("error"));
    expect(mensaje().textContent).toMatch(/monto/i);
    expect($("resultadoCredito").hidden).toBe(true);
  });

  it("HB-17 Débito rechazado: dice el motivo, sin comprobante, y el intento siguiente lleva otra llave", async () => {
    respuestaPago = (cuerpo) => ({ status: 201, body: { ...(cobrarComoElServidor(cuerpo) as { body: object }).body,
      estado: "RECHAZADO", motivo: "SALDO_INSUFICIENTE", cuotasPagadas: [], uuidTransaccion: null } });
    cargarPagina();
    await pagar();
    await waitFor(() => expect(mensaje().className).toContain("error"));
    expect(mensaje().textContent).toMatch(/saldo insuficiente/i);
    expect($("resultadoCredito").hidden).toBe(true);
    respuestaPago = (cuerpo) => cobrarComoElServidor(cuerpo);
    await pagar();
    await waitFor(() => expect(mensaje().className).toContain("ok"));
    expect(new Set(referencias()).size).toBe(2);
  });
});

describe("Home Banking: sin claves de prueba ni texto de desarrollo", () => {
  it("HB-18 La entrada y la página de créditos no muestran claves de prueba, rutas de desarrollo ni promesas falsas", () => {
    const entrada = leer("index.html");
    for (const prohibido of ["246810", "777777", "CL-0004821", "CL-0009930", "Datos de prueba", "iniciar.sh",
      "127.0.0.1:8080", "Fase III", "RF-HB-001"]) {
      expect(entrada, prohibido).not.toContain(prohibido);
    }
    const creditos = leer("creditos.html");
    expect(creditos).not.toMatch(/Token Matriz|RF-HB-007|INT-14|RN-TOP-001/);
    for (const archivo of ["js/comun.js", "js/login.js", "js/creditos.js"]) {
      expect(leer(archivo), archivo).not.toMatch(/iniciar\.sh|127\.0\.0\.1:8080/);
    }
  });
});
