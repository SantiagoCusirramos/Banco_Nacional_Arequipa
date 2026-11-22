import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  apiCaptacion: { get: vi.fn(), post: vi.fn() },
  api: { get: vi.fn() },
}));
import { api, apiCaptacion } from "@/lib/api";
import CaptacionPage from "../app/captacion/page";

const get = vi.mocked(apiCaptacion.get);
const post = vi.mocked(apiCaptacion.post);
const perfil = vi.mocked(api.get);
const sobre = (data: unknown) => ({ data: { success: true, status_code: 200, data } });
const escribir = (campo: HTMLElement, valor: string) => fireEvent.change(campo, { target: { value: valor } });

const SOLICITANTE = {
  id_solicitante: "5a1c0000-0000-4000-8000-000000000001", tipo_documento: "DNI", numero_documento: "45678901",
  nombres: "Rosa", apellido_paterno: "Huamán", apellido_materno: "Ccori", celular: "958111222",
  correo: "rosa@example.com", cod_cliente: null, creado_en: "2026-11-15T15:00:00",
};
const CASO = {
  id_caso: "ca5e0000-0000-4000-8000-000000000001", id_solicitante: SOLICITANTE.id_solicitante, canal: "AGENCIA",
  id_agencia: "AQP01", producto_interes: null, estado: "INICIADO", observacion: null, motivo_cierre: null,
  cod_cliente: null, cliente_nuevo: null, id_verificacion_captacion: null, fecha_verificacion: null,
  vigente_hasta: null, creado_por: "asesor.demo", creado_en: "2026-11-15T15:00:00", cerrado_en: null,
};
const EXPEDIENTE = {
  ...CASO, solicitante: SOLICITANTE, consentimientos: [], validaciones: [], consultas: [], perfil: null,
  faltantes: ["Consentimiento TRATAMIENTO_DATOS aceptado", "Verificación OTP del celular"], listo_para_habilitar: false,
};
const HABILITADO = {
  ...EXPEDIENTE, estado: "HABILITADO", cod_cliente: "CLI000000007", cliente_nuevo: true,
  id_verificacion_captacion: "9f1d-ver", fecha_verificacion: "2026-11-15", vigente_hasta: "2026-12-15",
  faltantes: [], perfil: { puntaje: 970, calificacion: "BAJO", observacion: "Peor calificación NORMAL", fecha: "2026-11-15T15:05:00" },
};

beforeEach(() => {
  get.mockReset();
  post.mockReset();
  perfil.mockReset();
  perfil.mockResolvedValue({ data: { id_usuario: "u1", username: "asesor.demo", rol: "ASESOR", acciones: ["CREAR_CLIENTE", "MODIFICAR_CLIENTE", "VALIDAR_IDENTIDAD"] } });
});

describe("Página del módulo Captación", () => {
  it("CAP-01 Muestra la bandeja de casos", async () => {
    get.mockResolvedValue(sobre([{ ...CASO, solicitante: SOLICITANTE }]));
    render(<CaptacionPage />);
    const fila = (await screen.findByText("Rosa Huamán Ccori")).closest("tr") as HTMLElement;
    expect(within(fila).getByText("DNI 45678901")).toBeInTheDocument();
    expect(within(fila).getByText("INICIADO")).toBeInTheDocument();
    expect(get).toHaveBeenCalledWith("/casos", { params: { limite: 100 } });
  });

  it("CAP-02 Registra al solicitante, abre el caso y muestra lo que falta", async () => {
    get.mockImplementation(async (url: string) => sobre(url === "/casos" ? [] : EXPEDIENTE));
    post.mockImplementation(async (url: string) =>
      sobre(url === "/solicitantes" ? { solicitante: SOLICITANTE, duplicado: false } : CASO));
    render(<CaptacionPage />);
    await userEvent.click(within(screen.getByRole("navigation", { name: "Navegación Captación" })).getByRole("button", { name: "Nuevo solicitante" }));
    escribir(screen.getByLabelText("Número de documento"), "45678901");
    escribir(screen.getByLabelText("Nombres"), "Rosa");
    escribir(screen.getByLabelText("Apellido paterno"), "Huamán");
    escribir(screen.getByLabelText("Celular"), "958111222");
    escribir(screen.getByLabelText("Correo"), "rosa@example.com");
    await userEvent.click(screen.getByRole("button", { name: "Registrar y abrir caso" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/solicitantes", expect.objectContaining({
      numero_documento: "45678901", apellido_materno: null })));
    expect(post).toHaveBeenCalledWith("/casos", expect.objectContaining({ id_solicitante: SOLICITANTE.id_solicitante, canal: "AGENCIA" }));
    expect(await screen.findByRole("heading", { name: "Rosa Huamán Ccori" })).toBeInTheDocument();
    expect(screen.getByText("Verificación OTP del celular")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Habilitar cliente/ })).toBeDisabled();
  });

  it("CAP-03 Muestra al cliente habilitado y la referencia para Solicitud de Crédito", async () => {
    get.mockImplementation(async (url: string) => {
      if (url === "/casos") return sobre([{ ...CASO, solicitante: SOLICITANTE }]);
      if (url.endsWith("/referencia")) return sobre({ id_cliente: "CLI000000007", estado_habilitante: "HABILITADO", estado_cliente: "ACTIVO" });
      return sobre(HABILITADO);
    });
    render(<CaptacionPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Abrir" }));
    expect(await screen.findByText("CLI000000007")).toBeInTheDocument();
    expect(screen.getByText("2026-11-15 al 2026-12-15")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Ver lo que recibe Solicitud de Crédito" }));
    expect(await screen.findByText(/"estado_cliente": "ACTIVO"/)).toBeInTheDocument();
  });

  it("CAP-04 Explica por qué no se pudo habilitar", async () => {
    const listo = { ...EXPEDIENTE, estado: "APROBADO", faltantes: [], listo_para_habilitar: true };
    get.mockImplementation(async (url: string) => sobre(url === "/casos" ? [{ ...CASO, solicitante: SOLICITANTE }] : listo));
    post.mockRejectedValue(new AxiosError("Request failed", "ERR_BAD_REQUEST", undefined, undefined, {
      status: 400, statusText: "", headers: {}, config: {} as never,
      data: { success: false, status_code: 400, error_code: "ERR-CAP-CLIENTE-NO-ACTIVO",
        message: "El documento ya es de un cliente en estado BLOQUEADO", details: {} },
    }));
    render(<CaptacionPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Abrir" }));
    await userEvent.click(await screen.findByRole("button", { name: /Habilitar cliente/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("BLOQUEADO");
    expect(post).toHaveBeenCalledWith(`/casos/${CASO.id_caso}/habilitar`);
  });

  it("CAP-05 Pide iniciar sesión si no hay sesión", async () => {
    perfil.mockRejectedValue(new Error("sin sesión"));
    get.mockResolvedValue(sobre([]));
    render(<CaptacionPage />);
    expect(await screen.findByText(/Tu sesión no está iniciada/)).toBeInTheDocument();
  });
});
