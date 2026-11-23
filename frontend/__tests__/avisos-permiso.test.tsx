import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => "/",
}));
vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  apiCuentas: { get: vi.fn(), post: vi.fn() },
  apiCaptacion: { get: vi.fn(), post: vi.fn() },
  apiEvaluacion: { get: vi.fn(), post: vi.fn() },
  apiCobranza: { get: vi.fn(), post: vi.fn() },
  apiTarjetas: { get: vi.fn(), post: vi.fn(), put: vi.fn() },
  apiSeguridad: { get: vi.fn(), post: vi.fn() },
  api: { get: vi.fn() },
}));
vi.mock("@/lib/auth", async (original) => {
  const actual = await original<typeof import("@/lib/auth")>();
  return { ...actual, obtenerMiPerfil: vi.fn(), cerrarSesion: vi.fn() };
});
import { api, apiCuentas, apiCaptacion, apiEvaluacion, apiCobranza, apiTarjetas } from "@/lib/api";
import * as auth from "@/lib/auth";
import type { Usuario } from "@/lib/auth";
import CuentaPage from "../app/cuenta/page";
import CaptacionPage from "../app/captacion/page";
import EvaluacionPage from "../app/evaluacion/page";
import PagarCuotaPage from "../app/pagar-cuota/page";
import SolicitudCreditoPage from "../app/solicitud-credito/page";

const perfil = vi.mocked(api.get);
const miPerfil = vi.mocked(auth.obtenerMiPerfil);
const sobre = (data: unknown) => ({ data: { success: true, status_code: 200, data } });
const fetchMock = vi.fn();

function conPerfil(rol: string, acciones: string[]) {
  const usuario: Usuario = { id_usuario: "u1", username: "ana", nombre: "Ana", rol, acciones };
  perfil.mockResolvedValue({ data: usuario });
  miPerfil.mockResolvedValue(usuario);
}

beforeEach(() => {
  perfil.mockReset();
  miPerfil.mockReset();
  vi.mocked(apiCuentas.get).mockReset();
  vi.mocked(apiCuentas.post).mockReset();
  vi.mocked(apiCaptacion.get).mockReset();
  vi.mocked(apiCaptacion.post).mockReset();
  vi.mocked(apiEvaluacion.get).mockReset();
  vi.mocked(apiEvaluacion.post).mockReset();
  vi.mocked(apiCobranza.get).mockReset();
  vi.mocked(apiCobranza.post).mockReset();
  vi.mocked(apiTarjetas.get).mockReset();
  vi.mocked(apiTarjetas.post).mockReset();
  vi.mocked(apiTarjetas.put).mockReset();
  localStorage.setItem("bna_access_token", "jwt");
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

describe("Avisos de permiso por pantalla", () => {
  it("AP-01 Cuentas: rol sin VER_CUENTA ve aviso y no llama al servidor", async () => {
    conPerfil("ASESOR", ["CREAR_CLIENTE"]);
    render(<CuentaPage />);
    expect(await screen.findByText(/Esta pantalla no está disponible para tu rol/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Volver al portal/i })).toHaveAttribute("href", "/");
    expect(apiCuentas.get).not.toHaveBeenCalled();
    expect(apiCuentas.post).not.toHaveBeenCalled();
  });

  it("AP-02 Captación: rol sin permisos de captación ve aviso y no llama al servidor", async () => {
    conPerfil("ANALISTA", ["EVALUAR_CREDITO", "VER_CREDITO"]);
    vi.mocked(apiCaptacion.get).mockResolvedValue(sobre([]));
    render(<CaptacionPage />);
    expect(await screen.findByText(/Esta pantalla no está disponible para tu rol/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Volver al portal/i })).toBeInTheDocument();
    await waitFor(() => expect(apiCaptacion.get).not.toHaveBeenCalled());
  });

  it("AP-03 Evaluación: rol sin VER_CREDITO ve aviso y no llama al servidor", async () => {
    conPerfil("ASESOR", ["CREAR_SOLICITUD_CREDITO"]);
    render(<EvaluacionPage />);
    expect(await screen.findByText(/Esta pantalla no está disponible para tu rol/i)).toBeInTheDocument();
    expect(apiEvaluacion.get).not.toHaveBeenCalled();
  });

  it("AP-04 Pagar cuota: rol sin CONSULTAR_DEUDA/REGISTRAR_PAGO ve aviso", async () => {
    conPerfil("ANALISTA", ["EVALUAR_CREDITO"]);
    render(<PagarCuotaPage />);
    expect(await screen.findByText(/Esta pantalla no está disponible para tu rol/i)).toBeInTheDocument();
    expect(apiCobranza.get).not.toHaveBeenCalled();
  });

  it("AP-05 Solicitud de crédito: rol sin crear solicitud ve aviso en vez del botón", async () => {
    // Perfil real del portal (COREDB /coredb/auth/me): sin CREAR_SOLICITUD_CREDITO.
    const sinPermiso: Usuario = { id_usuario: "u1", username: "ana", nombre: "Ana", rol: "OPERADOR",
      acciones: ["VER_CUENTA", "CREAR_CUENTA"] };
    miPerfil.mockResolvedValue(sinPermiso);
    fetchMock.mockImplementation(async (url: string) => {
      if (String(url).includes("/auth/me")) return { ok: true, json: async () => ({ nombre: "Ana", username: "ana", rol: "AUDITOR" }) };
      if (String(url).includes("/policy")) return { ok: true, json: async () => ({}) };
      if (String(url).includes("/applications")) return { ok: true, json: async () => [] };
      if (String(url).includes("/clients")) return { ok: true, json: async () => [] };
      return { ok: true, json: async () => ({}) };
    });
    render(<SolicitudCreditoPage />);
    expect(await screen.findByText(/Esta pantalla no está disponible para tu rol/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Iniciar solicitud/i })).not.toBeInTheDocument();
  });
});
