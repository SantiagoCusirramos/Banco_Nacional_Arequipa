// @vitest-environment node
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { GET, POST } from "../app/api/seguridad/[...path]/route";

// El puente de Seguridad existe solo para la pantalla de desbloqueo de tarjetas: deja pasar
// su perfil y las rutas de tarjetas, y nada más (ni la bitácora ni los incidentes).
const upstream = vi.fn();
const context = (path: string[]) => ({ params: Promise.resolve({ path }) });
const ID = "7e570001-0000-4000-8000-000000000002";

function peticion(metodo: "GET" | "POST", ruta: string, headers: Record<string, string> = {}) {
  return new NextRequest(`http://localhost:3000/api/seguridad/${ruta}`, {
    method: metodo,
    headers: { host: "localhost:3000", ...headers },
    body: metodo === "POST" ? JSON.stringify({ motivo: "Identidad confirmada" }) : undefined,
  });
}

beforeEach(() => {
  vi.stubGlobal("fetch", upstream);
  vi.stubEnv("SEGURIDAD_GATEWAY_URL", "http://bus:8018/bus/seguridad/seguridad");
  vi.stubEnv("BUS_TOKEN", "t".repeat(48));
  upstream.mockReset().mockImplementation(async () => Response.json({ ok: true }));
});
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

describe("puente /api/seguridad", () => {
  it("SP-01 lleva la ficha y el desbloqueo de una tarjeta a Seguridad por el Bus, con el token de la persona", async () => {
    await GET(peticion("GET", `tarjetas/${ID}`, { authorization: "Bearer jwt" }), context(["tarjetas", ID]));
    expect(upstream.mock.calls[0][0]).toBe(`http://bus:8018/bus/seguridad/seguridad/tarjetas/${ID}`);
    const enviadas = new Headers(upstream.mock.calls[0][1].headers);
    expect(enviadas.get("Authorization")).toBe("Bearer jwt");
    expect(enviadas.get("X-Bus-Token")).toBe("t".repeat(48));
    expect(enviadas.get("X-Correlation-ID")).toBeTruthy();

    await POST(peticion("POST", `tarjetas/${ID}/desbloqueo`), context(["tarjetas", ID, "desbloqueo"]));
    expect(upstream.mock.calls[1][0]).toBe(`http://bus:8018/bus/seguridad/seguridad/tarjetas/${ID}/desbloqueo`);
    expect(upstream.mock.calls[1][1].method).toBe("POST");
  });

  it("SP-02 lleva la búsqueda por cliente con su parámetro", async () => {
    const r = new NextRequest("http://localhost:3000/api/seguridad/tarjetas?cod_cliente=CLI000000003");
    await GET(r, context(["tarjetas"]));
    expect(upstream.mock.calls[0][0]).toBe("http://bus:8018/bus/seguridad/seguridad/tarjetas?cod_cliente=CLI000000003");
  });

  it.each([
    ["GET", ["auditoria"]],
    ["GET", ["incidentes"]],
    ["POST", ["incidentes"]],
    ["POST", ["auditoria", "sellos"]],
    ["POST", ["operaciones", "evaluar"]],
    ["POST", ["auth", "login"]],
    ["POST", ["tarjetas", ID]],
    ["POST", ["tarjetas", ID, "estado"]],
    ["GET", ["tarjetas", ID, "desbloqueo"]],
    ["GET", ["tarjetas", "..", "auditoria"]],
  ] as const)("SP-03 no deja pasar %s %j", async (metodo, ruta) => {
    const manejador = metodo === "GET" ? GET : POST;
    const respuesta = await manejador(peticion(metodo, ruta.join("/")), context([...ruta]));
    expect(respuesta.status).toBe(404);
    expect(upstream).not.toHaveBeenCalled();
  });
});

describe("el cliente solo bloquea", () => {
  it("SP-04 el Home Banking no tiene ninguna ruta de desbloqueo ni llega a Seguridad", () => {
    const carpeta = join(__dirname, "..", "public", "homebanking");
    const archivos = [
      ...readdirSync(join(carpeta, "js")).map((f) => join(carpeta, "js", f)),
      ...readdirSync(carpeta).filter((f) => f.endsWith(".html")).map((f) => join(carpeta, f)),
    ];
    for (const archivo of archivos) {
      const texto = readFileSync(archivo, "utf8");
      expect(texto, archivo).not.toMatch(/\/desbloqueo/);
      expect(texto, archivo).not.toMatch(/\/api\/seguridad/);
    }
  });
});
