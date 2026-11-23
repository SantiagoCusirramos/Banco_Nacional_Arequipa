import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

// El PIN de Chaski lo generaba nadie: lo escribía el operador al afiliar (hallazgo C6). Ahora se
// genera y se muestra una vez para entregarlo, o la clienta lo escribe dos veces.
vi.mock("qrcode", () => ({ toDataURL: vi.fn(async () => "data:image/png;base64,eA==") }));
// La pantalla exige el perfil (bloque 3): un operador con los permisos reales de la billetera.
vi.mock("@/lib/auth", async (original) => ({
  ...(await original<typeof import("@/lib/auth")>()),
  obtenerMiPerfil: vi.fn(async () => ({ id_usuario: "u-op", username: "operador.uno", nombre: "Operador Uno", rol: "OPERADOR",
    acciones: ["AFILIAR_BILLETERA", "REGISTRAR_COMERCIO", "VER_CLIENTE", "VER_CUENTA"], debe_cambiar_clave: false })),
}));
vi.mock("@/lib/billetera", async (original) => ({
  ...(await original<typeof import("@/lib/billetera")>()),
  afiliar: vi.fn(),
  registrarComercio: vi.fn(),
}));
import { afiliar } from "@/lib/billetera";
import BilleteraPage from "../app/billetera/page";

const AFILIACION = { cod_cliente: "CLI000000001", num_cuenta: "24233417472693", estado: "ACTIVA", nueva: true };

beforeEach(() => {
  vi.mocked(afiliar).mockReset().mockResolvedValue(AFILIACION as never);
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ urlBilletera: null, urlCajero: null, urlApk: null })));
});

async function datosDelCliente() {
  render(<BilleteraPage />);
  fireEvent.change(await screen.findByLabelText(/Código del cliente/), { target: { value: "cli000000001" } });
  fireEvent.change(screen.getByLabelText("Número de cuenta en soles"), { target: { value: "24233417472693" } });
}

it("PB-01 el operador ya no escribe el PIN: se genera, se afilia y se muestra una vez", async () => {
  await datosDelCliente();
  expect(screen.queryByLabelText("PIN de la billetera (6 dígitos)")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Generar PIN y afiliar" }));
  await waitFor(() => expect(afiliar).toHaveBeenCalledTimes(1));
  const { pin, cod_cliente, num_cuenta } = vi.mocked(afiliar).mock.calls[0][0];
  expect(cod_cliente).toBe("CLI000000001");
  expect(num_cuenta).toBe("24233417472693");
  expect(pin).toMatch(/^\d{6}$/);
  const panel = await screen.findByRole("region", { name: /PIN de Chaski para entregar/ });
  expect(within(panel).getByText(pin)).toBeInTheDocument();
});

it("PB-02 la clienta lo escribe dos veces y no se muestra", async () => {
  await datosDelCliente();
  await userEvent.click(screen.getByLabelText("La clienta lo escribe"));
  fireEvent.change(screen.getByLabelText("PIN de Chaski (lo escribe la clienta)"), { target: { value: "281946" } });
  fireEvent.change(screen.getByLabelText("Repite el PIN de Chaski"), { target: { value: "281946" } });
  await userEvent.click(screen.getByRole("button", { name: "Afiliar a Chaski" }));
  await waitFor(() => expect(afiliar).toHaveBeenCalledWith({ cod_cliente: "CLI000000001", num_cuenta: "24233417472693", pin: "281946" }));
  expect(screen.queryByText("281946")).not.toBeInTheDocument();
});

it("PB-03 sin cliente o cuenta no afilia", async () => {
  render(<BilleteraPage />);
  await userEvent.click(await screen.findByRole("button", { name: "Generar PIN y afiliar" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/cliente y la cuenta/);
  expect(afiliar).not.toHaveBeenCalled();
});
