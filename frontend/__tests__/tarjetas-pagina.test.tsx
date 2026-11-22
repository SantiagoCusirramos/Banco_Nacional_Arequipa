import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  apiTarjetas: { get: vi.fn(), post: vi.fn(), put: vi.fn() },
  api: { get: vi.fn() },
}));
import { api, apiTarjetas } from "@/lib/api";
import TarjetasPage from "../app/tarjetas/page";

const get = vi.mocked(apiTarjetas.get);
const post = vi.mocked(apiTarjetas.post);
const put = vi.mocked(apiTarjetas.put);
const sobre = (data: unknown) => ({ data: { success: true, status_code: 200, data } });

const TARJETA = {
  id_tarjeta: "7e570001-0000-4000-8000-000000000001", bin: "004499", ultimos4: "0001",
  fecha_emision: "2026-01-15", fecha_vencimiento: "2030-01-31", estado_tarjeta: "ACTIVA", cod_cliente: "CLI000000001",
  num_cuenta: "10100000000001" as string | null, numero_enmascarado: "0044 99** **** 0001", vencimiento_mm_aa: "01/30",
};
const OTRA = {
  ...TARJETA, id_tarjeta: "7e570001-0000-4000-8000-000000000002", ultimos4: "0002",
  numero_enmascarado: "0044 99** **** 0002", estado_tarjeta: "BLOQUEADA",
};

const AUTORIZACION = {
  uuid_autorizacion: "5a1f0c3e-0000-4000-8000-000000000001", id_tarjeta: TARJETA.id_tarjeta, num_cuenta: "10100000000001",
  id_canal: "ATM", id_terminal: null, tipo_operacion: "RETIRO", monto: "150.00", estado_autorizacion: "AUTORIZADA",
  codigo_respuesta: "00", motivo_rechazo: null, aprobada: true,
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
  put.mockReset();
  perfil.mockReset();
  perfil.mockRejectedValue(new Error("sin sesión"));
});

// Lista las tarjetas del cliente y abre el detalle de la activa.
async function abrirDetalle() {
  get.mockResolvedValue(sobre([TARJETA]));
  render(<TarjetasPage />);
  escribir(screen.getByLabelText("Código del cliente"), "CLI000000001");
  await userEvent.click(screen.getByRole("button", { name: "Ver tarjetas" }));
  const [tarjeta] = await screen.findAllByRole("listitem");
  await userEvent.click(within(tarjeta).getByRole("button", { name: "Ver detalle" }));
}

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
    const config = post.mock.calls[0][2] as { headers: Record<string, string> };
    expect(config.headers["X-Idempotency-Key"]).toMatch(/^[0-9a-f-]{36}$/);
    expect(await screen.findByRole("status")).toHaveTextContent("emitida (PENDIENTE_ACTIVACION)");
  });

  it("TJ-09 Reintentar la misma emisión repite la llave; editar un dato la cambia", async () => {
    post.mockRejectedValueOnce(new AxiosError("Network Error", "ERR_NETWORK"));
    post.mockResolvedValue(sobre({ ...TARJETA, estado_tarjeta: "PENDIENTE_ACTIVACION" }));
    render(<TarjetasPage />);
    await pestana("Emitir tarjeta");
    escribir(screen.getByLabelText("Código del cliente"), "CLI000000001");
    escribir(screen.getByLabelText("Cuenta a vincular"), "10100000000001");
    const emitir = () => userEvent.click(enPantalla().getByRole("button", { name: "Emitir tarjeta" }));
    const llave = (i: number) => (post.mock.calls[i][2] as { headers: Record<string, string> }).headers["X-Idempotency-Key"];
    await emitir();
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    await emitir();
    await waitFor(() => expect(post).toHaveBeenCalledTimes(2));
    expect(llave(1)).toBe(llave(0));
    await pestana("Emitir tarjeta");
    escribir(screen.getByLabelText("Cuenta a vincular"), "10100000000002");
    await emitir();
    await waitFor(() => expect(post).toHaveBeenCalledTimes(3));
    expect(llave(2)).not.toBe(llave(1));
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
      "El desbloqueo de tarjetas solo se hace por el módulo Seguridad."));
    render(<TarjetasPage />);
    await pestana("Bloqueos y estados");
    escribir(screen.getByLabelText("Identificador de la tarjeta"), TARJETA.id_tarjeta);
    await userEvent.selectOptions(screen.getByLabelText("Nuevo estado"), "ACTIVA");
    await userEvent.click(screen.getByRole("button", { name: "Aplicar cambio" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("solo se hace por el módulo Seguridad");
    expect(post.mock.calls[0][1]).toEqual({ estado: "ACTIVA" });
  });

  it("TJ-08 Muestra en el menú quién tiene la sesión", async () => {
    // /coredb/auth/me no trae el nombre: viene de la sesión guardada al iniciar sesión.
    localStorage.setItem("bna_usuario", JSON.stringify({ id_usuario: "u1", username: "ana", nombre: "Ana Torres", rol: "OPERADOR" }));
    perfil.mockResolvedValue({ data: { id_usuario: "u1", username: "ana", rol: "OPERADOR", acciones: ["VER_TARJETA"] } });
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

  it("TJ-12 Muestra la cuenta vinculada en la lista y en el detalle", async () => {
    get.mockResolvedValue(sobre([TARJETA, { ...OTRA, num_cuenta: null }]));
    render(<TarjetasPage />);
    escribir(screen.getByLabelText("Código del cliente"), "CLI000000001");
    await userEvent.click(screen.getByRole("button", { name: "Ver tarjetas" }));
    const tarjetas = await screen.findAllByRole("listitem");
    expect(within(tarjetas[0]).getByText("Cuenta 10100000000001")).toBeInTheDocument();
    expect(within(tarjetas[1]).getByText("Cuenta sin vincular")).toBeInTheDocument();
    await userEvent.click(within(tarjetas[0]).getByRole("button", { name: "Ver detalle" }));
    expect(screen.getByText("Cuenta vinculada").nextSibling).toHaveTextContent("10100000000001");
  });

  it("TJ-13 Autoriza un retiro desde el detalle, con la cuenta vinculada y una llave", async () => {
    await abrirDetalle();
    await userEvent.click(enPantalla().getByRole("button", { name: "Autorizar" }));
    expect(screen.getByLabelText("Identificador de la tarjeta")).toHaveValue(TARJETA.id_tarjeta);
    expect(screen.getByLabelText("Cuenta a debitar")).toHaveValue("10100000000001");
    escribir(screen.getByLabelText("Monto"), "150.00");
    post.mockResolvedValue(sobre(AUTORIZACION));
    await userEvent.click(enPantalla().getByRole("button", { name: "Autorizar" }));
    await waitFor(() => expect(post).toHaveBeenCalled());
    const [ruta, cuerpo, opciones] = post.mock.calls[0];
    expect(ruta).toBe(`/${TARJETA.id_tarjeta}/autorizaciones`);
    expect(cuerpo).toEqual({ num_cuenta: "10100000000001", tipo_operacion: "RETIRO", monto: "150.00", id_canal: "ATM" });
    expect((opciones as { headers: Record<string, string> }).headers["X-Idempotency-Key"]).toMatch(/^[0-9a-f-]{36}$/);
    const resultado = await screen.findByRole("status", { name: "Resultado de la autorización" });
    expect(resultado).toHaveTextContent("AUTORIZADA");
    expect(resultado).toHaveTextContent("Aprobada");
    expect(resultado).toHaveTextContent("S/ 150.00");
  });

  it("TJ-14 Un rechazo muestra el código y su significado, sin extorno", async () => {
    await abrirDetalle();
    await userEvent.click(enPantalla().getByRole("button", { name: "Autorizar" }));
    escribir(screen.getByLabelText("Monto"), "9000.00");
    post.mockResolvedValue(sobre({
      ...AUTORIZACION, monto: "9000.00", estado_autorizacion: "RECHAZADA", codigo_respuesta: "61", aprobada: false,
      motivo_rechazo: "ERR-TAR-007: tope diario excedido (RN-TOP-001)",
    }));
    await userEvent.click(enPantalla().getByRole("button", { name: "Autorizar" }));
    const resultado = await screen.findByRole("status", { name: "Resultado de la autorización" });
    expect(resultado).toHaveTextContent("RECHAZADA");
    expect(resultado).toHaveTextContent("Excede el tope diario del canal");
    expect(screen.queryByRole("button", { name: "Extornar" })).not.toBeInTheDocument();
  });

  it("TJ-15 Extorna una autorización aprobada", async () => {
    await abrirDetalle();
    await userEvent.click(enPantalla().getByRole("button", { name: "Autorizar" }));
    escribir(screen.getByLabelText("Monto"), "150.00");
    post.mockResolvedValueOnce(sobre(AUTORIZACION));
    await userEvent.click(enPantalla().getByRole("button", { name: "Autorizar" }));
    escribir(await screen.findByLabelText("Motivo del extorno"), "El cajero no entregó el efectivo");
    post.mockResolvedValueOnce(sobre({ ...AUTORIZACION, estado_autorizacion: "EXTORNADA", codigo_respuesta: "EXT", aprobada: false }));
    await userEvent.click(screen.getByRole("button", { name: "Extornar" }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(2));
    expect(post.mock.calls[1]).toEqual([`/autorizaciones/${AUTORIZACION.uuid_autorizacion}/extorno`, { motivo: "El cajero no entregó el efectivo" }]);
    expect(await screen.findByText("EXTORNADA")).toBeInTheDocument();
    expect(screen.getByText(/el monto volvió al saldo disponible/)).toBeInTheDocument();
  });

  it("TJ-16 Asigna el PIN y no lo deja en el campo", async () => {
    await abrirDetalle();
    await userEvent.click(enPantalla().getByRole("button", { name: "Claves" }));
    const campo = screen.getByLabelText("Valor");
    expect(campo).toHaveAttribute("type", "password");
    escribir(campo, "48a21");
    expect(campo).toHaveValue("4821");
    put.mockResolvedValue(sobre(null));
    await userEvent.click(screen.getByRole("button", { name: "Asignar" }));
    await waitFor(() => expect(put).toHaveBeenCalledWith(`/${TARJETA.id_tarjeta}/credenciales/PIN_ATM`, { valor: "4821" }));
    expect(campo).toHaveValue("");
    expect(await screen.findByText(/PIN registrado/)).toBeInTheDocument();
  });

  it("TJ-17 Comprueba un PIN equivocado y muestra los intentos que quedan", async () => {
    await abrirDetalle();
    await userEvent.click(enPantalla().getByRole("button", { name: "Claves" }));
    escribir(screen.getByLabelText("Valor"), "0000");
    post.mockResolvedValue(sobre({ resultado: "FALLIDO", intentos_restantes: 1 }));
    await userEvent.click(screen.getByRole("button", { name: "Comprobar" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith(
      `/${TARJETA.id_tarjeta}/credenciales/PIN_ATM/validacion`, { valor: "0000", id_canal: "ATM" }));
    const resultado = await screen.findByRole("status", { name: "Resultado de la validación" });
    expect(resultado).toHaveTextContent("Clave incorrecta");
    expect(resultado).toHaveTextContent("Quedan 1 de 3 intentos.");
  });

  it("TJ-18 Al tercer fallo avisa que la tarjeta quedó bloqueada", async () => {
    await abrirDetalle();
    await userEvent.click(enPantalla().getByRole("button", { name: "Claves" }));
    escribir(screen.getByLabelText("Valor"), "0000");
    post.mockResolvedValue(sobre({ resultado: "FALLIDO", intentos_restantes: 0 }));
    await userEvent.click(screen.getByRole("button", { name: "Comprobar" }));
    expect(await screen.findByRole("status", { name: "Resultado de la validación" })).toHaveTextContent("la tarjeta quedó bloqueada");
  });

  it("TJ-19 La clave web pide seis dígitos", async () => {
    await abrirDetalle();
    await userEvent.click(enPantalla().getByRole("button", { name: "Claves" }));
    await userEvent.selectOptions(screen.getByLabelText("Clave"), "CLAVE_WEB");
    const campo = screen.getByLabelText("Valor");
    escribir(campo, "61524399");
    expect(campo).toHaveValue("615243");
    expect(campo).toHaveAttribute("pattern", "[0-9]{6}");
  });
});
