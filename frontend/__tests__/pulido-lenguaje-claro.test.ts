import { readFileSync, readdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { waitFor } from "@testing-library/react";

// Hallazgos C7, C9 y M6 de la prueba «solo con el mouse»: el Home Banking enseñaba rutas,
// identificadores de requisitos y códigos de error en lo que lee el cliente. Los comentarios del
// código pueden seguir siendo técnicos; las pantallas y los avisos, no.
const HB = resolve(process.cwd(), "public/homebanking"); // vitest corre en frontend/
const leer = (f: string) => readFileSync(join(HB, f), "utf8");
const paginas = readdirSync(HB).filter((f) => f.endsWith(".html"));
const guiones = readdirSync(join(HB, "js")).filter((f) => f.endsWith(".js"));

const JERGA = /GET \/|POST \/coredb|\bINT-\d|\bRF-HB|CR-INT-\d+|error 403|correlaci[oó]n/i;
const JERGA_FUENTE = /GET \/|POST \/coredb|\bINT-\d|\bRF-HB|CR-INT-\d+|error 403|correlaci[oó]n/i;

function textoVisible(archivo: string) {
  return leer(archivo)
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ");
}

function sinComentarios(texto: string) {
  return texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/[^\n]*/g, "$1");
}

function cargar(archivos: string[]) {
  document.body.innerHTML = leer("index.html")
    .slice(0, leer("index.html").lastIndexOf("</body>"))
    .replace(/^[\s\S]*?<body[^>]*>/, "")
    .replace(/<script[\s\S]*?<\/script>/g, "");
  (0, eval)(archivos.map((f) => leer(`js/${f}`)).join("\n;\n"));
}

const $ = (id: string) => document.getElementById(id) as HTMLElement;

beforeEach(() => {
  sessionStorage.clear();
  localStorage.clear();
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({}), { status: 200 })));
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  sessionStorage.clear();
  localStorage.clear();
  document.body.innerHTML = "";
});

describe("Home Banking: lenguaje claro", () => {
  it("HB-PU-01 ninguna pantalla muestra jerga en el texto visible", () => {
    for (const pagina of paginas) expect(textoVisible(pagina), pagina).not.toMatch(JERGA);
  });

  it("HB-PU-02 ningún guión muestra jerga en los textos que escribe en pantalla", () => {
    // Las rutas de los puentes ("/api/…") no se muestran: HB-03 comprueba que existan.
    for (const guion of guiones)
      expect(sinComentarios(leer(`js/${guion}`)).replace(/(["'`])\/api\/[^"'`]*\1/g, '""'), guion).not.toMatch(JERGA_FUENTE);
  });

  it("HB-PU-03 mensajeError traduce códigos, estados y correlaciones a lenguaje llano", () => {
    (0, eval)(leer("js/comun.js"));
    const traducir = (globalThis as unknown as { mensajeError: (e: unknown) => string }).mensajeError;
    const crudo = {
      codigo: "PERMISO_DENEGADO", status: 403,
      mensaje: "403 error en POST /api/core/coredb correlación c-123 INT-08",
    };
    const texto = traducir(crudo);
    expect(texto).toMatch(/Tu rol no puede hacer esta operación/);
    expect(texto).not.toMatch(JERGA);
    expect(texto).not.toMatch(/\/api\/|\b403\b/);
    expect(traducir({ codigo: "OTRO_CODIGO", mensaje: "GET /api/x RF-HB-002", status: 500 })).not.toMatch(JERGA);
  });

  it("HB-PU-04 el aviso de error del login no deja escapar el código ni la ruta", async () => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      if (String(url).includes("logout")) return new Response("{}", { status: 200 });
      return new Response(JSON.stringify({ error: {
        code: "PERMISO_DENEGADO", message: "403 /api/core/coredb/auth/login correlación c-9",
      } }), { status: 403 });
    }));
    cargar(["bus.js", "comun.js", "login.js"]);
    $("usuario").setAttribute("value", "operador");
    $("claveWeb").setAttribute("value", "clave");
    $("codCliente").setAttribute("value", "CLI1");
    $("formLogin").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await waitFor(() => expect($("msgLogin").textContent).toMatch(/Tu rol no puede hacer esta operación/));
    expect($("msgLogin").textContent).not.toMatch(JERGA);
    expect($("msgLogin").textContent).not.toMatch(/\/api\/|\b403\b|correlaci[oó]n/i);
  });

  it("HB-PU-05 «Obtener cuentas» dice de dónde salen los 16 dígitos", () => {
    const pagina = textoVisible("cuentas.html");
    expect(pagina).toMatch(/Mis tarjetas/);
    expect(pagina).toMatch(/16 dígitos/);
    expect(pagina).toMatch(/aparecen en tu tarjeta/);
    expect(pagina).not.toMatch(/solicitud al Bus/);
    const guion = sinComentarios(leer("js/cuentas.js"));
    expect(guion).not.toMatch(/Ingrese los 16 dígitos de su tarjeta\./);
    expect(guion).toMatch(/Elige una de Mis tarjetas o escribe los 16 dígitos de tu tarjeta\./);
  });
});
