import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  apiTarjetas: { get: vi.fn(), post: vi.fn() },
  api: { get: vi.fn() },
}));
import { api, apiTarjetas } from "@/lib/api";
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

const perfil = vi.mocked(api.get);
const pestana = (nombre: string) =>
  userEvent.click(within(screen.getByRole("navigation", { name: "Navegación Tarjetas" })).getByRole("button", { name: nombre }));
const enPantalla = () => within(screen.getByRole("main"));
// Como en page.test.tsx: escribir de una vez y no tecla por tecla, que en el CI no alcanza el tiempo.
const escribir = (campo: HTMLElement, valor: string) => fireEvent.change(campo, { target: { value: valor } });
// Error con el formato ITIL-02 de TARJETAS.
const errorTarjetas = (status: number, error_code: string, message: string) =>
  new AxiosError("Request failed", "ERR_BAD_REQUEST", undefined, undefined, {
    status, statusText: "", headers: {}, config: {} as never,
    data: { success: false, status_code: status, error_code, message, details: {} },
  });

beforeEach(() => {
  get.mockReset();
  post.mockReset();
  perfil.mockReset();
  perfil.mockRejectedValue(new Error("sin sesión"));
});

describe("Página del módulo Tarjetas", () => {
  it("TJ-01 Lista las tarjetas de un cliente por su código", async () => {
    get.mockResolvedValue(sobre([TARJETA, OTRA]));
    render(<TarjetasPage />);
    escribir(screen.getByLabelText("Código del cliente"), "cli000000001");
    await userEvent.click(screen.getByRole("button", { name: "Ver tarjetas" }));
    await waitFor(() => expect(get).toHaveBeenCalledWith("/cliente/CLI000000001"));
    const tarjetas = await screen.findAllByRole("listitem");
    expect(tarjetas).toHaveLength(2);
    expect(within(tarjetas[0]).getByText("0044 99** **** 0001")).toBeInTheDocument();
    expect(within(tarjetas[0]).getByText("01/30")).toBeInTheDocument();
    expect(within(tarjetas[1]).getByText("BLOQUEADA")).toBeInTheDocument();
    // Resumen: 2 tarjetas, 1 activa y 1 bloqueada
    expect(screen.getByText("Total de tarjetas").nextSibling).toHaveTextContent("2");
    expect(screen.getByText("Activas").nextSibling).toHaveTextContent("1");
    expect(screen.getByText("Fuera de uso").nextSibling).toHaveTextContent("1");
  });

  it("TJ-02 Avisa cuando el cliente no tiene tarjetas", async () => {
    get.mockResolvedValue(sobre([]));
    render(<TarjetasPage />);
    escribir(screen.getByLabelText("Código del cliente"), "CLI000000009");
    await userEvent.click(screen.getByRole("button", { name: "Ver tarjetas" }));
    expect(await screen.findByRole("status")).toHaveTextContent("El cliente no tiene tarjetas.");
  });

  it("TJ-03 Muestra el mensaje del servicio si el cliente no existe", async () => {
    get.mockRejectedValue(errorTarjetas(404, "ERR-CLI-NO-ENCONTRADO", "El cliente NOEXISTE no existe."));
    render(<TarjetasPage />);
    escribir(screen.getByLabelText("Código del cliente"), "NOEXISTE");
    await userEvent.click(screen.getByRole("button", { name: "Ver tarjetas" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("El cliente NOEXISTE no existe.");
  });

  it("TJ-04 Ver una tarjeta desde la lista abre su detalle", async () => {
    get.mockResolvedValue(sobre([TARJETA]));
    render(<TarjetasPage />);
    escribir(screen.getByLabelText("Código del cliente"), "CLI000000001");
    await userEvent.click(screen.getByRole("button", { name: "Ver tarjetas" }));
    await userEvent.click(await screen.findByRole("button", { name: "Ver detalle" }));
    expect(screen.getByRole("heading", { name: "Tarjeta 0044 99** **** 0001" })).toBeInTheDocument();
    expect(screen.getByText(TARJETA.id_tarjeta)).toBeInTheDocument();
    // Una tarjeta activa ofrece bloquearla, y eso lleva al cambio de estado con BLOQUEADA elegido.
    await userEvent.click(screen.getByRole("button", { name: "Bloquear" }));
    expect(screen.getByLabelText("Identificador de la tarjeta")).toHaveValue(TARJETA.id_tarjeta);
    expect(screen.getByLabelText("Nuevo estado")).toHaveValue("BLOQUEADA");
  });

  it("TJ-05 Emite una tarjeta sin enviar ningún dato del PAN", async () => {
    post.mockResolvedValue(sobre({ ...TARJETA, estado_tarjeta: "PENDIENTE_ACTIVACION" }));
    render(<TarjetasPage />);
    await pestana("Emitir tarjeta");
    escribir(screen.getByLabelText("Código del cliente"), "cli000000001");
    escribir(screen.getByLabelText("Cuenta a vincular"), "10100000000001");
    await userEvent.click(enPantalla().getByRole("button", { name: "Emitir tarjeta" }));
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
    await pestana("Bloqueos y estados");
    escribir(screen.getByLabelText("Identificador de la tarjeta"), TARJETA.id_tarjeta);
    escribir(screen.getByLabelText("Motivo"), "Robo reportado");
    await userEvent.click(screen.getByRole("button", { name: "Aplicar cambio" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith(
      `/${TARJETA.id_tarjeta}/estado`, { estado: "BLOQUEADA", motivo: "Robo reportado" }));
    expect(await screen.findByRole("status")).toHaveTextContent("quedó BLOQUEADA");
  });

  it("TJ-07 Un desbloqueo rechazado muestra el aviso del servicio", async () => {
    post.mockRejectedValue(errorTarjetas(403, "ERR-TAR-DESBLOQUEO-NO-PERMITIDO",
      "El desbloqueo de tarjetas no está disponible: pendiente de un cliente de Seguridad."));
    render(<TarjetasPage />);
    await pestana("Bloqueos y estados");
    escribir(screen.getByLabelText("Identificador de la tarjeta"), TARJETA.id_tarjeta);
    await userEvent.selectOptions(screen.getByLabelText("Nuevo estado"), "ACTIVA");
    await userEvent.click(screen.getByRole("button", { name: "Aplicar cambio" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("pendiente de un cliente de Seguridad");
    expect(post.mock.calls[0][1]).toEqual({ estado: "ACTIVA" });
  });

  it("TJ-08 Muestra en el menú quién tiene la sesión", async () => {
    // /coredb/auth/me no trae el nombre: viene de la sesión guardada al iniciar sesión.
    localStorage.setItem("bna_usuario", JSON.stringify({ id_usuario: "u1", username: "ana", nombre: "Ana Torres", rol: "OPERADOR" }));
    perfil.mockResolvedValue({ data: { id_usuario: "u1", username: "ana", rol: "OPERADOR" } });
    render(<TarjetasPage />);
    expect(await screen.findByText("Ana Torres")).toBeInTheDocument();
    expect(screen.getByText("OPERADOR")).toBeInTheDocument();
    expect(perfil).toHaveBeenCalledWith("/coredb/auth/me");
    expect(screen.getByRole("link", { name: "Cerrar sesión" })).toHaveAttribute("href", "/login");
  });

  it("TJ-10 Sin sesión pide iniciarla en lugar de mostrar el error técnico", async () => {
    perfil.mockRejectedValue(errorTarjetas(401, "TOKEN_REQUERIDO", "Falta el encabezado Authorization: Bearer <token>."));
    render(<TarjetasPage />);
    const aviso = await screen.findByRole("alert");
    expect(aviso).toHaveTextContent("Tu sesión no está iniciada o ya venció.");
    expect(aviso).not.toHaveTextContent("Authorization");
    expect(within(aviso).getByRole("link", { name: "Iniciar sesión" })).toHaveAttribute("href", "/login");
  });

  it("TJ-11 Si la sesión vence durante una consulta, pide iniciarla otra vez", async () => {
    get.mockRejectedValue(errorTarjetas(401, "ERR-TAR-TOKEN-EXPIRADO", "El token venció."));
    render(<TarjetasPage />);
    escribir(screen.getByLabelText("Código del cliente"), "CLI000000001");
    await userEvent.click(screen.getByRole("button", { name: "Ver tarjetas" }));
    const aviso = await screen.findByRole("alert");
    expect(aviso).toHaveTextContent("Tu sesión no está iniciada o ya venció.");
    expect(screen.queryByText("El token venció.")).not.toBeInTheDocument();
  });
});
