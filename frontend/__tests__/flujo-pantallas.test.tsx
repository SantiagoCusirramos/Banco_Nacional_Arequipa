import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { AxiosResponse } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ params: new URLSearchParams() }));

vi.mock("next/navigation", () => ({
  useSearchParams: () => mocks.params,
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/",
}));
vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  apiCuentas: { get: vi.fn(), post: vi.fn() },
  apiCaptacion: { get: vi.fn(), post: vi.fn() },
  apiEvaluacion: { get: vi.fn(), post: vi.fn() },
  apiCobranza: { get: vi.fn(), post: vi.fn() },
  apiTarjetas: { get: vi.fn(), post: vi.fn(), put: vi.fn() },
  api: { get: vi.fn() },
}));
vi.mock("@/lib/auth", async (original) => {
  const actual = await original<typeof import("@/lib/auth")>();
  return { ...actual, obtenerMiPerfil: vi.fn(), cerrarSesion: vi.fn() };
});

import { api, apiCuentas, apiCaptacion, apiEvaluacion } from "@/lib/api";
import { obtenerMiPerfil, type Usuario } from "@/lib/auth";
import CuentaPage from "../app/cuenta/page";
import CaptacionPage from "../app/captacion/page";
import TarjetasPage from "../app/tarjetas/page";
import BilleteraPage from "../app/billetera/page";
import EvaluacionPage from "../app/evaluacion/page";
import PagarCuotaPage from "../app/pagar-cuota/page";
import SolicitudPage from "../app/solicitud-credito/page";

const profile = (acciones: string[]): Usuario => ({
  id_usuario: "u-1", username: "ana", nombre: "Ana Demo", rol: "OPERADOR", acciones,
});
const sobre = (data: unknown) => ({ success: true, status_code: 200, data });
/** Respuesta mínima de los clientes HTTP: basta con `data` para estas pantallas. */
const respuesta = <T,>(data: T) => ({ data }) as unknown as AxiosResponse<T>;

const CUENTA = {
  num_cuenta: "10100000000001", cci: "00219100000000000101", moneda: "PEN", regimen: "INDIVIDUAL",
  estado_cuenta: "ACTIVA", saldo_contable: "300.00", saldo_disponible: "300.00", id_agencia: "AQP01",
  titulares: ["CLI000000007"],
};

beforeEach(() => {
  vi.clearAllMocks();
  mocks.params = new URLSearchParams();
  vi.mocked(obtenerMiPerfil).mockResolvedValue(profile([
    "VER_CUENTA", "CREAR_CUENTA", "REGISTRAR_MOVIMIENTO", "VER_TARJETA", "CREAR_TARJETA",
    "CREAR_CLIENTE", "MODIFICAR_CLIENTE", "VALIDAR_IDENTIDAD", "EVALUAR_CREDITO",
    "CONSULTAR_DEUDA", "REGISTRAR_PAGO", "AFILIAR_BILLETERA", "CREAR_SOLICITUD_CREDITO",
  ]));
  vi.mocked(api.get).mockResolvedValue(respuesta(profile([])));
  vi.mocked(apiCuentas.get).mockResolvedValue(respuesta(sobre([])));
  vi.mocked(apiCuentas.post).mockResolvedValue(respuesta(sobre(CUENTA)));
  vi.mocked(apiCaptacion.get).mockResolvedValue(respuesta(sobre([])));
  vi.mocked(apiEvaluacion.get).mockResolvedValue(respuesta([]));
  const fetchMock = vi.fn(async (input: string) => {
    const path = String(input);
    if (path.includes("/auth/me")) return Response.json({ username: "ana", nombre: "Ana Demo", rol: "ASESOR" });
    if (path.includes("/applications")) return Response.json({ items: [], total: 0, limit: 50, offset: 0, estados: {} });
    if (path.includes("/clients")) return Response.json([]);
    if (path.includes("/policy")) return Response.json({});
    return Response.json({});
  });
  vi.stubGlobal("fetch", fetchMock);
});

describe("Parámetros de entrada entre pantallas", () => {
  it("FP-01 Cuenta precarga el cliente que viene de Captación", async () => {
    mocks.params = new URLSearchParams("codCliente=cli000000007");
    render(<CuentaPage />);
    expect(await screen.findByLabelText("Código del cliente titular")).toHaveValue("CLI000000007");
  });

  it("FP-02 Cuenta abre la pestaña indicada por el parámetro tab", async () => {
    mocks.params = new URLSearchParams("tab=consulta");
    render(<CuentaPage />);
    expect(await screen.findByPlaceholderText("Número de cuenta...")).toBeInTheDocument();
  });

  it("FP-03 Tarjetas precarga cliente, cuenta y pestaña de emisión", async () => {
    mocks.params = new URLSearchParams("codCliente=cli7&numCuenta=10100000000001&tab=emision");
    render(<TarjetasPage />);
    expect(await screen.findByLabelText("Código del cliente")).toHaveValue("CLI7");
    expect(screen.getByLabelText("Cuenta a vincular")).toHaveValue("10100000000001");
  });

  it("FP-04 Billetera precarga el cliente y la cuenta del desembolso", async () => {
    mocks.params = new URLSearchParams("codCliente=cli7&numCuenta=10100000000001");
    render(<BilleteraPage />);
    expect(await screen.findByLabelText("Código del cliente")).toHaveValue("CLI7");
    expect(screen.getByLabelText("Número de cuenta en soles")).toHaveValue("10100000000001");
  });
});

describe("Enlaces de siguiente paso", () => {
  it("FP-05 Cuenta ofrece emitir tarjeta con el cliente y la cuenta en la URL", async () => {
    render(<CuentaPage />);
    await userEvent.type(screen.getByLabelText("Número de cuenta (hasta 20 caracteres)"), "10100000000001");
    await userEvent.type(screen.getByLabelText("Código de Cuenta Interbancario (CCI - 20 dígitos)"), "00219100000000000101");
    await userEvent.type(screen.getByLabelText("Código del cliente titular"), "CLI000000007");
    await userEvent.type(screen.getByLabelText("Agencia"), "AQP01");
    await userEvent.click(screen.getByRole("button", { name: "Crear cuenta" }));
    const enlace = await screen.findByRole("link", { name: /Emitir tarjeta para esta cuenta/i });
    expect(enlace).toHaveAttribute("href", "/tarjetas?tab=emision&codCliente=CLI000000007&numCuenta=10100000000001");
  });

  it("FP-06 Captación ofrece abrir cuenta con el cliente habilitado en la URL", async () => {
    const expediente = {
      id_caso: "ca-1", estado: "HABILITADO", canal: "AGENCIA", creado_en: "2026-11-15T15:00:00",
      cod_cliente: "CLI000000007", solicitante: { nombres: "Rosa", apellido_paterno: "Huamán", apellido_materno: "Ccori", tipo_documento: "DNI", numero_documento: "45678901" },
      consentimientos: [], validaciones: [], consultas: [], perfil: null, faltantes: [], listo_para_habilitar: false,
    };
    vi.mocked(apiCaptacion.get).mockImplementation(async (url: string) =>
      respuesta(sobre(url === "/casos" ? [{ ...expediente, solicitante: expediente.solicitante }] : expediente)));
    render(<CaptacionPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Abrir" }));
    const enlace = await screen.findByRole("link", { name: /Abrir cuenta/i });
    expect(enlace).toHaveAttribute("href", "/cuenta?codCliente=CLI000000007&tab=apertura");
  });
});

describe("Barra con texto en cada pantalla", () => {
  const pantallas: [string, () => React.JSX.Element][] = [
    ["Cuentas", () => <CuentaPage />],
    ["Captación", () => <CaptacionPage />],
    ["Tarjetas", () => <TarjetasPage />],
    ["Billetera", () => <BilleteraPage />],
    ["Evaluación", () => <EvaluacionPage />],
    ["Pagar cuota", () => <PagarCuotaPage />],
    ["Solicitud de crédito", () => <SolicitudPage />],
  ];

  it.each(pantallas)("FP-07 %s muestra Volver al portal y Cerrar sesión con texto", async (_nombre, renderPage) => {
    render(renderPage());
    expect(await screen.findByText(/Volver al portal/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Cerrar sesión/i).length).toBeGreaterThan(0);
  });
});
