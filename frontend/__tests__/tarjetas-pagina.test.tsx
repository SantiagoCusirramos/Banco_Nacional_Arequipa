import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  apiCore: { get: vi.fn(), post: vi.fn() },
}));
import { apiCore } from "@/lib/api";
import TarjetasPage from "../app/tarjetas/page";
import { enmascarada, vencimientoMmAa } from "@/lib/tarjetas";

const get = vi.mocked(apiCore.get);
const post = vi.mocked(apiCore.post);

const TARJETA = {
  id_tarjeta: "7e570001-0000-4000-8000-000000000001", bin: "004499", ultimos4: "0001",
  fecha_emision: "2026-01-15", fecha_vencimiento: "2030-01-31", estado_tarjeta: "ACTIVA", cod_cliente: "CLI000000001",
};
const OTRA = { ...TARJETA, id_tarjeta: "7e570001-0000-4000-8000-000000000002", ultimos4: "0002", estado_tarjeta: "BLOQUEADA" };

const pestana = (nombre: RegExp) => userEvent.click(screen.getByRole("button", { name: nombre }));
const errorCoreDb = (status: number, code: string, message: string) =>
  new AxiosError("Request failed", "ERR_BAD_REQUEST", undefined, undefined, {
    status, statusText: "", headers: {}, config: {} as never, data: { error: { code, message } },
  });

beforeEach(() => {
  get.mockReset();
  post.mockReset();
});

describe("Formato de tarjetas", () => {
  it("TJ-00 Enmascara la tarjeta y muestra el vencimiento como MM/AA", () => {
    expect(enmascarada(TARJETA)).toBe("0044 99•• •••• 0001");
    expect(vencimientoMmAa("2030-01-31")).toBe("01/30");
  });
});

describe("Página del módulo Tarjetas", () => {
  it("TJ-01 Lista las tarjetas de un cliente por su código", async () => {
    get.mockResolvedValue({ data: [TARJETA, OTRA] });
    render(<TarjetasPage />);
    await userEvent.type(screen.getByLabelText("Código del cliente"), "cli000000001");
    await userEvent.click(screen.getByRole("button", { name: "Ver tarjetas" }));
    await waitFor(() =>
      expect(get).toHaveBeenCalledWith("/coredb/tarjetas", { params: { cod_cliente: "CLI000000001" } }));
    const filas = await screen.findAllByRole("row");
    expect(filas).toHaveLength(3);
    expect(within(filas[1]).getByText("0044 99•• •••• 0001")).toBeInTheDocument();
    expect(within(filas[2]).getByText("BLOQUEADA")).toBeInTheDocument();
    expect(within(filas[1]).getByText("01/30")).toBeInTheDocument();
  });

  it("TJ-02 Avisa cuando el cliente no tiene tarjetas", async () => {
    get.mockResolvedValue({ data: [] });
    render(<TarjetasPage />);
    await userEvent.type(screen.getByLabelText("Código del cliente"), "CLI000000009");
    await userEvent.click(screen.getByRole("button", { name: "Ver tarjetas" }));
    expect(await screen.findByRole("status")).toHaveTextContent("El cliente no tiene tarjetas.");
  });

  it("TJ-03 Muestra el mensaje de COREDB si el cliente no existe", async () => {
    get.mockRejectedValue(errorCoreDb(404, "CLIENTE_NO_ENCONTRADO", "El cliente NOEXISTE no existe."));
    render(<TarjetasPage />);
    await userEvent.type(screen.getByLabelText("Código del cliente"), "NOEXISTE");
    await userEvent.click(screen.getByRole("button", { name: "Ver tarjetas" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("El cliente NOEXISTE no existe.");
  });

  it("TJ-04 Ver una tarjeta desde la lista abre su detalle", async () => {
    get.mockResolvedValue({ data: [TARJETA] });
    render(<TarjetasPage />);
    await userEvent.type(screen.getByLabelText("Código del cliente"), "CLI000000001");
    await userEvent.click(screen.getByRole("button", { name: "Ver tarjetas" }));
    await userEvent.click(await screen.findByRole("button", { name: "Ver" }));
    expect(screen.getByRole("heading", { name: "Tarjeta 0044 99•• •••• 0001" })).toBeInTheDocument();
    expect(screen.getByText(TARJETA.id_tarjeta)).toBeInTheDocument();
  });

  it("TJ-05 Emite una tarjeta con un token en lugar del PAN", async () => {
    post.mockResolvedValue({ data: { ...TARJETA, estado_tarjeta: "PENDIENTE_ACTIVACION" } });
    render(<TarjetasPage />);
    await pestana(/3\. Emitir/);
    await userEvent.type(screen.getByLabelText("Código del cliente"), "cli000000001");
    await userEvent.type(screen.getByLabelText("Cuenta a vincular"), "10100000000001");
    await userEvent.click(screen.getByRole("button", { name: "Emitir tarjeta" }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    const [ruta, cuerpo] = post.mock.calls[0] as [string, Record<string, string>];
    expect(ruta).toBe("/coredb/tarjetas");
    expect(cuerpo).toMatchObject({ cod_cliente: "CLI000000001", num_cuenta: "10100000000001", bin: "004499" });
    expect(cuerpo.pan_token).toMatch(/^[0-9a-f]{32}$/);
    expect(cuerpo.ultimos4).toMatch(/^[0-9]{4}$/);
    expect(await screen.findByRole("status")).toHaveTextContent("emitida (PENDIENTE_ACTIVACION)");
  });

  it("TJ-06 Bloquea una tarjeta con su motivo", async () => {
    post.mockResolvedValue({ data: { ...TARJETA, estado_tarjeta: "BLOQUEADA" } });
    render(<TarjetasPage />);
    await pestana(/4\. Bloquear/);
    await userEvent.type(screen.getByLabelText("Identificador de la tarjeta"), TARJETA.id_tarjeta);
    await userEvent.type(screen.getByLabelText("Motivo"), "Robo reportado");
    await userEvent.click(screen.getByRole("button", { name: "Aplicar cambio" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith(
      `/coredb/tarjetas/${TARJETA.id_tarjeta}/estado`, { estado: "BLOQUEADA", motivo: "Robo reportado" }));
    expect(await screen.findByRole("status")).toHaveTextContent("quedó BLOQUEADA");
  });

  it("TJ-07 Un desbloqueo rechazado muestra el aviso de COREDB", async () => {
    post.mockRejectedValue(errorCoreDb(403, "BNA-DESBLOQUEO",
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
