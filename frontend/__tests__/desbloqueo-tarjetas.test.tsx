import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  apiSeguridad: { get: vi.fn(), post: vi.fn() },
  api: { get: vi.fn() },
}));
import { api, apiSeguridad } from "@/lib/api";
import DesbloqueoPage from "../app/tarjetas/desbloqueo/page";

const get = vi.mocked(apiSeguridad.get);
const post = vi.mocked(apiSeguridad.post);
const perfil = vi.mocked(api.get);
const escribir = (campo: HTMLElement, valor: string) => fireEvent.change(campo, { target: { value: valor } });

const ID = "7e570001-0000-4000-8000-000000000002";
const BLOQUEO = {
  id_historial: 41, estado_nuevo: "BLOQUEADA", motivo: "Bloqueo solicitado por el cliente en Home Banking",
  origen: "OPERADOR", fecha_hora: "2026-11-21T15:04:00Z",
};
const FICHA = {
  id_tarjeta: ID, bin: "004499", ultimos4: "1904", fecha_emision: "2026-01-15", fecha_vencimiento: "2030-01-31",
  estado_tarjeta: "BLOQUEADA", cod_cliente: "CLI000000003", num_cuenta: "18250122240575",
  numero_enmascarado: "004499******1904", desbloqueable: true, bloqueo: BLOQUEO,
  historial: [BLOQUEO, { id_historial: 40, estado_nuevo: "ACTIVA", motivo: null, origen: "OPERADOR",
    fecha_hora: "2026-11-20T10:00:00Z" }],
};
const ACTIVA = { ...FICHA, estado_tarjeta: "ACTIVA", desbloqueable: false, bloqueo: null };
const RESPUESTA = {
  id_tarjeta: ID, bin: "004499", ultimos4: "1904", fecha_emision: "2026-01-15", fecha_vencimiento: "2030-01-31",
  estado_tarjeta: "ACTIVA", cod_cliente: "CLI000000003", num_cuenta: "18250122240575",
  cambio: { id_historial: 42, estado_nuevo: "ACTIVA", motivo: "El titular se presentó con su DNI en agencia",
    origen: "SEGURIDAD", fecha_hora: "2026-11-21T16:30:00Z", estado_anterior: "BLOQUEADA", actor: "operador.rev42" },
};
const errorSeguridad = (status: number, code: string, message: string) =>
  new AxiosError("Request failed", "ERR_BAD_REQUEST", undefined, undefined, {
    status, statusText: "", headers: {}, config: {} as never, data: { error: { code, message } },
  });

function conRol(rol: string, acciones: string[]) {
  perfil.mockResolvedValue({ data: { id_usuario: "u1", username: "operador.rev42", rol, acciones } });
}
const OPERADOR = ["VER_TARJETA", "BLOQUEAR_TARJETA", "CREAR_TARJETA"];

beforeEach(() => {
  get.mockReset();
  post.mockReset();
  perfil.mockReset();
  localStorage.setItem("bna_access_token", "jwt");
});

async function abrirFicha(ficha: typeof FICHA | typeof ACTIVA = FICHA) {
  conRol("OPERADOR", OPERADOR);
  get.mockResolvedValue({ data: ficha });
  render(<DesbloqueoPage />);
  escribir(await screen.findByLabelText("Número de identificación de la tarjeta"), ID);
  await userEvent.click(screen.getByRole("button", { name: "Buscar tarjeta" }));
  await screen.findByRole("region", { name: "Tarjeta 004499******1904" });
}

async function prepararConfirmacion() {
  await abrirFicha();
  escribir(screen.getByLabelText("Motivo del desbloqueo"), "El titular se presentó con su DNI en agencia");
  await userEvent.click(screen.getByLabelText(/Verifiqué la identidad del titular/));
  await userEvent.click(screen.getByRole("button", { name: "Revisar desbloqueo" }));
  return screen.findByRole("dialog", { name: "Confirmar el desbloqueo" });
}

describe("Desbloqueo de tarjetas (personal autorizado)", () => {
  it("DT-01 sin sesión pide iniciarla y no muestra el buscador", async () => {
    perfil.mockRejectedValue(new AxiosError("401", "ERR_BAD_REQUEST", undefined, undefined, {
      status: 401, statusText: "", headers: {}, config: {} as never, data: {},
    }));
    render(<DesbloqueoPage />);
    expect(await screen.findByRole("link", { name: "Iniciar sesión" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Código del cliente")).not.toBeInTheDocument();
  });

  it("DT-02 un rol sin permiso lo sabe al entrar, no al enviar", async () => {
    conRol("ASESOR", ["VER_CLIENTE"]);
    render(<DesbloqueoPage />);
    expect(await screen.findByText(/Esta pantalla es para operadores y administradores/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Código del cliente")).not.toBeInTheDocument();
    expect(get).not.toHaveBeenCalled();
  });

  it("DT-03 busca por cliente y muestra el estado de cada tarjeta; al revisar, el motivo, quién y cuándo", async () => {
    conRol("OPERADOR", OPERADOR);
    get.mockResolvedValueOnce({ data: [
      { ...FICHA, desbloqueable: undefined, bloqueo: undefined, historial: undefined },
      { ...ACTIVA, id_tarjeta: "7e570001-0000-4000-8000-000000000009", ultimos4: "0009", numero_enmascarado: "004499******0009" },
    ] });
    render(<DesbloqueoPage />);
    escribir(await screen.findByLabelText("Código del cliente"), "cli000000003");
    await userEvent.click(screen.getByRole("button", { name: "Buscar tarjetas" }));
    expect(get).toHaveBeenCalledWith("/tarjetas", { params: { cod_cliente: "CLI000000003" } });
    const lista = await screen.findByRole("list", { name: "Tarjetas del cliente" });
    expect(within(lista).getByText("004499******1904")).toBeInTheDocument();
    expect(within(lista).getByText("Bloqueada")).toBeInTheDocument();
    expect(within(lista).getByText("Activa")).toBeInTheDocument();

    get.mockResolvedValueOnce({ data: FICHA });
    await userEvent.click(within(lista).getByRole("button", { name: "Revisar la tarjeta terminada en 1904" }));
    expect(get).toHaveBeenLastCalledWith(`/tarjetas/${ID}`);
    await screen.findByRole("region", { name: "Tarjeta 004499******1904" });
    const bloqueo = screen.getByRole("region", { name: "Bloqueo vigente" });
    expect(within(bloqueo).getByText("Bloqueo solicitado por el cliente en Home Banking")).toBeInTheDocument();
    expect(within(bloqueo).getByText("Personal del banco")).toBeInTheDocument();
    expect(within(bloqueo).getByText("21/11/2026 10:04")).toBeInTheDocument(); // hora de Arequipa
    // Sin jerga técnica en pantalla.
    expect(document.body.textContent).not.toMatch(/OPERADOR|UUID|COREDB|BNA-|TARJETA_/);
  });

  it("DT-04 una tarjeta activa no ofrece desbloqueo", async () => {
    await abrirFicha(ACTIVA);
    expect(screen.getByText(/no está bloqueada/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Motivo del desbloqueo")).not.toBeInTheDocument();
  });

  it("DT-05 exige motivo y verificación de identidad antes de revisar", async () => {
    await abrirFicha();
    const revisar = screen.getByRole("button", { name: "Revisar desbloqueo" });
    await userEvent.click(revisar);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByText(/Escribe el motivo/)).toBeInTheDocument();
    escribir(screen.getByLabelText("Motivo del desbloqueo"), "El titular se presentó con su DNI en agencia");
    await userEvent.click(revisar);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByText(/Confirma que verificaste la identidad/)).toBeInTheDocument();
  });

  it("DT-06 la confirmación pide los últimos 4 dígitos; cancelar no envía nada", async () => {
    const dialogo = await prepararConfirmacion();
    expect(within(dialogo).getByText(/volverá a aceptarse en el cajero/)).toBeInTheDocument();
    const confirmar = within(dialogo).getByRole("button", { name: "Desbloquear tarjeta" });
    expect(confirmar).toBeDisabled();
    escribir(within(dialogo).getByLabelText("Últimos 4 dígitos de la tarjeta"), "1234");
    expect(confirmar).toBeDisabled();
    escribir(within(dialogo).getByLabelText("Últimos 4 dígitos de la tarjeta"), "1904");
    expect(confirmar).toBeEnabled();
    await userEvent.click(within(dialogo).getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(post).not.toHaveBeenCalled();
  });

  it("DT-07 desbloquea una sola vez y el comprobante usa los datos del servidor", async () => {
    let soltar: (v: unknown) => void = () => {};
    post.mockReturnValue(new Promise((r) => { soltar = r; }) as never);
    const dialogo = await prepararConfirmacion();
    escribir(within(dialogo).getByLabelText("Últimos 4 dígitos de la tarjeta"), "1904");
    const confirmar = within(dialogo).getByRole("button", { name: "Desbloquear tarjeta" });
    await userEvent.click(confirmar);
    await userEvent.click(confirmar);
    expect(post).toHaveBeenCalledTimes(1);
    expect(post).toHaveBeenCalledWith(`/tarjetas/${ID}/desbloqueo`, { motivo: "El titular se presentó con su DNI en agencia" });
    soltar({ data: RESPUESTA });
    const comprobante = await screen.findByRole("region", { name: "Comprobante de desbloqueo" });
    const texto = comprobante.textContent ?? "";
    expect(texto).toContain("42"); // número de operación del historial
    expect(texto).toContain("21/11/2026 11:30");
    expect(texto).toContain("004499******1904");
    expect(texto).toContain("CLI000000003");
    expect(texto).toContain("Bloqueada");
    expect(texto).toContain("Activa");
    expect(texto).toContain("operador.rev42");
    expect(texto).toContain("El titular se presentó con su DNI en agencia");
    expect(texto).toMatch(/bitácora/);
  });

  it("DT-08 una respuesta incompleta o distinta no se muestra como desbloqueo", async () => {
    post.mockResolvedValue({ data: { ...RESPUESTA, cambio: undefined } });
    const dialogo = await prepararConfirmacion();
    escribir(within(dialogo).getByLabelText("Últimos 4 dígitos de la tarjeta"), "1904");
    get.mockResolvedValue({ data: FICHA });
    await userEvent.click(within(dialogo).getByRole("button", { name: "Desbloquear tarjeta" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/No se pudo confirmar el desbloqueo/);
    expect(screen.queryByRole("region", { name: "Comprobante de desbloqueo" })).not.toBeInTheDocument();
  });

  it("DT-09 si ya no estaba bloqueada, lo dice y vuelve a leer la tarjeta", async () => {
    post.mockRejectedValue(errorSeguridad(409, "TARJETA_NO_BLOQUEADA", "La tarjeta no está bloqueada."));
    const dialogo = await prepararConfirmacion();
    escribir(within(dialogo).getByLabelText("Últimos 4 dígitos de la tarjeta"), "1904");
    get.mockResolvedValue({ data: ACTIVA });
    await userEvent.click(within(dialogo).getByRole("button", { name: "Desbloquear tarjeta" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/ya no está bloqueada/);
    await waitFor(() => expect(get).toHaveBeenLastCalledWith(`/tarjetas/${ID}`));
    const ficha = await screen.findByRole("region", { name: "Tarjeta 004499******1904" });
    expect(await within(ficha).findByText(/no está bloqueada/)).toBeInTheDocument();
  });

  it("DT-10 sin respuesta del servidor no supone nada: avisa y vuelve a leer antes de reintentar", async () => {
    post.mockRejectedValue(new AxiosError("Network Error", "ERR_NETWORK"));
    const dialogo = await prepararConfirmacion();
    escribir(within(dialogo).getByLabelText("Últimos 4 dígitos de la tarjeta"), "1904");
    get.mockClear().mockResolvedValue({ data: FICHA });
    await userEvent.click(within(dialogo).getByRole("button", { name: "Desbloquear tarjeta" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/No sabemos si se desbloqueó/);
    await waitFor(() => expect(get).toHaveBeenCalledWith(`/tarjetas/${ID}`));
  });

  it("DT-11 un permiso negado se explica sin códigos", async () => {
    post.mockRejectedValue(errorSeguridad(403, "PERMISO_DENEGADO", "PERMISO_DENEGADO · correlación x"));
    const dialogo = await prepararConfirmacion();
    escribir(within(dialogo).getByLabelText("Últimos 4 dígitos de la tarjeta"), "1904");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Desbloquear tarjeta" }));
    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(/Tu usuario no tiene permiso para desbloquear tarjetas/);
    expect(alerta.textContent).not.toMatch(/PERMISO_DENEGADO|correlación/);
  });
});
