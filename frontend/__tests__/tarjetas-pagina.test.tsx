import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  apiTarjetas: { get: vi.fn(), post: vi.fn() },
}));
import { apiTarjetas } from "@/lib/api";
import TarjetasPage from "../app/tarjetas/page";

const get = vi.mocked(apiTarjetas.get);
const post = vi.mocked(apiTarjetas.post);
const sobre = (data: unknown) => ({ data: { success: true, status_code: 200, data } });

const TARJETA = {
  id_tarjeta: "7e570001-0000-4000-8000-000000000001", bin: "004499", ultimos4: "0001",
  fecha_emision: "2026-01-15", fecha_vencimiento: "2030-01-31", estado_tarjeta: "ACTIVA", cod_cliente: "CLI000000001",
  numero_enmascarado: "0044 99** **** 0001", vencimiento_mm_aa: "01/30",
};
const OTRA = {
  ...TARJETA, id_tarjeta: "7e570001-0000-4000-8000-000000000002", ultimos4: "0002",
  numero_enmascarado: "0044 99** **** 0002", estado_tarjeta: "BLOQUEADA",
};

const pestana = (nombre: RegExp) => userEvent.click(screen.getByRole("button", { name: nombre }));
// Error con el formato ITIL-02 de TARJETAS.
const errorTarjetas = (status: number, error_code: string, message: string) =>
  new AxiosError("Request failed", "ERR_BAD_REQUEST", undefined, undefined, {
    status, statusText: "", headers: {}, config: {} as never,
    data: { success: false, status_code: status, error_code, message, details: {} },
  });

beforeEach(() => {
  get.mockReset();
  post.mockReset();
});

describe("Página del módulo Tarjetas", () => {
  it("TJ-01 Lista las tarjetas de un cliente por su código", async () => {
    get.mockResolvedValue(sobre([TARJETA, OTRA]));
    render(<TarjetasPage />);
    await userEvent.type(screen.getByLabelText("Código del cliente"), "cli000000001");
    await userEvent.click(screen.getByRole("button", { name: "Ver tarjetas" }));
    await waitFor(() => expect(get).toHaveBeenCalledWith("/cliente/CLI000000001"));
    const filas = await screen.findAllByRole("row");
    expect(filas).toHaveLength(3);
    expect(within(filas[1]).getByText("0044 99** **** 0001")).toBeInTheDocument();
    expect(within(filas[1]).getByText("01/30")).toBeInTheDocument();
    expect(within(filas[2]).getByText("BLOQUEADA")).toBeInTheDocument();
  });

  it("TJ-02 Avisa cuando el cliente no tiene tarjetas", async () => {
    get.mockResolvedValue(sobre([]));
    render(<TarjetasPage />);
    await userEvent.type(screen.getByLabelText("Código del cliente"), "CLI000000009");
    await userEvent.click(screen.getByRole("button", { name: "Ver tarjetas" }));
    expect(await screen.findByRole("status")).toHaveTextContent("El cliente no tiene tarjetas.");
  });

  it("TJ-03 Muestra el mensaje del servicio si el cliente no existe", async () => {
    get.mockRejectedValue(errorTarjetas(404, "ERR-CLI-NO-ENCONTRADO", "El cliente NOEXISTE no existe."));
    render(<TarjetasPage />);
    await userEvent.type(screen.getByLabelText("Código del cliente"), "NOEXISTE");
    await userEvent.click(screen.getByRole("button", { name: "Ver tarjetas" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("El cliente NOEXISTE no existe.");
  });

  it("TJ-04 Ver una tarjeta desde la lista abre su detalle", async () => {
    get.mockResolvedValue(sobre([TARJETA]));
    render(<TarjetasPage />);
    await userEvent.type(screen.getByLabelText("Código del cliente"), "CLI000000001");
    await userEvent.click(screen.getByRole("button", { name: "Ver tarjetas" }));
    await userEvent.click(await screen.findByRole("button", { name: "Ver" }));
    expect(screen.getByRole("heading", { name: "Tarjeta 0044 99** **** 0001" })).toBeInTheDocument();
    expect(screen.getByText(TARJETA.id_tarjeta)).toBeInTheDocument();
  });

  it("TJ-05 Emite una tarjeta sin enviar ningún dato del PAN", async () => {
    post.mockResolvedValue(sobre({ ...TARJETA, estado_tarjeta: "PENDIENTE_ACTIVACION" }));
    render(<TarjetasPage />);
    await pestana(/3\. Emitir/);
    await userEvent.type(screen.getByLabelText("Código del cliente"), "cli000000001");
    await userEvent.type(screen.getByLabelText("Cuenta a vincular"), "10100000000001");
    await userEvent.click(screen.getByRole("button", { name: "Emitir tarjeta" }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    const [ruta, cuerpo] = post.mock.calls[0] as [string, Record<string, string>];
    expect(ruta).toBe("/emision");
    expect(Object.keys(cuerpo).sort()).toEqual(["bin", "cod_cliente", "fecha_vencimiento", "num_cuenta"]);
    expect(cuerpo).toMatchObject({ cod_cliente: "CLI000000001", num_cuenta: "10100000000001", bin: "004499" });
    expect(await screen.findByRole("status")).toHaveTextContent("emitida (PENDIENTE_ACTIVACION)");
  });

  it("TJ-06 Bloquea una tarjeta con su motivo", async () => {
    post.mockResolvedValue(sobre({ ...TARJETA, estado_tarjeta: "BLOQUEADA" }));
    render(<TarjetasPage />);
    await pestana(/4\. Bloquear/);
    await userEvent.type(screen.getByLabelText("Identificador de la tarjeta"), TARJETA.id_tarjeta);
    await userEvent.type(screen.getByLabelText("Motivo"), "Robo reportado");
    await userEvent.click(screen.getByRole("button", { name: "Aplicar cambio" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith(
      `/${TARJETA.id_tarjeta}/estado`, { estado: "BLOQUEADA", motivo: "Robo reportado" }));
    expect(await screen.findByRole("status")).toHaveTextContent("quedó BLOQUEADA");
  });

  it("TJ-07 Un desbloqueo rechazado muestra el aviso del servicio", async () => {
    post.mockRejectedValue(errorTarjetas(403, "ERR-TAR-DESBLOQUEO-NO-PERMITIDO",
      "El desbloqueo de tarjetas no está disponible: pendiente de un cliente de Seguridad."));
    render(<TarjetasPage />);
    await pestana(/4\. Bloquear/);
    await userEvent.type(screen.getByLabelText("Identificador de la tarjeta"), TARJETA.id_tarjeta);
    await userEvent.selectOptions(screen.getByLabelText("Nuevo estado"), "ACTIVA");
    await userEvent.click(screen.getByRole("button", { name: "Aplicar cambio" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("pendiente de un cliente de Seguridad");
    expect(post.mock.calls[0][1]).toEqual({ estado: "ACTIVA" });
  });
});
