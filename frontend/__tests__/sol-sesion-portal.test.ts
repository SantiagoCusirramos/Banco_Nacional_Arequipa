// @vitest-environment node
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { POST } from "../app/api/solicitud-credito/[...path]/route";

// Solicitud de crédito adopta la sesión del portal: el token de COREDB que ya tiene el navegador
// pasa a la cookie HttpOnly de Solicitud después de que SOL lo acepta en /auth/me. Así hay una sola
// sesión (la del portal) que cerrar, y no queda abierta la de otro usuario.
const upstream = vi.fn();
const context = { params: Promise.resolve({ path: ["auth", "portal"] }) };

function pedir(cabeceras: Record<string, string> = {}, origin: string | null = "http://localhost:3000") {
  const headers: Record<string, string> = { host: "localhost:3000", ...cabeceras };
  if (origin !== null) headers.origin = origin;
  return new NextRequest("http://localhost:3000/api/solicitud-credito/auth/portal", { method: "POST", headers, body: "{}" });
}

beforeEach(() => {
  vi.stubGlobal("fetch", upstream);
  vi.stubEnv("SOL_GATEWAY_URL", "http://sol.fake:8011/sol");
  vi.stubEnv("SOL_COOKIE_SECURE", "false");
  vi.stubEnv("SOL_PUBLIC_ORIGIN", "");
  upstream.mockReset().mockResolvedValue(Response.json({ username: "asesora.dos", nombre: "Asesora Dos", rol: "ASESOR" }));
});
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

it("SP-10 con el token del portal que SOL acepta, guarda la cookie HttpOnly y devuelve el usuario", async () => {
  const response = await POST(pedir({ Authorization: "Bearer token-del-portal" }), context);
  expect(response.status).toBe(200);
  expect(await response.json()).toEqual({ usuario: { username: "asesora.dos", nombre: "Asesora Dos", rol: "ASESOR" } });
  const [url, init] = upstream.mock.calls[0];
  expect(url).toBe("http://sol.fake:8011/sol/auth/me");
  expect((init as RequestInit).method).toBe("GET");
  expect(new Headers((init as RequestInit).headers).get("Authorization")).toBe("Bearer token-del-portal");
  const cookie = response.headers.get("set-cookie") || "";
  expect(cookie).toContain("bna_sol_session=token-del-portal");
  expect(cookie).toMatch(/HttpOnly/i);
  expect(cookie).toContain("Path=/api/solicitud-credito");
});

it("SP-11 sin token no llama a SOL", async () => {
  const response = await POST(pedir(), context);
  expect(response.status).toBe(401);
  expect(upstream).not.toHaveBeenCalled();
});

it("SP-12 si SOL rechaza el token, no guarda cookie y responde lo mismo que SOL", async () => {
  upstream.mockResolvedValue(Response.json({ detail: "Tu perfil no usa Solicitud de Crédito." }, { status: 403 }));
  const response = await POST(pedir({ Authorization: "Bearer token-de-cajero" }), context);
  expect(response.status).toBe(403);
  expect(await response.json()).toEqual({ detail: "Tu perfil no usa Solicitud de Crédito." });
  expect(response.headers.get("set-cookie")).toBeNull();
});

it("SP-13 exige el mismo origen, como toda escritura", async () => {
  const response = await POST(pedir({ Authorization: "Bearer token-del-portal" }, "http://externo.test"), context);
  expect(response.status).toBe(403);
  expect(upstream).not.toHaveBeenCalled();
});
