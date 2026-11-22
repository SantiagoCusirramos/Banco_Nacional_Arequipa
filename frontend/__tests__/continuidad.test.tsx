import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const router = { replace: vi.fn(), push: vi.fn() };
vi.mock("qrcode", () => ({ toDataURL: vi.fn(async () => "data:image/png;base64,") }));
vi.mock("next/navigation", () => ({
  useRouter: () => router,
  useSearchParams: () => new URLSearchParams(window.location.search),
}));

vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  api: { get: vi.fn(), post: vi.fn() },
  apiCore: { get: vi.fn(), post: vi.fn() },
  apiCuentas: { get: vi.fn(), post: vi.fn() },
}));

import { api, apiCore, apiCuentas } from "@/lib/api";
import {
  enmascararCuenta, enmascararDocumento, etiquetaSolicitud, rutaSeguraVolver, urlLoginConVolver,
} from "@/lib/continuidad";
import SelectorCliente from "../app/components/SelectorCliente";
import SelectorCuenta from "../app/components/SelectorCuenta";
import LoginPage from "../app/login/page";
import BilleteraPage from "../app/billetera/page";

const get = vi.mocked(api.get);
const post = vi.mocked(api.post);
const getCore = vi.mocked(apiCore.get);
const getCuentas = vi.mocked(apiCuentas.get);

const SOLICITANTE = {
  id_solicitante: "s-1", tipo_documento: "DNI", numero_documento: "70000001",
  nombres: "Ana", apellido_paterno: "Pérez", apellido_materno: "Quispe",
  celular: "987654321", correo: "ana@example.com", cod_cliente: "CLI000000001",
  creado_por: "asesor.uno", fecha_registro: "2026-01-15T10:00:00Z",
};
const CLIENTE = {
  cod_cliente: "CLI000000001", tipo_documento: "DNI", numero_documento: "70000001",
  nombres: "Ana", apellido_paterno: "Pérez", apellido_materno: "Quispe",
  estado_cliente: "ACTIVO", permite_operar: true,
};
const CUENTA = {
  num_cuenta: "10100000000001", cci: "00219100000000000101", moneda: "PEN", regimen: "INDIVIDUAL",
  estado_cuenta: "ACTIVA", saldo_contable: "450.50", saldo_disponible: "450.50", id_agencia: "AQP01",
  titulares: ["CLI000000001"],
};
const sobre = (data: unknown) => ({ data: { success: true, status_code: 200, data } });
const ID = "0198b000-0000-7000-8000-000000000001";

beforeEach(() => {
  get.mockReset(); post.mockReset(); getCore.mockReset(); getCuentas.mockReset();
  router.replace.mockReset(); router.push.mockReset();
  window.history.pushState({}, "", "/");
  localStorage.clear();
  sessionStorage.clear();
});
afterEach(() => {
  window.history.pushState({}, "", "/");
  localStorage.clear();
  sessionStorage.clear();
});

describe("Ayudas de continuidad", () => {
  it("CN-01 enmascara documentos y cuentas dejando ver solo los últimos cuatro dígitos", () => {
    expect(enmascararDocumento("70000001")).toBe("••••0001");
    expect(enmascararCuenta("10100000000001")).toBe("••••0001");
    expect(enmascararCuenta("")).toBe("—");
  });

  it("CN-02 solo admite rutas internas como destino al volver", () => {
    expect(rutaSeguraVolver("/cuenta?tab=operaciones")).toBe("/cuenta?tab=operaciones");
    expect(rutaSeguraVolver("//malicioso.test/cuenta")).toBeNull();
    expect(rutaSeguraVolver("https://malicioso.test")).toBeNull();
    expect(rutaSeguraVolver("cuenta")).toBeNull();
    expect(rutaSeguraVolver("")).toBeNull();
    expect(urlLoginConVolver("/cuenta?tab=operaciones")).toBe("/login?volver=%2Fcuenta%3Ftab%3Doperaciones");
  });

  it("CN-03 la etiqueta de una solicitud nunca muestra el UUID", () => {
    expect(etiquetaSolicitud({ idSolicitud: ID, codigo: "SOL-2611-ABCDEF12", codCliente: "CLI1", montoSolicitado: "15000.00" }))
      .toBe("SOL-2611-ABCDEF12");
    const sinCodigo = etiquetaSolicitud({ idSolicitud: ID, nombre: "Ana Pérez", monto: "15000.00", moneda: "PEN" });
    expect(sinCodigo).toContain("Ana Pérez");
    expect(sinCodigo).toContain("15,000.00");
    expect(sinCodigo).not.toContain(ID);
  });
});

describe("Selector de clientes", () => {
  it("SC-01 busca por documento o nombre en el cuerpo y muestra documento enmascarado, nombre y código", async () => {
    post.mockResolvedValue({ data: [SOLICITANTE] });
    const onChange = vi.fn();
    render(<SelectorCliente id="cod_cliente" label="Cliente titular" value="" onChange={onChange} />);

    await userEvent.type(screen.getByLabelText("Cliente titular"), "70000001");
    await userEvent.click(screen.getByRole("button", { name: "Buscar cod_cliente" }));

    expect(post).toHaveBeenCalledWith("/coredb/captacion/solicitantes/busqueda", {
      texto: "70000001", con_cliente: true, limite: 20,
    });
    expect(get).not.toHaveBeenCalled();
    const opcion = await screen.findByRole("button", { name: /Ana Pérez Quispe/ });
    expect(opcion).toHaveTextContent("••••0001");
    expect(opcion).toHaveTextContent("CLI000000001");
    await userEvent.click(opcion);
    expect(onChange).toHaveBeenCalledWith("CLI000000001");
  });

  it("SC-02 no consulta con menos de tres caracteres", async () => {
    render(<SelectorCliente id="cod_cliente" label="Cliente titular" value="" onChange={vi.fn()} />);
    await userEvent.type(screen.getByLabelText("Cliente titular"), "An");
    await userEvent.click(screen.getByRole("button", { name: "Buscar cod_cliente" }));
    expect(await screen.findByText("Escribe al menos 3 caracteres para buscar.")).toBeInTheDocument();
    expect(post).not.toHaveBeenCalled();
    expect(get).not.toHaveBeenCalled();
  });

  it("SC-03 admite escribir el código del cliente a mano", async () => {
    getCore.mockResolvedValue({ data: CLIENTE });
    const onChange = vi.fn();
    render(<SelectorCliente id="cod_cliente" label="Cliente titular" value="" onChange={onChange} />);
    fireEvent.change(screen.getByLabelText("Cliente titular"), { target: { value: "CLI000000001" } });
    await userEvent.click(screen.getByRole("button", { name: "Buscar cod_cliente" }));

    expect(getCore).toHaveBeenCalledWith("/coredb/clientes/CLI000000001");
    expect(post).not.toHaveBeenCalled();
    await waitFor(() => expect(onChange).toHaveBeenCalledWith("CLI000000001"));
    expect(await screen.findByText(/Cliente seleccionado: Ana Pérez Quispe/)).toBeInTheDocument();
  });
});

describe("Selector de cuentas", () => {
  it("SC-04 lista las cuentas del cliente con número enmascarado, moneda y saldo", async () => {
    getCuentas.mockResolvedValue(sobre([CUENTA]));
    const onChange = vi.fn();
    render(<SelectorCuenta id="cuenta" label="Número de Cuenta" codCliente="CLI000000001" value="" onChange={onChange} />);

    expect(getCuentas).toHaveBeenCalledWith("/consolidada/CLI000000001");
    const opcion = await screen.findByRole("button", { name: /••••0001/ });
    expect(opcion).toHaveTextContent("PEN");
    expect(opcion).toHaveTextContent("450.50");
    expect(opcion).not.toHaveTextContent("10100000000001");
    await userEvent.click(opcion);
    expect(onChange).toHaveBeenCalledWith("10100000000001");
  });

  it("SC-05 permite escribir un número de cuenta a mano", async () => {
    getCuentas.mockResolvedValue(sobre([]));
    const onChange = vi.fn();
    render(<SelectorCuenta id="cuenta" label="Número de Cuenta" codCliente="CLI000000001" value="" onChange={onChange} />);
    fireEvent.change(await screen.findByLabelText("Número de Cuenta"), { target: { value: "001-1234567-8" } });
    expect(onChange).toHaveBeenCalledWith("001-1234567-8");
  });
});

describe("Volver al entrar", () => {
  const USUARIO = { id_usuario: "u-1", username: "ana", nombre: "Ana", rol: "OPERADOR", activo: true };
  async function entrar() {
    post.mockResolvedValue({ data: { access_token: "t", token_type: "bearer", expires_in: 1800, usuario: USUARIO } });
    render(<LoginPage />);
    await userEvent.type(screen.getByLabelText("Usuario"), "ana");
    await userEvent.type(screen.getByLabelText("Contraseña"), "clave-larga");
    await userEvent.click(screen.getByRole("button", { name: /Ingresar a mi cuenta/ }));
  }

  it("LG-01 vuelve a la ruta interna pedida después de iniciar sesión", async () => {
    window.history.pushState({}, "", "/login?volver=%2Fcuenta%3Ftab%3Doperaciones");
    await entrar();
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/cuenta?tab=operaciones"));
  });

  it.each(["//malicioso.test/cuenta", "https://malicioso.test", "cuenta", "javascript:alert(1)"])(
    "LG-02 ignora un destino inseguro: %s", async (volver) => {
      window.history.pushState({}, "", `/login?volver=${encodeURIComponent(volver)}`);
      await entrar();
      await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/"));
    },
  );

  it("LG-03 sin destino entra al inicio", async () => {
    await entrar();
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/"));
  });
});

describe("Billetera sin copiar códigos", () => {
  const PERFIL = { id_usuario: "u-op", username: "operador", nombre: "Operador", rol: "OPERADOR",
    acciones: ["AFILIAR_BILLETERA", "REGISTRAR_COMERCIO"], debe_cambiar_clave: false };

  async function abrirBilletera() {
    get.mockResolvedValue({ data: PERFIL });
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({ urlBilletera: null, urlCajero: null, urlApk: null })));
    render(<BilleteraPage />);
    expect(await screen.findByRole("heading", { name: "Afiliar un cliente a Chaski" })).toBeInTheDocument();
  }

  afterEach(() => vi.unstubAllGlobals());

  it("BL-01 Afiliar elige cliente y cuenta de listas y deja el código listo para la operación", async () => {
    post.mockResolvedValue({ data: [SOLICITANTE] });
    getCuentas.mockResolvedValue(sobre([CUENTA]));
    await abrirBilletera();

    await userEvent.type(screen.getByLabelText("Cliente titular"), "Ana Pérez");
    await userEvent.click(screen.getByRole("button", { name: "Buscar cod_cliente" }));
    await userEvent.click(await screen.findByRole("button", { name: /Ana Pérez Quispe/ }));
    expect(await screen.findByLabelText("Número de cuenta en soles")).toHaveValue(CUENTA.num_cuenta);
    expect(screen.getByLabelText("Código del cliente")).toHaveValue("CLI000000001");
    expect(getCuentas).toHaveBeenCalledWith("/consolidada/CLI000000001");
  });

  it("BL-02 La cuenta de abono del comercio se elige de un cliente", async () => {
    getCuentas.mockResolvedValue(sobre([CUENTA]));
    await abrirBilletera();
    await userEvent.click(screen.getByRole("button", { name: "2. Registrar comercio" }));

    fireEvent.change(screen.getByLabelText("Código del cliente de la cuenta de abono"),
      { target: { value: "CLI000000001" } });
    const opcion = await screen.findByRole("button", { name: /••••0001/ });
    await userEvent.click(opcion);
    expect(screen.getByLabelText("Cuenta de abono en soles")).toHaveValue(CUENTA.num_cuenta);
  });
});
