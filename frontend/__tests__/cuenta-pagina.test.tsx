import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  apiCuentas: { get: vi.fn(), post: vi.fn() },
}));
import { apiCuentas } from "@/lib/api";
import CuentaPage from "../app/cuenta/page";

const get = vi.mocked(apiCuentas.get);
const post = vi.mocked(apiCuentas.post);
const sobre = (data: unknown) => ({ data: { success: true, status_code: 200, data } });

const CUENTA = {
  num_cuenta: "10100000000001", cci: "00219100000000000101", moneda: "PEN", regimen: "INDIVIDUAL",
  estado_cuenta: "ACTIVA", saldo_contable: "300.00", saldo_disponible: "300.00", id_agencia: "AQP01",
  titulares: ["CLI000000001"],
};
const MOVIMIENTOS = [
  { uuid_transaccion: "22222222-2222-4222-8222-222222222222", num_cuenta: CUENTA.num_cuenta, tipo_operacion: "TRANSFERENCIA_ENVIADA",
    naturaleza: "D", monto: "200.00", moneda: "PEN", glosa: "Transferencia por canal VEN", id_canal: "VEN",
    estado_transaccion: "APROBADO", fecha_hora: "2026-11-11T15:00:00Z" },
  { uuid_transaccion: "11111111-1111-4111-8111-111111111111", num_cuenta: CUENTA.num_cuenta, tipo_operacion: "DEPOSITO",
    naturaleza: "C", monto: "500.00", moneda: "PEN", glosa: "Deposito por canal VEN", id_canal: "VEN",
    estado_transaccion: "APROBADO", fecha_hora: "2026-11-11T14:00:00Z" },
];

const pestana = (nombre: RegExp) => userEvent.click(screen.getByRole("button", { name: nombre }));

beforeEach(() => {
  get.mockReset();
  post.mockReset();
});

describe("Página del módulo Cuentas", () => {
  it("CT-01 Abre una cuenta con los titulares escritos y muestra su detalle", async () => {
    post.mockResolvedValue(sobre(CUENTA));
    render(<CuentaPage />);
    await userEvent.type(screen.getByLabelText(/Número de cuenta/), "10100000000001");
    await userEvent.type(screen.getByLabelText(/CCI/), "00219100000000000101");
    await userEvent.type(screen.getByLabelText("Código del cliente titular"), "cli000000001");
    await userEvent.type(screen.getByLabelText("Agencia"), "AQP01");
    await userEvent.click(screen.getByRole("button", { name: "Crear cuenta" }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    expect(post.mock.calls[0]).toEqual(["/apertura", {
      num_cuenta: "10100000000001", cci: "00219100000000000101", moneda: "PEN", regimen: "INDIVIDUAL",
      id_agencia: "AQP01", titulares: [{ id_cliente: "CLI000000001" }],
    }]);
    expect(await screen.findByRole("status")).toHaveTextContent("Cuenta 10100000000001 abierta.");
    expect(screen.getByRole("heading", { name: /Detalle de Cuenta: 10100000000001/ })).toBeInTheDocument();
    expect(screen.getByText("S/ 300.00", { selector: "strong[style]" })).toBeInTheDocument();
  });

  it("CT-02 Un depósito envía el monto como texto decimal y muestra el identificador", async () => {
    post.mockResolvedValue(sobre({ uuid_transaccion: "11111111-1111-4111-8111-111111111111", replay: false }));
    render(<CuentaPage />);
    await pestana(/3\. Depositar/);
    await userEvent.type(screen.getByLabelText("Número de Cuenta"), "10100000000001");
    await userEvent.type(screen.getByLabelText("Monto"), "150.5");
    await userEvent.click(screen.getByRole("button", { name: /Ejecutar DEPOSITO/ }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/deposito", { num_cuenta: "10100000000001", monto: "150.50" }));
    expect(await screen.findByRole("status")).toHaveTextContent("11111111-1111-4111-8111-111111111111");
  });

  it("CT-03 Una transferencia envía origen, destino y monto", async () => {
    post.mockResolvedValue(sobre({ uuid_debito: "d-1", uuid_abono: "a-1", replay: false }));
    render(<CuentaPage />);
    await pestana(/3\. Depositar/);
    await userEvent.selectOptions(screen.getByLabelText("Tipo de Operación"), "transferencia");
    await userEvent.type(screen.getByLabelText("Cuenta de Origen"), "111");
    await userEvent.type(screen.getByLabelText("Cuenta de Destino"), "222");
    await userEvent.type(screen.getByLabelText("Monto"), "200");
    await userEvent.click(screen.getByRole("button", { name: /Ejecutar TRANSFERENCIA/ }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/transferencia", {
      num_cuenta_origen: "111", num_cuenta_destino: "222", monto: "200.00",
    }));
    expect(await screen.findByRole("status")).toHaveTextContent("Débito d-1, abono a-1");
  });

  it("CT-04 El error de una operación muestra el mensaje de CUENTAS", async () => {
    const error = new AxiosError("fail", "ERR_BAD_REQUEST");
    error.response = { status: 400, statusText: "", headers: {}, config: {} as never,
      data: { success: false, error_code: "ERR-CTA-FONDOS-INSUFICIENTES", message: "Saldo disponible insuficiente." } };
    post.mockRejectedValue(error);
    render(<CuentaPage />);
    await pestana(/3\. Depositar/);
    await userEvent.selectOptions(screen.getByLabelText("Tipo de Operación"), "retiro");
    await userEvent.type(screen.getByLabelText("Número de Cuenta"), "111");
    await userEvent.type(screen.getByLabelText("Monto"), "999");
    await userEvent.click(screen.getByRole("button", { name: /Ejecutar RETIRO/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Saldo disponible insuficiente.");
  });

  it("CT-05 Los movimientos muestran débito o crédito, el monto con su moneda y la glosa", async () => {
    get.mockResolvedValue(sobre(MOVIMIENTOS));
    render(<CuentaPage />);
    await pestana(/4\. Revisar movimientos/);
    await userEvent.type(screen.getByPlaceholderText(/Número de cuenta para revisar/), CUENTA.num_cuenta);
    await userEvent.click(screen.getByRole("button", { name: "Revisar movimientos" }));
    const filas = await screen.findAllByRole("row");
    expect(get).toHaveBeenCalledWith("/10100000000001/movimientos");
    expect(filas).toHaveLength(3);
    expect(within(filas[1]).getByText("TRANSFERENCIA_ENVIADA")).toBeInTheDocument();
    expect(within(filas[1]).getByText("Débito")).toBeInTheDocument();
    expect(within(filas[1]).getByText("S/ 200.00")).toBeInTheDocument();
    expect(within(filas[2]).getByText("Crédito")).toBeInTheDocument();
    expect(within(filas[2]).getByText("Deposito por canal VEN")).toBeInTheDocument();
  });

  it("CT-06 Una cuenta sin movimientos lo dice", async () => {
    get.mockResolvedValue(sobre([]));
    render(<CuentaPage />);
    await pestana(/4\. Revisar movimientos/);
    await userEvent.type(screen.getByPlaceholderText(/Número de cuenta para revisar/), "111");
    await userEvent.click(screen.getByRole("button", { name: "Revisar movimientos" }));
    expect(await screen.findByText("La cuenta no tiene movimientos.")).toBeInTheDocument();
  });

  it("CT-07 Un movimiento por su identificador", async () => {
    get.mockResolvedValue(sobre(MOVIMIENTOS[1]));
    render(<CuentaPage />);
    await pestana(/5\. Ver movimiento/);
    await userEvent.type(screen.getByPlaceholderText(/UUID de la transacción/), MOVIMIENTOS[1].uuid_transaccion);
    await userEvent.click(screen.getByRole("button", { name: "Ver movimiento" }));
    expect(await screen.findByRole("heading", { name: /Detalle del Movimiento/ })).toBeInTheDocument();
    expect(get).toHaveBeenCalledWith("/movimiento/11111111-1111-4111-8111-111111111111");
    expect(screen.getByText("DEPOSITO")).toBeInTheDocument();
    expect(screen.getByText("S/ 500.00")).toBeInTheDocument();
  });
});
