import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  apiCaptacion: { get: vi.fn(), post: vi.fn() },
  api: { get: vi.fn() },
}));
import { api, apiCaptacion } from "@/lib/api";
import CaptacionPage from "../app/captacion/page";

const get = vi.mocked(apiCaptacion.get);
const perfil = vi.mocked(api.get);
const sobre = (data: unknown) => ({ data: { success: true, status_code: 200, data } });

const SOLICITANTE = {
  id_solicitante: "5a1c0000-0000-4000-8000-000000000001", tipo_documento: "DNI", numero_documento: "45678901",
  nombres: "Rosa", apellido_paterno: "Huamán", apellido_materno: "Ccori", celular: "958111222",
  correo: "rosa@example.com", cod_cliente: null, creado_en: "2026-11-15T15:00:00+00:00",
};
const CASO = {
  id_caso: "ca5e0000-0000-4000-8000-000000000001", id_solicitante: SOLICITANTE.id_solicitante, canal: "AGENCIA",
  id_agencia: "AQP01", producto_interes: null, estado: "INICIADO", observacion: null, motivo_cierre: null,
  cod_cliente: null, cliente_nuevo: null, id_verificacion_captacion: null, fecha_verificacion: null,
  vigente_hasta: null, creado_por: "asesor.demo", creado_en: "2026-11-15T15:00:00+00:00", cerrado_en: null,
};
const EXPEDIENTE = {
  ...CASO, solicitante: SOLICITANTE, consentimientos: [], validaciones: [], consultas: [], perfil: null,
  faltantes: ["Consentimiento TRATAMIENTO_DATOS aceptado"], listo_para_habilitar: false,
};

beforeEach(() => {
  get.mockReset();
  perfil.mockReset();
  perfil.mockResolvedValue({ data: { id_usuario: "u1", username: "asesor.demo", rol: "ASESOR", acciones: ["CREAR_CLIENTE"] } });
});

describe("Captación: fecha de apertura", () => {
  it("CAP-PU-01 la fecha con zona horaria de la respuesta real no dice «Invalid Date»", async () => {
    get.mockImplementation(async (url: string) => sobre(url === "/casos" ? [{ ...CASO, solicitante: SOLICITANTE }] : EXPEDIENTE));
    render(<CaptacionPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Abrir" }));
    await waitFor(() => expect(screen.getByText(/Abierto 15 nov/)).toBeInTheDocument());
    expect(screen.queryByText(/Invalid Date/)).not.toBeInTheDocument();
  });

  it("CAP-PU-02 si no hay fecha de apertura, no se muestra nada en su lugar", async () => {
    const sinFecha = { ...EXPEDIENTE, creado_en: null };
    get.mockImplementation(async (url: string) => sobre(url === "/casos"
      ? [{ ...CASO, creado_en: null, solicitante: SOLICITANTE }] : sinFecha));
    render(<CaptacionPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Abrir" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Rosa Huamán Ccori" })).toBeInTheDocument());
    expect(screen.queryByText(/Invalid Date/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Abierto/)).not.toBeInTheDocument();
  });
});
