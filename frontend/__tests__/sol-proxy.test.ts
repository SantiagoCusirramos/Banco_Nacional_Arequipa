// @vitest-environment node
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { GET, POST } from "../app/api/solicitud-credito/[...path]/route";

const upstream = vi.fn();
function request(path: string[], method = "POST", origin: string | null = "http://localhost:3000") {
  const headers: Record<string, string> = { host: "localhost:3000", cookie: "bna_sol_session=sesion-sintetica", "X-Idempotency-Key": "operacion-e05" };
  if (origin !== null) headers.origin = origin;
  return new NextRequest("http://localhost:3000/api/solicitud-credito/" + path.join("/"), {
    method, headers, ...(method === "GET" ? {} : { body: "{}" }),
  });
}
const context = (path: string[]) => ({ params: Promise.resolve({ path }) });
beforeEach(() => {
  vi.stubGlobal("fetch", upstream);
  vi.stubEnv("SOL_GATEWAY_URL", "http://sol.fake:8011/sol");
  vi.stubEnv("SOL_COOKIE_SECURE", "false");
  vi.stubEnv("SOL_PUBLIC_ORIGIN", "");
  upstream.mockReset().mockResolvedValue(Response.json({ ok: true }));
});

it("usa origen público explícito cuando Next ve host/puerto internos de Docker", async () => {
  vi.stubEnv("SOL_PUBLIC_ORIGIN", "http://127.0.0.1:13016");
  const response = await POST(request(["applications"], "POST", "http://127.0.0.1:13016"), context(["applications"]));
  expect(response.status).toBe(200);
  expect(upstream).toHaveBeenCalledOnce();
});
it("no acepta el origen interno ni externos cuando hay origen público configurado", async () => {
  vi.stubEnv("SOL_PUBLIC_ORIGIN", "https://bna.example.test");
  for (const origin of ["http://localhost:3000", "https://externo.test"]) {
    const response = await POST(request(["applications"], "POST", origin), context(["applications"]));
    expect(response.status).toBe(403);
  }
  expect(upstream).not.toHaveBeenCalled();
});
it.each(["no-es-url", "https://bna.example.test/ruta", "https://user@bna.example.test"])("rechaza configuración de origen inválida %s", async (configured) => {
  vi.stubEnv("SOL_PUBLIC_ORIGIN", configured);
  const response = await POST(request(["applications"]), context(["applications"]));
  expect(response.status).toBe(503);
  expect(upstream).not.toHaveBeenCalled();
});
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

it.each([null, "null", "https://localhost:3000", "http://externo.test"])("rechaza origen de escritura %s sin llamar upstream", async (origin) => {
  const response = await POST(request(["applications"], "POST", origin), context(["applications"]));
  expect(response.status).toBe(403);
  expect(upstream).not.toHaveBeenCalled();
});
it("rechaza segmentos de navegación y callbacks del canal navegador", async () => {
  for (const path of [["..", "health"], ["integrations", "evaluation-results"]]) {
    const response = await POST(request(path), context(path));
    expect([400, 404]).toContain(response.status);
  }
  expect(upstream).not.toHaveBeenCalled();
});
it("oculta token de login y guarda cookie HttpOnly", async () => {
  upstream.mockResolvedValue(Response.json({ token: "TOKEN-SINTETICO-E05", usuario: { rol: "ASESOR" } }));
  const response = await POST(request(["auth", "login"]), context(["auth", "login"]));
  expect(await response.json()).toEqual({ usuario: { rol: "ASESOR" } });
  expect(response.headers.get("set-cookie")).toMatch(/HttpOnly/i);
  expect(response.headers.get("set-cookie")).toMatch(/SameSite=lax/i);
  expect(response.headers.get("cache-control")).toBe("no-store");
});
it.each(["/sol", "/gateway/sol"])("conserva ruta configurada %s, credencial servidor e idempotencia", async (base) => {
  vi.stubEnv("SOL_GATEWAY_URL", "http://sol.fake:8011" + base);
  const path = ["applications", "sol-e05", "send"];
  await POST(request(path), context(path));
  const [url, init] = upstream.mock.calls[0];
  expect(url).toBe("http://sol.fake:8011" + base + "/applications/sol-e05/send");
  expect(init.headers.get("Authorization")).toBe("Bearer sesion-sintetica");
  expect(init.headers.get("X-Idempotency-Key")).toBe("operacion-e05");
  expect(init.redirect).toBe("error");
});
it("propaga 401 y borra cookie sin cachear respuesta", async () => {
  upstream.mockResolvedValue(Response.json({ detail: "Sesión vencida" }, { status: 401 }));
  const response = await GET(request(["auth", "me"], "GET"), context(["auth", "me"]));
  expect(response.status).toBe(401);
  expect(response.headers.get("set-cookie")).toContain("Max-Age=0");
  expect(response.headers.get("cache-control")).toBe("no-store");
});
it("fallo de transporte es 503 sin cuerpos remotos", async () => {
  upstream.mockRejectedValue(new Error("SECRETO-REMOTO-SINTETICO"));
  const response = await POST(request(["applications"]), context(["applications"]));
  expect(response.status).toBe(503);
  expect(await response.text()).not.toContain("SECRETO-REMOTO-SINTETICO");
});
it("no usa fallback de URL cuando falta configuración", async () => {
  vi.stubEnv("SOL_GATEWAY_URL", "");
  const response = await GET(request(["policy"], "GET"), context(["policy"]));
  expect(response.status).toBe(503);
  expect(upstream).not.toHaveBeenCalled();
});
it("no conserva cookie al cerrar sesión con upstream caído", async () => {
  upstream.mockRejectedValue(new Error("offline"));
  const response = await POST(request(["auth", "logout"]), context(["auth", "logout"]));
  expect(response.status).toBe(503);
  expect(response.headers.get("set-cookie")).toContain("Max-Age=0");
});
it("rechaza login sin token y aplica Secure cuando está configurado", async () => {
  upstream.mockResolvedValueOnce(Response.json({ usuario: { rol: "ASESOR" } }));
  const invalid = await POST(request(["auth", "login"]), context(["auth", "login"]));
  expect(invalid.status).toBe(503);
  expect(invalid.headers.get("set-cookie")).toBeNull();
  vi.stubEnv("SOL_COOKIE_SECURE", "true");
  upstream.mockResolvedValueOnce(Response.json({ token: "TOKEN-SINTETICO", usuario: { rol: "ASESOR" } }));
  const valid = await POST(request(["auth", "login"]), context(["auth", "login"]));
  expect(valid.headers.get("set-cookie")).toMatch(/; Secure/i);
});
