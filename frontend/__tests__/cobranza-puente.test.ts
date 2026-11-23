// @vitest-environment node
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { AxiosError } from "axios";
import { NextRequest } from "next/server";
import { GET, POST } from "../app/api/cobranza/[...path]/route";
import { mensajeDeError } from "../lib/cobranza";

// El puente de Cobranza responde sus propios rechazos con la misma forma que Cobranza y
// COREDB ({"error": {"code", "message"}}), para que "Pagar cuota" muestre su texto.
const upstream = vi.fn();
const context = (path: string[]) => ({ params: Promise.resolve({ path }) });

function peticion(metodo: string, headers: Record<string, string> = {}) {
  return new NextRequest("http://localhost:3000/api/cobranza/x", {
    method: metodo,
    headers: { host: "localhost:3000", ...headers },
    body: metodo === "POST" ? "{}" : undefined,
  });
}

async function mensajeMostrado(respuesta: Response) {
  const data = await respuesta.json();
  const err = new AxiosError("fail", "ERR_BAD_REQUEST", undefined, undefined, {
    status: respuesta.status, statusText: "", headers: {}, config: {} as never, data,
  });
  return { data, texto: mensajeDeError(err) };
}

beforeEach(() => {
  vi.stubGlobal("fetch", upstream);
  upstream.mockReset().mockImplementation(async () => Response.json({ ok: true }));
});
afterEach(() => { vi.unstubAllGlobals(); });

it("una ruta no expuesta responde 404 con su mensaje", async () => {
  const r = await GET(peticion("GET", { authorization: "Bearer x" }), context(["otra", "ruta"]));
  expect(r.status).toBe(404);
  const { data, texto } = await mensajeMostrado(r);
  expect(data.error.code).toBe("RUTA_NO_DISPONIBLE");
  expect(texto).toBe("Ruta no disponible en este canal.");
  expect(upstream).not.toHaveBeenCalled();
});

it("sin sesión responde 401 con su mensaje", async () => {
  const r = await GET(peticion("GET"), context(["clientes", "CLI1", "creditos"]));
  expect(r.status).toBe(401);
  const { data, texto } = await mensajeMostrado(r);
  expect(data.error.code).toBe("SESION_REQUERIDA");
  expect(texto).toBe("Inicia sesión para continuar.");
  expect(upstream).not.toHaveBeenCalled();
});

it("un pago desde otro origen responde 403 con su mensaje", async () => {
  const r = await POST(
    peticion("POST", { authorization: "Bearer x", origin: "http://otro.example" }),
    context(["cr-int-08", "pagos"]),
  );
  expect(r.status).toBe(403);
  const { data, texto } = await mensajeMostrado(r);
  expect(data.error.code).toBe("ORIGEN_NO_PERMITIDO");
  expect(texto).toBe("Origen de la petición no permitido.");
  expect(upstream).not.toHaveBeenCalled();
});
