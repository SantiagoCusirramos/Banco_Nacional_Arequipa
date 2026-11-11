import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BancaPersonal } from "../app/components/BancaPersonal";

// El frontend no llama a ningún servicio real en las pruebas.
vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  apiCore: { get: vi.fn(), post: vi.fn() },
  apiCuentas: { get: vi.fn(), post: vi.fn() },
}));
import { apiCore, apiCuentas } from "@/lib/api";

const core = vi.mocked(apiCore.get);
const post = vi.mocked(apiCuentas.post);
const get = vi.mocked(apiCuentas.get);

const cuentaBase = {
  num_cuenta: "20261025123456",
  cci: "00219100000000000101",
  moneda: "PEN",
  regimen: "INDIVIDUAL",
  estado_cuenta: "ACTIVA",
  saldo_contable: "0.00",
  saldo_disponible: "0.00",
  id_agencia: "AQP01",
  titulares: ["CLI000000001"],
};
const sobre = (data: unknown) => ({ data: { success: true, status_code: 200, data } });

const cliente = (codigo: string, nombres: string, extra: Record<string, unknown> = {}) => ({
  cod_cliente: codigo, tipo_documento: "DNI", numero_documento: "70000001", nombres,
  apellido_paterno: "Pérez", apellido_materno: null, estado_cliente: "ACTIVO", permite_operar: true, ...extra,
});
const CLIENTES: Record<string, unknown> = {
  CLI000000001: cliente("CLI000000001", "Ana"),
  CLI000000002: cliente("CLI000000002", "Luis"),
  CLI000000003: cliente("CLI000000003", "Rosa", { estado_cliente: "BLOQUEADO", permite_operar: false }),
};

const USUARIO = { id_usuario: "u-1", username: "diego", nombre: "Diego Vargas", rol: "OPERADOR" };
const nav = () => screen.getByRole("navigation", { name: "Navegación principal" });
const irA = (nombre: RegExp) => userEvent.click(within(nav()).getByRole("button", { name: nombre }));

function errorHttp(status: number, data: unknown) {
  const err = new AxiosError("fail", "ERR_BAD_REQUEST");
  err.response = { status, data, statusText: "", headers: {}, config: {} as never };
  return err;
}

beforeEach(() => {
  core.mockReset();
  post.mockReset();
  get.mockReset();
  core.mockImplementation((url) => {
    const ruta = String(url);
    if (ruta === "/coredb/catalogos/agencias") {
      return Promise.resolve({ data: [{ id_agencia: "AQP01", nombre: "Agencia Arequipa Centro" }] });
    }
    const codigo = ruta.replace("/coredb/clientes/", "");
    if (CLIENTES[codigo]) return Promise.resolve({ data: CLIENTES[codigo] });
    return Promise.reject(errorHttp(404, { error: { code: "CLIENTE_NO_ENCONTRADO", message: "El cliente no existe." } }));
  });
});

// ======================================================
// Crear cuenta: POST /api/cuenta/apertura (módulo CUENTAS)
// ======================================================
describe("Crear cuenta", () => {
  const abrir = async () => {
    render(<BancaPersonal usuario={USUARIO} onSalir={() => {}} />);
    await irA(/Crear cuenta/);
    await screen.findByRole("option", { name: /Agencia Arequipa Centro/ });
  };
  const buscarCliente = async (etiqueta: string, id: string, codigo: string) => {
    await userEvent.type(screen.getByLabelText(etiqueta), codigo);
    await userEvent.click(screen.getByRole("button", { name: "Buscar " + id }));
  };
  const llenar = async (codigo = "CLI000000001") => {
    await buscarCliente("Cliente titular", "cod_cliente", codigo);
    await screen.findByText(/Cliente seleccionado: Ana Pérez/);
    await userEvent.selectOptions(screen.getByLabelText("Agencia"), "AQP01");
  };
  const enviar = () => userEvent.click(screen.getByRole("button", { name: /^Crear cuenta/ }));

  it("CC-01 Muestra el formulario con sus campos y los valores por defecto", async () => {
    await abrir();
    expect(screen.getByRole("heading", { level: 1, name: "Crear cuenta" })).toBeInTheDocument();
    expect(screen.getByLabelText("Cliente titular")).toBeInTheDocument();
    expect(screen.getByLabelText("Moneda")).toHaveValue("PEN");
    expect(screen.getByLabelText("Agencia")).toBeInTheDocument();
    expect(screen.getByLabelText("Régimen")).toHaveValue("INDIVIDUAL");
    expect(screen.getByLabelText("Régimen")).toHaveTextContent(/MANCOMUNADA_INDISTINTA.*MANCOMUNADA_CONJUNTA/);
  });

  it("CC-02 Con campos vacíos muestra errores y no llama al backend", async () => {
    await abrir();
    await enviar();
    expect(await screen.findByText("Busca y selecciona el cliente titular.")).toBeInTheDocument();
    expect(screen.getByText("Selecciona una agencia.")).toBeInTheDocument();
    expect(post).not.toHaveBeenCalled();
  });

  it("CC-03 Buscar con el código en blanco avisa y no consulta al CORE", async () => {
    await abrir();
    await buscarCliente("Cliente titular", "cod_cliente", "   ");
    expect(screen.getByText("Ingresa el código del cliente para buscar.")).toBeInTheDocument();
    expect(core).toHaveBeenCalledTimes(1); // solo el catálogo de agencias
  });

  it("CC-04 Abre la cuenta por CUENTAS con el titular, la moneda, el régimen y la agencia", async () => {
    post.mockResolvedValue(sobre(cuentaBase));
    await abrir();
    await llenar();
    await userEvent.selectOptions(screen.getByLabelText("Moneda"), "USD");
    await enviar();
    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    const [url, body] = post.mock.calls[0] as [string, Record<string, unknown>];
    expect(url).toBe("/apertura");
    expect(body).toMatchObject({
      moneda: "USD", regimen: "INDIVIDUAL", id_agencia: "AQP01", titulares: [{ id_cliente: "CLI000000001" }],
    });
    expect(body.num_cuenta).toMatch(/^\d{14}$/);
    expect(body.cci).toMatch(/^\d{20}$/);
  });

  it("CC-05 Tras crear muestra la cuenta, el aviso y las acciones siguientes", async () => {
    post.mockResolvedValue(sobre(cuentaBase));
    await abrir();
    await llenar();
    await enviar();
    expect(await screen.findByRole("heading", { name: "Cuenta creada" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Cuenta 20261025123456 creada correctamente.");
    expect(screen.getByText("CLI000000001")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ver el estado de esta cuenta" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Abrir otra cuenta" })).toBeInTheDocument();
  });

  it("CC-06 'Abrir otra cuenta' devuelve el formulario vacío", async () => {
    post.mockResolvedValue(sobre(cuentaBase));
    await abrir();
    await llenar();
    await enviar();
    await userEvent.click(await screen.findByRole("button", { name: "Abrir otra cuenta" }));
    expect(screen.getByLabelText("Cliente titular")).toHaveValue("");
    expect(screen.getByLabelText("Agencia")).toHaveValue("");
  });

  it("CC-07 Muestra el mensaje de CUENTAS cuando la apertura falla", async () => {
    post.mockRejectedValue(errorHttp(404, { success: false, error_code: "ERR-CLI-NO-ENCONTRADO", message: "El cliente no existe." }));
    await abrir();
    await llenar();
    await enviar();
    expect(await screen.findByRole("alert")).toHaveTextContent("El cliente no existe.");
    expect(screen.queryByRole("heading", { name: "Cuenta creada" })).not.toBeInTheDocument();
  });

  it("CC-08 Muestra aviso de conexión si el servicio no responde", async () => {
    post.mockRejectedValue(new AxiosError("Network Error", "ERR_NETWORK"));
    await abrir();
    await llenar();
    await enviar();
    expect(await screen.findByRole("alert")).toHaveTextContent("No se pudo conectar con el servidor.");
  });

  it("CC-09 Un código inexistente o un cliente que no puede operar no se selecciona", async () => {
    await abrir();
    await buscarCliente("Cliente titular", "cod_cliente", "CLI999999999");
    expect(await screen.findByText("El cliente no existe.")).toBeInTheDocument();
    await userEvent.clear(screen.getByLabelText("Cliente titular"));
    await buscarCliente("Cliente titular", "cod_cliente", "cli000000003");
    expect(await screen.findByText("El cliente está BLOQUEADO y no puede operar.")).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Agencia"), "AQP01");
    await enviar();
    expect(await screen.findByText("Busca y selecciona el cliente titular.")).toBeInTheDocument();
    expect(post).not.toHaveBeenCalled();
  });

  it("CC-10 Cuenta mancomunada exige al menos dos titulares (RGN-16)", async () => {
    await abrir();
    await llenar();
    await userEvent.selectOptions(screen.getByLabelText("Régimen"), "MANCOMUNADA_INDISTINTA");
    await enviar();
    expect(await screen.findByText(/requiere al menos dos titulares/)).toBeInTheDocument();
    expect(post).not.toHaveBeenCalled();
  });

  it("CC-11 Mancomunada con segundo titular envía a los dos", async () => {
    post.mockResolvedValue(sobre({ ...cuentaBase, regimen: "MANCOMUNADA_CONJUNTA", titulares: ["CLI000000001", "CLI000000002"] }));
    await abrir();
    await llenar();
    await userEvent.selectOptions(screen.getByLabelText("Régimen"), "MANCOMUNADA_CONJUNTA");
    await userEvent.click(screen.getByRole("button", { name: "+ Agregar titular" }));
    await buscarCliente("Titular 2", "titular_2", "CLI000000002");
    await screen.findByText(/Cliente seleccionado: Luis Pérez/);
    await enviar();
    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    const [, body] = post.mock.calls[0] as [string, Record<string, unknown>];
    expect(body).toMatchObject({
      regimen: "MANCOMUNADA_CONJUNTA", titulares: [{ id_cliente: "CLI000000001" }, { id_cliente: "CLI000000002" }],
    });
  });

  it("CC-12 No permite repetir el mismo cliente como titular ni un segundo titular en una cuenta individual", async () => {
    await abrir();
    await llenar();
    await userEvent.click(screen.getByRole("button", { name: "+ Agregar titular" }));
    await buscarCliente("Titular 2", "titular_2", "CLI000000001");
    await enviar();
    expect(await screen.findByText("Este cliente ya figura como titular.")).toBeInTheDocument();
    expect(screen.getByText("Una cuenta individual tiene un solo titular.")).toBeInTheDocument();
    expect(post).not.toHaveBeenCalled();
  });

  it("CC-13 Se puede quitar un titular adicional", async () => {
    await abrir();
    await userEvent.click(screen.getByRole("button", { name: "+ Agregar titular" }));
    expect(screen.getByLabelText("Titular 2")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Quitar titular 2" }));
    expect(screen.queryByLabelText("Titular 2")).not.toBeInTheDocument();
  });

  it("CC-14 Cambiar de pestaña y volver deja el formulario limpio", async () => {
    await abrir();
    await llenar();
    await irA(/Resumen/);
    await irA(/Crear cuenta/);
    await screen.findByRole("option", { name: /Agencia Arequipa Centro/ });
    expect(screen.getByLabelText("Cliente titular")).toHaveValue("");
    expect(screen.getByLabelText("Agencia")).toHaveValue("");
  });
});

// ======================================================
// Modificar cuenta: GET /api/cuenta/{num_cuenta}
// ======================================================
describe("Modificar cuenta", () => {
  const abrir = async () => {
    render(<BancaPersonal usuario={USUARIO} onSalir={() => {}} />);
    await irA(/Modificar cuenta/);
  };
  const buscar = async (numero: string) => {
    if (numero) await userEvent.type(screen.getByLabelText("Número de cuenta"), numero);
    await userEvent.click(screen.getByRole("button", { name: "Buscar cuenta" }));
  };

  it("MC-01 Muestra el buscador y no muestra cuenta al inicio", async () => {
    await abrir();
    expect(screen.getByRole("heading", { name: "Modificar cuenta", level: 2 })).toBeInTheDocument();
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
  });

  it("MC-02 Buscar con el campo vacío avisa y no llama al backend", async () => {
    await abrir();
    await buscar("");
    expect(screen.getByRole("alert")).toHaveTextContent("Ingresa el número de cuenta.");
    expect(get).not.toHaveBeenCalled();
  });

  it("MC-03 Busca la cuenta por CUENTAS y muestra su detalle", async () => {
    get.mockResolvedValue(sobre({ ...cuentaBase, saldo_disponible: "150.50", titulares: ["CLI000000001", "CLI000000002"] }));
    await abrir();
    await buscar("20261025123456");
    const detalle = await screen.findByRole("article", { name: "Cuenta 20261025123456" });
    expect(get).toHaveBeenCalledWith("/20261025123456");
    expect(within(detalle).getByText("S/ 150.50")).toBeInTheDocument();
    expect(within(detalle).getByText("CLI000000002")).toBeInTheDocument();
    expect(within(detalle).getByText("AQP01")).toBeInTheDocument();
  });

  it("MC-04 Cuenta inexistente muestra el error del servicio", async () => {
    get.mockRejectedValue(errorHttp(404, { success: false, error_code: "ERR-CTA-NO-ENCONTRADA", message: "La cuenta 999 no existe." }));
    await abrir();
    await buscar("999");
    expect(await screen.findByRole("alert")).toHaveTextContent("La cuenta 999 no existe.");
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
  });

  it("MC-05 Muestra el estado de la cuenta y avisa que aún no se puede cambiar", async () => {
    get.mockResolvedValue(sobre({ ...cuentaBase, estado_cuenta: "BLOQUEADA" }));
    await abrir();
    await buscar("20261025123456");
    await screen.findByRole("article");
    const estados = screen.getAllByRole("radio");
    expect(estados.map((e) => (e as HTMLInputElement).value)).toEqual(["ACTIVA", "BLOQUEADA", "BLOQUEADA_PREVENTIVA", "CANCELADA"]);
    expect(screen.getByRole("radio", { name: /^BLOQUEADA\s*No origina/ })).toBeChecked();
    for (const estado of estados) expect(estado).toBeDisabled();
    expect(screen.getByRole("note")).toHaveTextContent("todavía no está disponible");
  });

  it("MC-06 Desde una cuenta recién creada se llega a su estado sin volver a buscarla", async () => {
    post.mockResolvedValue(sobre(cuentaBase));
    render(<BancaPersonal usuario={USUARIO} onSalir={() => {}} />);
    await irA(/Crear cuenta/);
    await screen.findByRole("option", { name: /Agencia Arequipa Centro/ });
    await userEvent.type(screen.getByLabelText("Cliente titular"), "CLI000000001");
    await userEvent.click(screen.getByRole("button", { name: "Buscar cod_cliente" }));
    await screen.findByText(/Cliente seleccionado/);
    await userEvent.selectOptions(screen.getByLabelText("Agencia"), "AQP01");
    await userEvent.click(screen.getByRole("button", { name: /^Crear cuenta/ }));
    await userEvent.click(await screen.findByRole("button", { name: "Ver el estado de esta cuenta" }));
    expect(screen.getByRole("heading", { level: 1, name: "Modificar cuenta" })).toBeInTheDocument();
    expect(screen.getByRole("article", { name: "Cuenta 20261025123456" })).toBeInTheDocument();
    expect(get).not.toHaveBeenCalled();
  });
});
