import { readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { waitFor } from "@testing-library/react";

// Registro de actividad del Home Banking (auditoria.html). Antes prometía «Token Matriz», «riesgo»,
// «topes», «INT-13», «COBIT 2019» y «RNF-HB-005»; mostraba columnas que siempre venían vacías o
// inventadas (canal «-», IP «-», resultado «OK» fijo) y el permiso se descubría al fallar. Ahora
// dice en lenguaje llano qué es (la bitácora del banco), quién puede verla, y muestra solo lo que
// devuelve COREDB, sin interpretar como HTML lo que viene del servidor.
const HB = resolve(process.cwd(), "public/homebanking"); // vitest corre en frontend/
const leer = (f: string) => readFileSync(join(HB, f), "utf8");

const EVENTOS = [
  { id_evento: 912, modulo: "CORE", entidad: "tarjeta", id_entidad: "1a951971-d8de-54ed-b286-9327f5645e30",
    accion: "DESBLOQUEAR_TARJETA", actor: "operador.rev42", correlation_id: "c-1", detalle: null,
    fecha_hora: "2026-11-21T16:30:05Z" },
  { id_evento: 911, modulo: "SOLICITUD DE CREDITO", entidad: "solicitud_credito", id_entidad: "SOL-2611-B3C2EE07",
    accion: "RECIBIR_CR_INT_03", actor: "<img src=x onerror=alert(1)>", correlation_id: null, detalle: null,
    fecha_hora: "2026-11-21T15:04:00Z" },
];

let perfil: { status: number; body: unknown };
let auditoria: { status: number; body: unknown } | "red";
let pedidas: string[];

function cargarPagina() {
  const html = leer("auditoria.html");
  document.body.innerHTML = html.slice(html.indexOf("<body"), html.lastIndexOf("</body>"))
    .replace(/^<body[^>]*>/, "").replace(/<script[\s\S]*?<\/script>/g, "");
  const scripts = [...html.matchAll(/<script src="([^"]+)"/g)].map((m) => m[1]);
  (0, eval)(scripts.map(leer).join("\n;\n"));
}

beforeEach(() => {
  pedidas = [];
  perfil = { status: 200, body: { username: "auditor.rev", rol: "AUDITOR", acciones: ["VER_AUDITORIA", "VER_CLIENTE"] } };
  auditoria = { status: 200, body: EVENTOS };
  sessionStorage.setItem("hb_sesion_bna", JSON.stringify({ codCliente: "CLI000000003", nombres: "Auditor", dni: "auditor" }));
  localStorage.setItem("bna_access_token", "token-de-coredb");
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    pedidas.push(url);
    let r: { status: number; body: unknown } | "red" = { status: 404, body: { detail: "no simulado" } };
    if (url === "/api/core/coredb/auth/me") r = perfil;
    else if (url.startsWith("/api/core/coredb/auditoria")) r = auditoria;
    if (r === "red") throw new TypeError("Failed to fetch");
    return new Response(JSON.stringify(r.body), { status: r.status, headers: { "Content-Type": "application/json" } });
  }));
  vi.stubGlobal("alert", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  sessionStorage.clear();
  localStorage.clear();
  document.body.innerHTML = "";
});

const $ = (id: string) => document.getElementById(id) as HTMLElement;
const visible = (el: HTMLElement | null) => !!el && !el.hidden && !el.closest("[hidden]");
const filas = () => [...document.querySelectorAll("#tablaAuditoria tr")] as HTMLTableRowElement[];

describe("Registro de actividad (auditoria.html)", () => {
  it("HB-30 sin jerga ni promesas falsas en la página ni en su script", () => {
    const html = leer("auditoria.html");
    const js = leer("js/auditoria.js");
    for (const texto of [html, js]) {
      expect(texto).not.toMatch(/Token Matriz|INT-\d|COBIT|RNF-|RF-HB|riesgo|topes|timeouts|Bus de Servicios|UUID|centralizada/i);
    }
    expect(html).not.toMatch(/>IP<|>Canal<|>Resultado<|filtroResultado/);
  });

  it("HB-31 explica en lenguaje llano qué es y quién puede verlo", () => {
    cargarPagina();
    const texto = document.body.textContent ?? "";
    expect(texto).toMatch(/Registro de actividad/);
    expect(texto).toMatch(/quién lo hizo y cuándo/);
    expect(texto).toMatch(/administradores y auditores/);
  });

  it("HB-32 un usuario sin permiso de auditoría lo sabe al entrar y no se pide la bitácora", async () => {
    perfil = { status: 200, body: { username: "operador.rev42", rol: "OPERADOR", acciones: ["VER_TARJETA"] } };
    cargarPagina();
    await waitFor(() => expect($("msgAuditoria").textContent).toMatch(/solo para administradores y auditores/));
    expect(pedidas.some((u) => u.startsWith("/api/core/coredb/auditoria"))).toBe(false);
    expect(visible($("contenidoAuditoria"))).toBe(false);
    expect($("msgAuditoria").textContent).not.toMatch(/PERMISO_DENEGADO|correlación|403/);
  });

  it("HB-33 muestra fecha de Arequipa, acción y módulo legibles, usuario y sobre qué", async () => {
    cargarPagina();
    await waitFor(() => expect(filas()).toHaveLength(2));
    const celdas = [...filas()[0].cells].map((c) => c.textContent);
    expect(celdas).toEqual(["21/11/2026 11:30:05", "Desbloquear tarjeta", "Núcleo del banco", "operador.rev42",
      "Tarjeta 1a951971…"]);
    expect(filas()[1].cells[1].textContent).toBe("Recibir cr int 03");
    expect(filas()[1].cells[2].textContent).toBe("Solicitud de crédito");
    expect(filas()[1].cells[4].textContent).toBe("Solicitud credito SOL-2611-B3C2EE07");
    expect($("resumenAuditoria").textContent).toMatch(/2 acciones/);
  });

  it("HB-34 lo que viene del servidor se muestra como texto, nunca como HTML", async () => {
    cargarPagina();
    await waitFor(() => expect(filas()).toHaveLength(2));
    expect(document.querySelector("#tablaAuditoria img")).toBeNull();
    expect(filas()[1].cells[3].textContent).toBe("<img src=x onerror=alert(1)>");
  });

  it("HB-35 los filtros piden a COREDB por módulo y por acción, con nombres legibles", async () => {
    cargarPagina();
    await waitFor(() => expect(filas()).toHaveLength(2));
    const modulo = $("filtroModulo") as HTMLSelectElement;
    expect([...modulo.options].map((o) => o.textContent)).toContain("Núcleo del banco");
    modulo.value = "CORE";
    modulo.dispatchEvent(new Event("change"));
    await waitFor(() => expect(pedidas.some((u) => u.includes("modulo=CORE"))).toBe(true));
    const accion = $("filtroTipo") as HTMLSelectElement;
    expect([...accion.options].map((o) => o.textContent)).toContain("Desbloquear tarjeta");
  });

  it("HB-36 un error del servidor se explica sin rutas ni códigos", async () => {
    auditoria = { status: 503, body: { detail: "No se pudo contactar al servicio COREDB." } };
    cargarPagina();
    await waitFor(() => expect($("msgAuditoria").textContent).toMatch(/no está disponible/));
    expect($("msgAuditoria").textContent).not.toMatch(/\/api|COREDB|endpoint|503/);
  });

  it("HB-37 sin conexión lo dice en texto llano", async () => {
    auditoria = "red";
    cargarPagina();
    await waitFor(() => expect($("msgAuditoria").textContent).toMatch(/conexión/));
  });

  it("HB-38 el CSV trae solo las columnas reales", async () => {
    let csv = "";
    vi.spyOn(URL, "createObjectURL").mockImplementation(() => "blob:x");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    const OriginalBlob = Blob;
    vi.stubGlobal("Blob", class extends OriginalBlob {
      constructor(partes: BlobPart[], opciones?: BlobPropertyBag) { super(partes, opciones); csv = String(partes.join("")); }
    });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    cargarPagina();
    await waitFor(() => expect(filas()).toHaveLength(2));
    $("btnCsv").click();
    const cabecera = csv.replace(/^﻿/, "").split("\r\n")[0];
    expect(cabecera).toBe('"Fecha y hora","Acción","Módulo","Usuario","Entidad","Identificador","N.º de registro"');
    expect(csv).toContain('"Desbloquear tarjeta"');
    expect(csv).not.toMatch(/"-"|IP|Canal|Resultado/);
  });
});
