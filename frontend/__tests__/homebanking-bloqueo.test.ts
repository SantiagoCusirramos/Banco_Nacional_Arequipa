import { readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { waitFor } from "@testing-library/react";

// Bloqueo de tarjeta desde el Home Banking: la página de cuentas lista las tarjetas del cliente
// (GET /api/tarjeta/cliente/{cod}) y cada tarjeta ACTIVA tiene un botón «Bloquear» que, tras
// confirmar, llama a la ruta de bloqueo de TARJETAS (POST /api/tarjeta/{id}/bloqueo, por el Bus).
const HB = resolve(process.cwd(), "public/homebanking"); // vitest corre en frontend/
const leer = (f: string) => readFileSync(join(HB, f), "utf8");

const ACTIVA = "445f1137-d511-5d48-b805-b95b14994c94";
const BLOQUEADA = "7e570001-0000-4000-8000-000000000002";
// Forma real de TARJETAS (GET /api/v1/tarjetas/cliente/{cod}, capturada con ./bna up).
const tarjeta = (id: string, ultimos4: string, estado: string) => ({
  id_tarjeta: id, bin: "004499", ultimos4, fecha_emision: "2026-11-19", fecha_vencimiento: "2030-11-19",
  estado_tarjeta: estado, cod_cliente: "CLI000000001", num_cuenta: "59144088949989",
  numero_enmascarado: `0044 99** **** ${ultimos4}`, vencimiento_mm_aa: "11/30",
});
const sobre = (data: unknown, message = "Operacion ejecutada satisfactoriamente") =>
  ({ success: true, status_code: 200, message, data, metadata: { modulo_emisor: "TARJETAS" } });

type Respuesta = { status: number; body: unknown };
let llamadas: { url: string; init: RequestInit }[];
let bloqueo: Respuesta;

function cargarPagina() {
  const html = leer("cuentas.html");
  document.body.innerHTML = html.slice(html.indexOf("<body"), html.lastIndexOf("</body>"))
    .replace(/^<body[^>]*>/, "").replace(/<script[\s\S]*?<\/script>/g, "");
  // Los tres scripts de la página, en su orden y en un solo ámbito (como en el navegador).
  const codigo = ["js/bus.js", "js/comun.js", "js/cuentas.js"].map(leer).join("\n;\n");
  (0, eval)(codigo);
}

beforeEach(() => {
  llamadas = [];
  bloqueo = { status: 200, body: sobre({ ...tarjeta(ACTIVA, "9102", "BLOQUEADA") }, "Tarjeta bloqueada") };
  sessionStorage.setItem("hb_sesion_bna", JSON.stringify({ codCliente: "CLI000000001", nombres: "Rosa Quispe", dni: "asesor" }));
  localStorage.setItem("bna_access_token", "token-de-coredb");
  vi.stubGlobal("fetch", vi.fn(async (url: string, init: RequestInit = {}) => {
    llamadas.push({ url, init });
    const r: Respuesta = url.endsWith("/bloqueo") ? bloqueo
      : url.startsWith("/api/tarjeta/cliente/")
        ? { status: 200, body: sobre([tarjeta(ACTIVA, "9102", "ACTIVA"), tarjeta(BLOQUEADA, "0002", "BLOQUEADA")]) }
        : { status: 404, body: { detail: "no simulado" } };
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

const botones = () => [...document.querySelectorAll<HTMLButtonElement>("button[data-bloquear]")];
const bloqueos = () => llamadas.filter((l) => l.url.endsWith("/bloqueo"));
const mensaje = () => document.getElementById("msgBloqueo")!;

describe("Home Banking: bloquear tarjeta", () => {
  it("HB-05 Solo las tarjetas ACTIVA tienen el botón «Bloquear»", async () => {
    cargarPagina();
    await waitFor(() => expect(botones()).toHaveLength(1));
    expect(botones()[0].dataset.bloquear).toBe(ACTIVA);
    expect(botones()[0].textContent).toBe("Bloquear");
    expect(botones()[0].getAttribute("aria-label")).toContain("9102");
  });

  it("HB-06 Pide confirmación; si el cliente cancela, no bloquea", async () => {
    const confirmar = vi.spyOn(window, "confirm").mockReturnValue(false);
    cargarPagina();
    await waitFor(() => expect(botones()).toHaveLength(1));
    botones()[0].click();
    expect(confirmar).toHaveBeenCalledOnce();
    expect(confirmar.mock.calls[0][0]).toMatch(/9102/);
    expect(bloqueos()).toEqual([]);
    expect(botones()).toHaveLength(1);
  });

  it("HB-07 Confirmado: POST a la ruta de bloqueo de TARJETAS, mensaje de éxito y la tarjeta queda BLOQUEADA", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    cargarPagina();
    await waitFor(() => expect(botones()).toHaveLength(1));
    botones()[0].click();
    await waitFor(() => expect(mensaje().className).toContain("ok"));
    expect(bloqueos()).toHaveLength(1);
    const { url, init } = bloqueos()[0];
    expect(url).toBe(`/api/tarjeta/${ACTIVA}/bloqueo`);
    expect(init.method).toBe("POST");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer token-de-coredb");
    expect(JSON.parse(init.body as string).motivo.length).toBeGreaterThanOrEqual(3);
    expect(mensaje().textContent).toMatch(/9102.*bloqueada/i);
    expect(botones()).toEqual([]);
    expect(document.getElementById("chipsTarjetas")!.textContent).not.toMatch(/9102[^]*ACTIVA/);
  });

  it("HB-08 Si TARJETAS rechaza, muestra el error y la tarjeta sigue con su botón", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    bloqueo = { status: 422, body: { success: false, error_code: "ERR-TAR-002", message: "La tarjeta no puede pasar de ACTIVA a BLOQUEADA" } };
    cargarPagina();
    await waitFor(() => expect(botones()).toHaveLength(1));
    botones()[0].click();
    await waitFor(() => expect(mensaje().className).toContain("error"));
    expect(mensaje().textContent).toContain("La tarjeta no puede pasar de ACTIVA a BLOQUEADA");
    expect(botones()).toHaveLength(1);
    expect(botones()[0].disabled).toBe(false);
  });
});
