import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  apiCobranza: { get: vi.fn(), post: vi.fn() },
  apiCuentas: { get: vi.fn(), post: vi.fn() },
  api: { get: vi.fn() },
}));
import { api, apiCobranza, apiCuentas } from "@/lib/api";
import PagarCuotaPage from "../app/pagar-cuota/page";

const get = vi.mocked(apiCobranza.get);
const post = vi.mocked(apiCobranza.post);
const getCuentas = vi.mocked(apiCuentas.get);
const perfil = vi.mocked(api.get);
const sobreCuentas = (data: unknown) => ({ data: { success: true, data } });

const CREDITO = {
  codCredito: "CR-0001", idCliente: "CLI000000001", montoAprobado: "450.00", moneda: "PEN",
  fechaDesembolso: "2026-01-01T00:00:00", estadoCredito: "ACTIVO", saldoTotalPendiente: "300.00",
  cuotas: [
    { idCuota: "CUO-1", numeroCuota: 1, fechaVencimiento: "2026-02-01", montoCuota: "150.00",
      saldoPendiente: "0.00", moraPendiente: "0.00", totalAdeudado: "0.00", estadoCuota: "PAGADA" },
    { idCuota: "CUO-2", numeroCuota: 2, fechaVencimiento: "2026-03-01", montoCuota: "150.00",
      saldoPendiente: "150.00", moraPendiente: "0.00", totalAdeudado: "150.00", estadoCuota: "PENDIENTE" },
    { idCuota: "CUO-3", numeroCuota: 3, fechaVencimiento: "2026-04-01", montoCuota: "150.00",
      saldoPendiente: "150.00", moraPendiente: "0.00", totalAdeudado: "150.00", estadoCuota: "PENDIENTE" },
  ],
};
const MONTO = {
  codCredito: "CR-0001", idCuota: "CUO-2", numeroCuota: 2, fechaVencimiento: "2026-03-01",
  saldoCapital: "150.00", moraVigente: "0.00", totalAPagar: "150.00",
};
const CUENTA = {
  num_cuenta: "10100000000001", cci: "00219100000000000101", moneda: "PEN", regimen: "INDIVIDUAL",
  estado_cuenta: "ACTIVA", saldo_contable: "500.00", saldo_disponible: "500.00", id_agencia: "AQP01",
  titulares: ["CLI000000001"],
};
const RESULTADO_BASE = {
  idPago: "PAG-0001", referenciaTransaccion: "ref-0001", estado: "CONFIRMADO", idempotente: false,
  motivo: null, codCredito: "CR-0001", idCanal: "HB", montoPago: "150.00", fechaHora: "2026-11-15T10:00:00",
  aplicacion: { idCuota: "CUO-2", numeroCuota: 2, montoAplicado: "150.00", montoAplicadoMora: "0.00",
    montoAplicadoCapital: "150.00", saldoPendienteCuota: "0.00", moraPendienteCuota: "0.00", estadoCuota: "PAGADA" },
  estadoCredito: "ACTIVO",
};
const COMPROBANTE = {
  numeroOperacion: "ref-0001", fechaHora: "2026-11-15T10:00:00", canal: "Home Banking", codCredito: "CR-0001",
  montoPagado: "150.00", montoAplicadoMora: "0.00", montoAplicadoCapital: "150.00", cuotaNumero: 2,
  saldoRestanteCuota: "0.00", moraRestanteCuota: "0.00", saldoRestanteCredito: "150.00", estadoCredito: "ACTIVO",
};

function errorCobranza(status: number, message: string) {
  return new AxiosError("fail", "ERR_BAD_REQUEST", undefined, undefined, {
    status, statusText: "", headers: {}, config: {} as never, data: { error: { code: "X", message } },
  });
}

function mockRutasGet() {
  get.mockImplementation((url: string) => {
    if (url === "/clientes/CLI000000001/creditos") return Promise.resolve({ data: [CREDITO] });
    if (url === "/creditos/CR-0001/monto-a-pagar") return Promise.resolve({ data: MONTO });
    if (url === "/pagos/ref-0001/comprobante") return Promise.resolve({ data: COMPROBANTE });
    return Promise.reject(new Error(`ruta no mockeada: ${url}`));
  });
}

async function irAPago() {
  render(<PagarCuotaPage />);
  await userEvent.type(screen.getByLabelText("Código del cliente"), "cli000000001");
  await userEvent.click(screen.getByRole("button", { name: "Ver créditos" }));
  await userEvent.click(await screen.findByRole("button", { name: "Pagar una cuota de este crédito" }));
  await screen.findByRole("heading", { name: /Pagar cuota 2 del crédito CR-0001/ });
}

beforeEach(() => {
  get.mockReset();
  post.mockReset();
  getCuentas.mockReset();
  perfil.mockReset();
  perfil.mockRejectedValue(new Error("sin sesión"));
  mockRutasGet();
  getCuentas.mockResolvedValue(sobreCuentas([CUENTA]));
});

describe("Página Pagar cuota", () => {
  it("PCC-01 Muestra los créditos del cliente con el estado de sus cuotas", async () => {
    render(<PagarCuotaPage />);
    await userEvent.type(screen.getByLabelText("Código del cliente"), "cli000000001");
    await userEvent.click(screen.getByRole("button", { name: "Ver créditos" }));
    await waitFor(() => expect(get).toHaveBeenCalledWith("/clientes/CLI000000001/creditos"));
    expect(await screen.findByRole("heading", { name: "Crédito CR-0001" })).toBeInTheDocument();
    expect(screen.getByText("PAGADA")).toBeInTheDocument();
    expect(screen.getAllByText("PENDIENTE")).toHaveLength(2);
  });

  it("PCC-02 Un cliente sin créditos lo dice", async () => {
    get.mockResolvedValueOnce({ data: [] });
    render(<PagarCuotaPage />);
    await userEvent.type(screen.getByLabelText("Código del cliente"), "CLI000000009");
    await userEvent.click(screen.getByRole("button", { name: "Ver créditos" }));
    expect(await screen.findByText("El cliente no tiene créditos en Cobranza.")).toBeInTheDocument();
  });

  it("PCC-03 Elegir un crédito trae lo que toca pagar hoy y las cuentas del cliente", async () => {
    await irAPago();
    expect(get).toHaveBeenCalledWith("/creditos/CR-0001/monto-a-pagar");
    expect(getCuentas).toHaveBeenCalledWith("/consolidada/CLI000000001");
    expect(screen.getByLabelText("Monto a pagar")).toHaveValue(150);
    expect(screen.getByLabelText("Cuenta de ahorros con la que paga")).toHaveValue("10100000000001");
  });

  it("PCC-04 Confirma el pago con la referencia generada", async () => {
    post.mockResolvedValue({ data: RESULTADO_BASE });
    await irAPago();
    await userEvent.click(screen.getByRole("button", { name: "Confirmar pago" }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    const [ruta, cuerpo] = post.mock.calls[0] as [string, Record<string, string>];
    expect(ruta).toBe("/cr-int-08/pagos");
    expect(cuerpo).toMatchObject({
      codCliente: "CLI000000001", codCredito: "CR-0001", montoPago: "150.00", cuentaOrigen: "10100000000001",
    });
    expect(cuerpo.referenciaTransaccion).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("PCC-05 Un pago CONFIRMADO muestra el comprobante", async () => {
    post.mockResolvedValue({ data: { ...RESULTADO_BASE, estado: "CONFIRMADO" } });
    await irAPago();
    await userEvent.click(screen.getByRole("button", { name: "Confirmar pago" }));
    expect(await screen.findByText(/Comprobante ref-0001/)).toBeInTheDocument();
    expect(get).toHaveBeenCalledWith("/pagos/ref-0001/comprobante");
    const comprobante = screen.getByRole("status");
    expect(within(comprobante).getByText("Home Banking")).toBeInTheDocument();
    expect(within(comprobante).getAllByText("S/ 150.00").length).toBeGreaterThan(0);
  });

  it("PCC-06 Un pago RECHAZADO muestra el motivo de CUENTAS", async () => {
    post.mockResolvedValue({
      data: { ...RESULTADO_BASE, estado: "RECHAZADO", motivo: "ERR-CTA-FONDOS-INSUFICIENTES: Saldo disponible insuficiente." },
    });
    await irAPago();
    await userEvent.click(screen.getByRole("button", { name: "Confirmar pago" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Saldo disponible insuficiente");
  });

  it("PCC-07 Un pago PENDIENTE explica que se revisará", async () => {
    post.mockResolvedValue({ data: { ...RESULTADO_BASE, estado: "PENDIENTE", motivo: "Sin respuesta de CUENTAS" } });
    await irAPago();
    await userEvent.click(screen.getByRole("button", { name: "Confirmar pago" }));
    expect(await screen.findByRole("status")).toHaveTextContent("se revisará");
  });

  it("PCC-08 Un pago que requiere revisión lo indica", async () => {
    post.mockResolvedValue({ data: { ...RESULTADO_BASE, estado: "REQUIERE_REVISION" } });
    await irAPago();
    await userEvent.click(screen.getByRole("button", { name: "Confirmar pago" }));
    expect(await screen.findByRole("status")).toHaveTextContent("revisión manual");
  });

  it("PCC-09 Un error de negocio 4xx muestra su detalle", async () => {
    post.mockRejectedValue(errorCobranza(409, "El crédito está CANCELADO; no admite más pagos"));
    await irAPago();
    await userEvent.click(screen.getByRole("button", { name: "Confirmar pago" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("El crédito está CANCELADO");
  });

  it("PCC-10 Reintentar mantiene la referencia; cambiar el monto la cambia", async () => {
    post.mockRejectedValueOnce(new AxiosError("Network Error", "ERR_NETWORK"));
    post.mockResolvedValue({ data: RESULTADO_BASE });
    await irAPago();
    const confirmar = () => userEvent.click(screen.getByRole("button", { name: "Confirmar pago" }));
    const llave = (i: number) => (post.mock.calls[i][1] as { referenciaTransaccion: string }).referenciaTransaccion;
    await confirmar();
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    await confirmar();
    await waitFor(() => expect(post).toHaveBeenCalledTimes(2));
    expect(llave(1)).toBe(llave(0));

    await userEvent.clear(screen.getByLabelText("Monto a pagar"));
    await userEvent.type(screen.getByLabelText("Monto a pagar"), "100");
    await confirmar();
    await waitFor(() => expect(post).toHaveBeenCalledTimes(3));
    expect(llave(2)).not.toBe(llave(1));
  });

  it("PCC-11 Sin sesión pide iniciarla", async () => {
    perfil.mockRejectedValue(errorCobranza(401, "Falta el encabezado Authorization: Bearer <token>."));
    render(<PagarCuotaPage />);
    const aviso = await screen.findByRole("alert");
    expect(aviso).toHaveTextContent("Tu sesión no está iniciada o ya venció.");
    expect(within(aviso).getByRole("link", { name: "Iniciar sesión" })).toHaveAttribute("href", "/login");
  });
});
