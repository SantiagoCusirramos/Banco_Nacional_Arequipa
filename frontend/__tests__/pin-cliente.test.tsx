import { render, screen, waitFor, within, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { esTrivial, generarPin } from "@/lib/pin";
import { ClaveNueva } from "../app/components/ClaveNueva";

// PIN definidos por la clienta o generados (hallazgo C6 de la prueba «solo con el mouse»): el
// empleado escribía el PIN de la tarjeta y el de Chaski. Ahora el sistema lo genera y se muestra
// una sola vez para entregarlo, o la clienta lo escribe dos veces en la pantalla.

describe("generarPin", () => {
  it("PC-01 da solo dígitos, del largo pedido y nunca triviales", () => {
    for (let i = 0; i < 500; i++) {
      const pin = generarPin(4);
      expect(pin).toMatch(/^\d{4}$/);
      expect(esTrivial(pin)).toBe(false);
    }
    expect(generarPin(6)).toMatch(/^\d{6}$/);
  });

  it("PC-02 reconoce los PIN triviales", () => {
    for (const p of ["0000", "1111", "1234", "4321", "123456", "654321", "0123", "9876"]) expect(esTrivial(p), p).toBe(true);
    for (const p of ["4821", "7350", "281946"]) expect(esTrivial(p), p).toBe(false);
  });
});

describe("ClaveNueva", () => {
  const props = (asignar = vi.fn(async (_valor: string) => undefined)) => ({ digitos: 4, nombre: "PIN del cajero", asignar });

  it("PC-03 por omisión genera el PIN, lo asigna y lo muestra una sola vez", async () => {
    const asignar = vi.fn(async (_valor: string) => undefined);
    render(<ClaveNueva {...props(asignar)} />);
    await userEvent.click(screen.getByRole("button", { name: "Generar y asignar" }));
    await waitFor(() => expect(asignar).toHaveBeenCalledTimes(1));
    const pin = asignar.mock.calls[0][0] as string;
    expect(pin).toMatch(/^\d{4}$/);
    const panel = await screen.findByRole("region", { name: /PIN del cajero para entregar/ });
    expect(within(panel).getByText(pin)).toBeInTheDocument();
    expect(within(panel).getByText(/no se volverá a mostrar/i)).toBeInTheDocument();
    await userEvent.click(within(panel).getByRole("button", { name: /Ya lo entregué/ }));
    expect(screen.queryByText(pin)).not.toBeInTheDocument();
  });

  it("PC-04 si falla la asignación, no muestra ningún PIN", async () => {
    const asignar = vi.fn(async (_valor: string) => { throw new Error("TARJETAS no respondió"); });
    render(<ClaveNueva {...props(asignar)} />);
    await userEvent.click(screen.getByRole("button", { name: "Generar y asignar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("TARJETAS no respondió");
    expect(screen.queryByRole("region", { name: /para entregar/ })).not.toBeInTheDocument();
  });

  it("PC-05 la clienta lo escribe dos veces; si no coinciden no se asigna", async () => {
    const asignar = vi.fn(async (_valor: string) => undefined);
    render(<ClaveNueva {...props(asignar)} />);
    await userEvent.click(screen.getByLabelText("La clienta lo escribe"));
    fireEvent.change(screen.getByLabelText("PIN del cajero (lo escribe la clienta)"), { target: { value: "4821" } });
    fireEvent.change(screen.getByLabelText("Repite el PIN del cajero"), { target: { value: "4822" } });
    await userEvent.click(screen.getByRole("button", { name: "Asignar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("no coinciden");
    expect(asignar).not.toHaveBeenCalled();
  });

  it("PC-06 con los dos iguales lo asigna, borra los campos y no lo muestra", async () => {
    const asignar = vi.fn(async (_valor: string) => undefined);
    render(<ClaveNueva {...props(asignar)} />);
    await userEvent.click(screen.getByLabelText("La clienta lo escribe"));
    const campo = screen.getByLabelText("PIN del cajero (lo escribe la clienta)");
    expect(campo).toHaveAttribute("type", "password");
    fireEvent.change(campo, { target: { value: "48a21" } });
    expect(campo).toHaveValue("4821");
    fireEvent.change(screen.getByLabelText("Repite el PIN del cajero"), { target: { value: "4821" } });
    await userEvent.click(screen.getByRole("button", { name: "Asignar" }));
    await waitFor(() => expect(asignar).toHaveBeenCalledWith("4821"));
    expect(campo).toHaveValue("");
    expect(screen.queryByText("4821")).not.toBeInTheDocument();
  });

  it("PC-07 rechaza un PIN trivial escrito por la clienta", async () => {
    const asignar = vi.fn(async (_valor: string) => undefined);
    render(<ClaveNueva {...props(asignar)} />);
    await userEvent.click(screen.getByLabelText("La clienta lo escribe"));
    fireEvent.change(screen.getByLabelText("PIN del cajero (lo escribe la clienta)"), { target: { value: "1234" } });
    fireEvent.change(screen.getByLabelText("Repite el PIN del cajero"), { target: { value: "1234" } });
    await userEvent.click(screen.getByRole("button", { name: "Asignar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/fácil de adivinar/);
    expect(asignar).not.toHaveBeenCalled();
  });
});
