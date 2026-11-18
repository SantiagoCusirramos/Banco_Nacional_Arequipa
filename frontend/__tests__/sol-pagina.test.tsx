import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import SolicitudPage from "../app/solicitud-credito/page";

const user = { username: "asesor.bna", nombre: "Asesor de prueba", rol: "ASESOR" };
const policy = { version: "TEST-E05", estado_aprobacion: "PROPUESTO", producto_nombre: "Crédito de prueba", monedas: ["PEN"], monto_minimo: "1000.00", monto_maximo: "50000.00", plazo_minimo_meses: 6, plazo_maximo_meses: 60, tea: "0.22", dias_por_periodo: 30, nota: "Solo prueba", integracion: "REAL" };
const client = { id_cliente: "cliente-e05", numero_documento: "DOC-SINTETICO", nombres: "Persona", apellido_paterno: "Sintetica", apellido_materno: "Prueba", estado_cliente: "ACTIVO", estado_habilitante: "HABILITADO", vigente_hasta: "2099-01-01", id_caso: "caso-e05", id_verificacion: "ver-e05" };
const snapshot = { cliente: client, condiciones: { id_cliente: client.id_cliente, monto_solicitado: "15000.00", moneda: "PEN", plazo_meses: 12, destino_credito: "Mejoras de prueba", fecha_base: "2026-11-14", pago_doble: false, garantias: [] }, fiadores: [], politica: policy, calendario: { estado: "PRELIMINAR", cuotas: [], cuota_referencial: "100.00", intereses_totales: "10.00", total_pagar: "15010.00" } };
const summary = { id: "sol-e05", codigo: "SOL-E05", estado: "BORRADOR", version: 1, revision: 1, cliente_nombre: "Persona Sintetica Prueba", documento: "DOC-SINTETICO", monto: "15000.00", moneda: "PEN", plazo: 12, actualizado: "2026-11-14T15:00:00Z" };
let detail = { ...summary, versiones: [{ numero: 1, congelada: false, expediente: snapshot }], eventos: [], resultados: [], envios: [] as { version: number; id_operacion: string; acuse: string; estado_transporte: string; fecha: string }[] };
let profile = user;
let override: (path: string, init?: RequestInit) => Response | Promise<Response> | undefined;
const api = vi.fn(async (input: string, init?: RequestInit) => {
  const path = input.replace("/api/solicitud-credito/", "");
  const custom = override(path, init);
  if (custom) return custom;
  if (path === "auth/me") return Response.json(profile);
  if (path === "policy") return Response.json(policy);
  if (path === "clients") return Response.json([client]);
  if (path.startsWith("applications?")) return Response.json({ items: [detail], total: 1, limit: 50, offset: 0, estados: { [detail.estado]: 1 } });
  if (path === "applications/sol-e05") return Response.json(detail);
  throw new Error("Ruta de prueba no preparada: " + path);
});
beforeEach(() => {
  detail = { ...summary, versiones: [{ numero: 1, congelada: false, expediente: snapshot }], eventos: [], resultados: [], envios: [] };
  profile = user; policy.integracion = "REAL"; override = () => undefined; api.mockClear(); vi.stubGlobal("fetch", api);
});
afterEach(() => vi.unstubAllGlobals());
async function open() {
  render(<SolicitudPage />);
  await userEvent.click(await screen.findByRole("button", { name: "Abrir SOL-E05" }));
  await screen.findByRole("heading", { name: "Condiciones de la versión 1" });
}
it("muestra errores funcionales objeto sin [object Object]", async () => {
  override = (path) => path.endsWith("/send") ? Response.json({ detail: { mensaje: "Reintenta con la operación pendiente.", idOperacion: "operacion-e05" } }, { status: 409 }) : undefined;
  await open();
  await userEvent.click(screen.getByRole("button", { name: /Enviar a Evaluación/ }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Reintenta con la operación pendiente.");
});
it("recupera operación pendiente tras recarga y no anuncia recepción EVA", async () => {
  detail.versiones[0].congelada = true;
  detail.envios = [{ version: 1, id_operacion: "pendiente-e05", acuse: "", estado_transporte: "PENDIENTE", fecha: "2026-11-14T15:00:00Z" }];
  override = (path) => path.endsWith("/send") ? Response.json({ ...detail, pendiente_envio: true }, { status: 202 }) : undefined;
  await open();
  expect(screen.getByRole("button", { name: "Editar borrador" })).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: "Reintentar envío pendiente" }));
  expect(await screen.findByRole("status")).toHaveTextContent("pendiente de confirmación");
  const sent = api.mock.calls.find(([url]) => url.endsWith("/send"))!;
  expect((sent[1]!.headers as Record<string, string>)["X-Idempotency-Key"]).toBe("pendiente-e05");
});
it("sesión caducada abandona expediente y muestra acceso", async () => {
  await open();
  override = () => Response.json({ detail: "Sesión vencida" }, { status: 401 });
  await userEvent.click(screen.getByRole("button", { name: "Actualizar estado" }));
  expect(await screen.findByRole("heading", { name: "Bienvenido a BNA" })).toBeInTheDocument();
  expect(screen.queryByText("SOL-E05")).not.toBeInTheDocument();
});
it.each(["SUPERVISOR", "AUDITOR"])("%s consulta métricas sin controles de asesor", async (rol) => {
  profile = { ...user, rol };
  override = (path) => path === "ops/metrics" ? Response.json({ operaciones: [{ operacion: "GET /sol/applications", muestras: 3, p95_ms: 12 }] }) : undefined;
  render(<SolicitudPage />);
  await screen.findByRole("button", { name: "Abrir SOL-E05" });
  expect(screen.queryByRole("button", { name: "Nueva solicitud" })).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Integraciones" }));
  await userEvent.click(screen.getByRole("button", { name: "Actualizar métricas" }));
  expect(await screen.findByText(/GET \/sol\/applications: 3 muestras/)).toBeInTheDocument();
  // Sin base propia: ni pendientes locales ni bajas de usuario (los usuarios están en COREDB).
  expect(api.mock.calls.some(([url]) => url.includes("ops/pending") || url.includes("/admin/users/"))).toBe(false);
  expect(screen.queryByRole("button", { name: "Deshabilitar usuario" })).not.toBeInTheDocument();
});
it("crea, previsualiza y guarda borrador sin ejecutar envío", async () => {
  override = (path, init) => path === "preview" ? Response.json(snapshot) : path === "applications" && init?.method === "POST" ? Response.json(detail, { status: 201 }) : undefined;
  render(<SolicitudPage />);
  await userEvent.click(await screen.findByRole("button", { name: "Nueva solicitud" }));
  await userEvent.click(screen.getByRole("radio"));
  await userEvent.click(screen.getByRole("button", { name: "Continuar" }));
  fireEvent.change(screen.getByLabelText("Monto solicitado"), { target: { value: "15000" } });
  fireEvent.change(screen.getByLabelText("Destino del crédito"), { target: { value: "Mejoras de prueba" } });
  await userEvent.click(screen.getByRole("button", { name: "Continuar" }));
  await userEvent.click(screen.getByRole("button", { name: "Calcular y revisar" }));
  await userEvent.click(await screen.findByRole("button", { name: "Guardar borrador" }));
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Borrador guardado"));
  expect(api.mock.calls.some(([url]) => url.endsWith("/send"))).toBe(false);
});
it("asesor no ve operaciones administrativas y error de contrato bloquea reenvío", async () => {
  detail.versiones[0].congelada = true;
  detail.envios = [{ version: 1, id_operacion: "error-e05", estado_transporte: "ERROR_CONTRATO", acuse: "", fecha: "2026-11-14T15:00:00Z" }];
  await open();
  expect(screen.getByRole("button", { name: "Envío requiere revisión" })).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: "Integraciones" }));
  expect(screen.queryByRole("button", { name: "Actualizar métricas" })).not.toBeInTheDocument();
});
it("evita doble click mientras el envío está en curso", async () => {
  let finish!: (response: Response) => void;
  override = (path) => path.endsWith("/send") ? new Promise<Response>((resolve) => { finish = resolve; }) : undefined;
  await open();
  await userEvent.dblClick(screen.getByRole("button", { name: /Enviar a Evaluación/ }));
  expect(api.mock.calls.filter(([url]) => url.endsWith("/send"))).toHaveLength(1);
  finish(Response.json({ ...detail, pendiente_envio: true }, { status: 202 }));
  expect(await screen.findByRole("status")).toHaveTextContent("pendiente");
});
it("login y logout manejan sesión sin recibir token en el navegador", async () => {
  let loggedIn = false;
  override = (path) => path === "auth/me" && !loggedIn ? Response.json({ detail: "Inicia sesión" }, { status: 401 }) : path === "auth/login" ? (loggedIn = true, Response.json({ usuario: user })) : path === "auth/logout" ? Response.json({ ok: true }) : undefined;
  render(<SolicitudPage />);
  await screen.findByRole("heading", { name: "Bienvenido a BNA" });
  fireEvent.change(screen.getByLabelText("Usuario"), { target: { value: "asesora" } });
  fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: "clave-sintetica" } });
  await userEvent.click(screen.getByRole("button", { name: "Ingresar al portal" }));
  await screen.findByRole("button", { name: "Abrir SOL-E05" });
  await userEvent.click(screen.getByRole("button", { name: "Cerrar sesión" }));
  expect(await screen.findByRole("heading", { name: "Bienvenido a BNA" })).toBeInTheDocument();
  expect(screen.getByLabelText("Contraseña")).toHaveValue("");
});
it("las garantías se eligen del catálogo de la base", async () => {
  render(<SolicitudPage />);
  await userEvent.click(await screen.findByRole("button", { name: "Nueva solicitud" }));
  await userEvent.click(screen.getByRole("radio"));
  await userEvent.click(screen.getByRole("button", { name: "Continuar" }));
  fireEvent.change(screen.getByLabelText("Monto solicitado"), { target: { value: "15000" } });
  fireEvent.change(screen.getByLabelText("Destino del crédito"), { target: { value: "Mejoras de prueba" } });
  await userEvent.click(screen.getByRole("button", { name: "Continuar" }));
  await userEvent.click(screen.getByRole("button", { name: "Agregar" }));
  const opciones = Array.from(document.querySelectorAll("select option")).map((o) => o.textContent);
  expect(opciones).toEqual(expect.arrayContaining(["HIPOTECARIA", "MOBILIARIA", "PRENDARIA"]));
  expect(opciones).not.toContain("PERSONAL");
});
