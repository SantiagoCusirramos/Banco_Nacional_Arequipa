import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Home from "../app/page";

// El frontend no debe llamar al backend real en las pruebas
vi.mock("@/lib/api", () => ({
  api: { post: vi.fn(), get: vi.fn(), patch: vi.fn(), defaults: { baseURL: "http://localhost:8000" } },
}));
import { api } from "@/lib/api";

const post = vi.mocked(api.post);
const get = vi.mocked(api.get);
const patch = vi.mocked(api.patch);

const cuentaBase = {
  num_cuenta: "20261025123456",
  moneda: "PEN",
  regimen: "LIBRE",
  estado_cuenta: "ACTIVA",
  saldo_contable: "0.00",
  saldo_disponible: "0.00",
  saldo_retenido: "0.00",
  fecha_apertura: "2026-10-25T10:00:00",
  id_agencia: "ag-1",
  id_producto_ahorro: "prod-1",
  titulares: [{ id_cliente: "cli-1", rol_titular: "TITULAR" }],
};

const clientesDisponibles = [
  { id_cliente: "cli-1", cod_tipo_documento: "DNI", numero_documento: "11111111", nombres: "Ana", apellido_paterno: "Pérez", apellido_materno: null, fecha_nacimiento: null, numero_celular: "999999999", correo_electronico: null, estado_cliente: "ACTIVO", fecha_registro: null },
  { id_cliente: "cli-2", cod_tipo_documento: "DNI", numero_documento: "22222222", nombres: "Luis", apellido_paterno: "Rojas", apellido_materno: null, fecha_nacimiento: null, numero_celular: "988888888", correo_electronico: null, estado_cliente: "ACTIVO", fecha_registro: null },
];

const nav = () => screen.getByRole("navigation", { name: "Navegación principal" });
const irA = (nombre: RegExp) => userEvent.click(within(nav()).getByRole("button", { name: nombre }));

function errorHttp(status: number, data: unknown) {
  const err = new AxiosError("fail", "ERR_BAD_REQUEST");
  err.response = { status, data, statusText: "", headers: {}, config: {} as never };
  return err;
}

beforeEach(() => {
  post.mockReset();
  get.mockReset();
  patch.mockReset();
  get.mockImplementation((url, config) => {
    const ruta = String(url);
    if (ruta === "/core/catalogos/agencias") {
      return Promise.resolve({ data: [{ id_agencia: "ag-1", nombre: "Agencia Central", direccion: "Arequipa" }] });
    }
    if (ruta === "/core/catalogos/productos-ahorro") {
      return Promise.resolve({ data: [{ id_producto_ahorro: "prod-1", nombre: "Ahorro Clásico", moneda: "PEN", tasa_tea: 1.5 }] });
    }
    if (ruta === "/core/clientes") {
      const params = (config as { params?: { documento?: string } } | undefined)?.params;
      const documento = params?.documento ?? "";
      return Promise.resolve({ data: clientesDisponibles.filter((cliente) => cliente.numero_documento.includes(documento)) });
    }
    return Promise.resolve({ data: cuentaBase });
  });
});

// ======================================================
// POST /core/cuentas — Crear cuenta
// ======================================================
describe("Crear cuenta", () => {
  const abrir = async () => {
    render(<Home />);
    await irA(/Crear cuenta/);
    await screen.findByRole("option", { name: /Ahorro Clásico/ });
  };
  const buscarYSeleccionarCliente = async (label: string, idCliente: string) => {
    const documento = idCliente === "cli-1" ? "11111111" : "22222222";
    const idSelector = label === "Buscar cliente titular" ? "id_cliente" : "titular_2";
    const etiquetaSeleccion = label.replace("Buscar ", "") + " seleccionado";
    await userEvent.type(screen.getByLabelText(label), documento);
    await userEvent.click(screen.getByRole("button", { name: "Buscar " + idSelector }));
    await userEvent.selectOptions(await screen.findByLabelText(etiquetaSeleccion), idCliente);
  };
  const llenar = async (cliente = "cli-1", producto = "prod-1", agencia = "ag-1") => {
    await buscarYSeleccionarCliente("Buscar cliente titular", cliente);
    await userEvent.selectOptions(screen.getByLabelText("Producto de ahorro"), producto);
    await userEvent.selectOptions(screen.getByLabelText("Agencia"), agencia);
  };
  const enviar = () => userEvent.click(screen.getByRole("button", { name: /^Crear cuenta/ }));

  it("CC-01 Muestra el formulario con sus campos y el régimen LIBRE por defecto", async () => {
    await abrir();
    expect(screen.getByRole("heading", { level: 1, name: "Crear cuenta" })).toBeInTheDocument();
    expect(screen.getByLabelText("Buscar cliente titular")).toBeInTheDocument();
    expect(screen.getByLabelText("Producto de ahorro")).toBeInTheDocument();
    expect(screen.getByLabelText("Agencia")).toBeInTheDocument();
    expect(screen.getByLabelText("Régimen")).toHaveValue("LIBRE");
    expect(screen.getByLabelText("Régimen")).toHaveTextContent(/PROGRAMADO.*INFANTIL.*CTS.*A_PLAZO/);
  });

  it("CC-02 Con campos vacíos muestra errores y no llama al backend", async () => {
    await abrir();
    await enviar();
    expect(await screen.findByText("Selecciona el cliente titular.")).toBeInTheDocument();
    expect(screen.getByText("Selecciona un producto de ahorro.")).toBeInTheDocument();
    expect(screen.getByText("Selecciona una agencia.")).toBeInTheDocument();
    expect(post).not.toHaveBeenCalled();
  });

  it("CC-03 Rechaza campos con solo espacios", async () => {
    await abrir();
    await userEvent.type(screen.getByLabelText("Buscar cliente titular"), "   ");
    await userEvent.click(screen.getByRole("button", { name: "Buscar id_cliente" }));
    await enviar();
    expect(await screen.findByText("Selecciona el cliente titular.")).toBeInTheDocument();
    expect(post).not.toHaveBeenCalled();
  });

  it("CC-04 Envía POST /core/cuentas sin 'titulares' cuando solo hay un titular", async () => {
    post.mockResolvedValue({ data: cuentaBase });
    await abrir();
    await llenar();
    await userEvent.selectOptions(screen.getByLabelText("Régimen"), "CTS");
    await enviar();
    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    const [url, body, config] = post.mock.calls[0] as [string, Record<string, unknown>, { headers: Record<string, string> }];
    expect(url).toBe("/core/cuentas");
    expect(body).toMatchObject({ id_cliente: "cli-1", id_producto_ahorro: "prod-1", id_agencia: "ag-1", regimen: "CTS", actor: "portal-web" });
    expect(body.titulares).toBeUndefined();
    expect(body.correlation_id).toBeTruthy();
    expect(config.headers["x-correlation-id"]).toBe(body.correlation_id);
  });

  it("CC-05 Tras crear muestra la cuenta, el aviso y las acciones siguientes", async () => {
    post.mockResolvedValue({ data: cuentaBase });
    await abrir();
    await llenar();
    await enviar();
    expect(await screen.findByText("20261025123456")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Cuenta 20261025123456 creada correctamente.");
    expect(screen.getByText("ACTIVA")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Abrir otra cuenta" })).toBeInTheDocument();
  });

  it("CC-06 'Abrir otra cuenta' devuelve el formulario vacío", async () => {
    post.mockResolvedValue({ data: cuentaBase });
    await abrir();
    await llenar();
    await enviar();
    await userEvent.click(await screen.findByRole("button", { name: "Abrir otra cuenta" }));
    expect(screen.getByLabelText("Buscar cliente titular")).toHaveValue("");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("CC-07 Muestra el mensaje de negocio del backend cuando falla (404 cliente)", async () => {
    post.mockRejectedValue(errorHttp(404, { error: { code: "CLIENTE_NO_ENCONTRADO", message: "Cliente cli-1 no existe." } }));
    await abrir();
    await llenar();
    await enviar();
    expect(await screen.findByRole("alert")).toHaveTextContent("Cliente cli-1 no existe. (CLIENTE_NO_ENCONTRADO)");
    // el formulario conserva lo escrito para corregirlo
    expect(screen.getByLabelText("cliente titular seleccionado")).toHaveValue("cli-1");
  });

  it("CC-08 Muestra aviso de conexión si el backend no responde", async () => {
    post.mockRejectedValue(new AxiosError("Network Error", "ERR_NETWORK"));
    await abrir();
    await llenar();
    await enviar();
    expect(await screen.findByRole("alert")).toHaveTextContent("No se pudo conectar con el servidor");
  });

  it("CC-09 Errores 422 de validación de FastAPI se muestran legibles", async () => {
    post.mockRejectedValue(errorHttp(422, { detail: [{ loc: ["body", "id_agencia"], msg: "Field required" }] }));
    await abrir();
    await llenar();
    await enviar();
    expect(await screen.findByRole("alert")).toHaveTextContent("Datos inválidos en «id_agencia»");
  });

  it("CC-10 Cuenta mancomunada exige al menos dos titulares (RGN-16)", async () => {
    await abrir();
    await llenar();
    await userEvent.selectOptions(screen.getByLabelText("Rol del cliente principal"), "MANCOMUNADO");
    await enviar();
    expect(await screen.findByText(/requiere al menos dos titulares/)).toBeInTheDocument();
    expect(post).not.toHaveBeenCalled();
  });

  it("CC-11 Mancomunada con segundo titular envía la lista completa de titulares", async () => {
    post.mockResolvedValue({ data: { ...cuentaBase, titulares: [{ id_cliente: "cli-1", rol_titular: "MANCOMUNADO" }, { id_cliente: "cli-2", rol_titular: "MANCOMUNADO" }] } });
    await abrir();
    await llenar();
    await userEvent.selectOptions(screen.getByLabelText("Rol del cliente principal"), "MANCOMUNADO");
    await userEvent.click(screen.getByRole("button", { name: /Agregar titular/ }));
    await buscarYSeleccionarCliente("Buscar titular 2", "cli-2");
    await userEvent.selectOptions(screen.getByLabelText("Rol del titular 2"), "MANCOMUNADO");
    await enviar();
    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    expect((post.mock.calls[0][1] as { titulares: unknown }).titulares).toEqual([
      { id_cliente: "cli-1", rol_titular: "MANCOMUNADO" },
      { id_cliente: "cli-2", rol_titular: "MANCOMUNADO" },
    ]);
  });

  it("CC-12 No permite repetir el mismo cliente como titular", async () => {
    await abrir();
    await llenar();
    await userEvent.click(screen.getByRole("button", { name: /Agregar titular/ }));
    await buscarYSeleccionarCliente("Buscar titular 2", "cli-1");
    await enviar();
    expect(await screen.findByText("Este cliente ya figura como titular.")).toBeInTheDocument();
    expect(post).not.toHaveBeenCalled();
  });

  it("CC-13 Se puede quitar un titular adicional", async () => {
    await abrir();
    await userEvent.click(screen.getByRole("button", { name: /Agregar titular/ }));
    expect(screen.getByLabelText("Buscar titular 2")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Quitar titular 2" }));
    expect(screen.queryByLabelText("Buscar titular 2")).not.toBeInTheDocument();
  });

  it("CC-14 Cambiar de pestaña y volver deja el formulario limpio", async () => {
    await abrir();
    await userEvent.type(screen.getByLabelText("Buscar cliente titular"), "cli-9");
    await irA(/Resumen/);
    await irA(/Crear cuenta/);
    expect(screen.getByLabelText("Buscar cliente titular")).toHaveValue("");
  });
});

// ======================================================
// GET + PATCH /core/cuentas/{num_cuenta} — Modificar cuenta
// ======================================================
describe("Modificar cuenta", () => {
  const abrir = async () => {
    render(<Home />);
    await irA(/Modificar cuenta/);
  };
  const buscar = async (num = "20261025123456") => {
    await userEvent.type(screen.getByLabelText("Número de cuenta"), num);
    await userEvent.click(screen.getByRole("button", { name: "Buscar cuenta" }));
  };

  it("MC-01 Muestra el buscador y no muestra cuenta al inicio", async () => {
    await abrir();
    expect(screen.getByRole("heading", { level: 1, name: "Modificar cuenta" })).toBeInTheDocument();
    expect(screen.getByLabelText("Número de cuenta")).toBeInTheDocument();
    expect(screen.queryByText("Nuevo estado de la cuenta")).not.toBeInTheDocument();
  });

  it("MC-02 Buscar con el campo vacío avisa y no llama al backend", async () => {
    await abrir();
    await userEvent.click(screen.getByRole("button", { name: "Buscar cuenta" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Ingresa el número de cuenta.");
    expect(get).not.toHaveBeenCalledWith("/core/cuentas/20261025123456");
  });

  it("MC-03 Busca con GET /core/cuentas/{num} y muestra el detalle", async () => {
    get.mockResolvedValue({ data: cuentaBase });
    await abrir();
    await buscar("  20261025123456 ");
    expect(await screen.findByText("Nuevo estado de la cuenta")).toBeInTheDocument();
    expect(get).toHaveBeenCalledWith("/core/cuentas/20261025123456");
    expect(screen.getByLabelText("Cuenta 20261025123456")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /^ACTIVA/ })).toBeChecked();
  });

  it("MC-04 Cuenta inexistente muestra el error del backend", async () => {
    get.mockRejectedValue(errorHttp(404, { error: { code: "CUENTA_NO_ENCONTRADA", message: "Cuenta 999 no existe." } }));
    await abrir();
    await buscar("999");
    expect(await screen.findByRole("alert")).toHaveTextContent("Cuenta 999 no existe. (CUENTA_NO_ENCONTRADA)");
    expect(screen.queryByText("Nuevo estado de la cuenta")).not.toBeInTheDocument();
  });

  it("MC-05 'Guardar cambios' estÃ¡ deshabilitado mientras no se elija otro estado", async () => {
    get.mockResolvedValue({ data: cuentaBase });
    await abrir();
    await buscar();
    const guardar = await screen.findByRole("button", { name: /Guardar cambios/ });
    expect(guardar).toBeDisabled();
    await userEvent.click(screen.getByRole("radio", { name: /BLOQUEADA/ }));
    expect(guardar).toBeEnabled();
  });

  it("MC-06 Cambia el estado con PATCH y actualiza el detalle", async () => {
    get.mockResolvedValue({ data: cuentaBase });
    patch.mockResolvedValue({ data: { ...cuentaBase, estado_cuenta: "BLOQUEADA" } });
    await abrir();
    await buscar();
    await userEvent.click(await screen.findByRole("radio", { name: /BLOQUEADA/ }));
    await userEvent.click(screen.getByRole("button", { name: /Guardar cambios/ }));
    await waitFor(() => expect(patch).toHaveBeenCalledTimes(1));
    const [url, body] = patch.mock.calls[0] as [string, Record<string, unknown>];
    expect(url).toBe("/core/cuentas/20261025123456");
    expect(body).toMatchObject({ estado_cuenta: "BLOQUEADA", actor: "portal-web" });
    expect(await screen.findByRole("status")).toHaveTextContent("Cuenta 20261025123456 actualizada: estado BLOQUEADA.");
    expect(within(screen.getByLabelText("Cuenta 20261025123456")).getByText("BLOQUEADA")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Guardar cambios/ })).toBeDisabled();
  });

  it("MC-07 Si el PATCH falla muestra el error y conserva el estado actual", async () => {
    get.mockResolvedValue({ data: cuentaBase });
    patch.mockRejectedValue(errorHttp(400, { error: { code: "ESTADO_CUENTA_INVALIDO", message: "Estado X no admitido." } }));
    await abrir();
    await buscar();
    await userEvent.click(await screen.findByRole("radio", { name: /EMBARGO/ }));
    await userEvent.click(screen.getByRole("button", { name: /Guardar cambios/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Estado X no admitido. (ESTADO_CUENTA_INVALIDO)");
    expect(within(screen.getByLabelText("Cuenta 20261025123456")).getByText("ACTIVA")).toBeInTheDocument();
  });

  it("MC-08 Ofrece exactamente los 4 estados admitidos por el backend", async () => {
    get.mockResolvedValue({ data: cuentaBase });
    await abrir();
    await buscar();
    await screen.findByText("Nuevo estado de la cuenta");
    const opciones = screen.getAllByRole("radio").map((r) => (r as HTMLInputElement).value);
    expect(opciones).toEqual(["ACTIVA", "INACTIVA", "BLOQUEADA", "EMBARGO"]);
  });

  it("MC-09 Desde una cuenta recién creada se puede ir a modificarla sin volver a buscarla", async () => {
    post.mockResolvedValue({ data: cuentaBase });
    render(<Home />);
    await irA(/Crear cuenta/);
    await screen.findByRole("option", { name: /Ahorro Clásico/ });
    await userEvent.type(screen.getByLabelText("Buscar cliente titular"), "11111111");
    await userEvent.click(screen.getByRole("button", { name: "Buscar id_cliente" }));
    await userEvent.selectOptions(await screen.findByLabelText("cliente titular seleccionado"), "cli-1");
    await userEvent.selectOptions(screen.getByLabelText("Producto de ahorro"), "prod-1");
    await userEvent.selectOptions(screen.getByLabelText("Agencia"), "ag-1");
    await userEvent.click(screen.getByRole("button", { name: /^Crear cuenta/ }));
    await userEvent.click(await screen.findByRole("button", { name: "Modificar estado de esta cuenta" }));
    expect(screen.getByRole("heading", { level: 1, name: "Modificar cuenta" })).toBeInTheDocument();
    expect(screen.getByLabelText("Número de cuenta")).toHaveValue("20261025123456");
    expect(screen.getByText("Nuevo estado de la cuenta")).toBeInTheDocument();
    expect(get).not.toHaveBeenCalledWith("/core/cuentas/20261025123456");
  });
});
