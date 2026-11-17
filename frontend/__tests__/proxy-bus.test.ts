// @vitest-environment node
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { POST as core } from "../app/api/core/[...path]/route";
import { POST as cuenta } from "../app/api/cuenta/[...path]/route";
import { POST as sol } from "../app/api/solicitud-credito/[...path]/route";

// Los puentes del frontend llegan a los módulos por el Bus de Servicios: presentan la
// credencial del Bus que tiene el servidor (BUS_TOKEN) y nunca la que mande el navegador.
const upstream = vi.fn();
const context = (path: string[]) => ({ params: Promise.resolve({ path }) });
const TOKEN = "t".repeat(48);

function peticion(url: string, headers: Record<string, string> = {}) {
  return new NextRequest(url, {
    method: "POST",
    headers: { host: "localhost:3000", origin: "http://localhost:3000", ...headers },
    body: "{}",
  });
}
const cabecerasEnviadas = () => new Headers(upstream.mock.calls[0][1].headers);

beforeEach(() => {
  vi.stubGlobal("fetch", upstream);
  vi.stubEnv("COREDB_URL", "http://bus:8018/bus/coredb");
  vi.stubEnv("CUENTAS_GATEWAY_URL", "http://bus:8018/bus/cuentas/api/v1/cuentas");
  vi.stubEnv("SOL_GATEWAY_URL", "http://bus:8018/bus/sol/gateway/sol");
  vi.stubEnv("SOL_PUBLIC_ORIGIN", "");
  upstream.mockReset().mockResolvedValue(Response.json({ ok: true }));
});
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

it("el puente de COREDB presenta la credencial del Bus y va a su ruta en el Bus", async () => {
  vi.stubEnv("BUS_TOKEN", TOKEN);
  await core(peticion("http://localhost:3000/api/core/coredb/auth/login"), context(["coredb", "auth", "login"]));
  expect(upstream.mock.calls[0][0]).toBe("http://bus:8018/bus/coredb/coredb/auth/login");
  expect(cabecerasEnviadas().get("X-Bus-Token")).toBe(TOKEN);
});

it("no reenvía una credencial del Bus que mande el navegador", async () => {
  await cuenta(peticion("http://localhost:3000/api/cuenta/deposito", { "X-Bus-Token": "del-navegador" }),
    context(["deposito"]));
  expect(cabecerasEnviadas().get("X-Bus-Token")).toBeNull();

  upstream.mockClear();
  vi.stubEnv("BUS_TOKEN", TOKEN);
  await cuenta(peticion("http://localhost:3000/api/cuenta/deposito", { "X-Bus-Token": "del-navegador" }),
    context(["deposito"]));
  expect(cabecerasEnviadas().get("X-Bus-Token")).toBe(TOKEN);
});

it("sigue reenviando Authorization, idempotencia y correlación", async () => {
  vi.stubEnv("BUS_TOKEN", TOKEN);
  await cuenta(peticion("http://localhost:3000/api/cuenta/deposito", {
    authorization: "Bearer jwt", "x-idempotency-key": "op-1", "x-correlation-id": "c-1",
  }), context(["deposito"]));
  const enviadas = cabecerasEnviadas();
  expect(enviadas.get("Authorization")).toBe("Bearer jwt");
  expect(enviadas.get("X-Idempotency-Key")).toBe("op-1");
  expect(enviadas.get("X-Correlation-ID")).toBe("c-1");
});

it("muestra el error claro del Bus cuando el módulo está caído", async () => {
  vi.stubEnv("BUS_TOKEN", TOKEN);
  upstream.mockResolvedValue(Response.json(
    { detail: "No se pudo contactar al módulo CUENTAS.", codigo: "MODULO_NO_DISPONIBLE", modulo: "CUENTAS" },
    { status: 503 }));
  const respuesta = await cuenta(peticion("http://localhost:3000/api/cuenta/deposito"), context(["deposito"]));
  expect(respuesta.status).toBe(503);
  expect((await respuesta.json()).codigo).toBe("MODULO_NO_DISPONIBLE");
});

it("el puente de SOL también presenta la credencial del Bus", async () => {
  vi.stubEnv("BUS_TOKEN", TOKEN);
  await sol(peticion("http://localhost:3000/api/solicitud-credito/auth/login", { "X-Bus-Token": "del-navegador" }),
    context(["auth", "login"]));
  expect(upstream.mock.calls[0][0]).toBe("http://bus:8018/bus/sol/gateway/sol/auth/login");
  expect(cabecerasEnviadas().get("X-Bus-Token")).toBe(TOKEN);
});
