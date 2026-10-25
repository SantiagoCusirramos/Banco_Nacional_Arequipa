import { render, screen, within, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import Home from "../app/page";
import RootLayout, { metadata } from "../app/layout";

// ---------- Utilidades ----------
const nav = () => screen.getByRole("navigation", { name: "Navegación principal" });
const irA = async (nombre: RegExp) =>
  userEvent.click(within(nav()).getByRole("button", { name: nombre }));
const enviarTransferencia = (destino: string, monto: string) => {
  fireEvent.change(screen.getByLabelText(/Cuenta de destino/i), { target: { value: destino } });
  fireEvent.change(screen.getByLabelText(/Monto a transferir/i), { target: { value: monto } });
  // fireEvent.submit evita la validación nativa del navegador y prueba la lógica de React
  fireEvent.submit(screen.getByRole("button", { name: /Continuar transferencia/i }).closest("form")!);
};

// ======================================================
// CP-01 a CP-06: Pantalla de inicio y navegación
// ======================================================
describe("Inicio y navegación", () => {
  it("CP-01 Muestra el saludo y el saldo total al cargar", () => {
    render(<Home />);
    expect(screen.getByRole("heading", { level: 1, name: "¡Hola, Diego!" })).toBeInTheDocument();
    expect(screen.getByText("SALDO TOTAL DISPONIBLE")).toBeInTheDocument();
    expect(screen.getAllByText(/12,480\.75/).length).toBeGreaterThan(0);
  });

  it("CP-02 El menú lateral tiene las 7 opciones esperadas", () => {
    render(<Home />);
    for (const n of [/Resumen/, /Mis cuentas/, /Crear cuenta/, /Modificar cuenta/, /Transferencias/, /Movimientos/, /Tarjetas/]) {
      expect(within(nav()).getByRole("button", { name: n })).toBeInTheDocument();
    }
  });

  it("CP-03 Navegar a 'Mis cuentas' muestra la cuenta de ahorros", async () => {
    render(<Home />);
    await irA(/Mis cuentas/);
    expect(screen.getByRole("heading", { level: 1, name: "Mis cuentas" })).toBeInTheDocument();
    expect(screen.getByText("Cuenta principal")).toBeInTheDocument();
    expect(screen.getByText(/CUENTA DE AHORROS/)).toBeInTheDocument();
  });

  it("CP-04 Navegar a 'Tarjetas' muestra la tarjeta de débito Visa", async () => {
    render(<Home />);
    await irA(/Tarjetas/);
    expect(screen.getByText("Tarjeta de débito")).toBeInTheDocument();
    expect(screen.getByText("DIEGO VARGAS")).toBeInTheDocument();
    expect(screen.getByText("Habilitadas")).toBeInTheDocument();
  });

  it("CP-05 El logo regresa a la pantalla de Resumen", async () => {
    render(<Home />);
    await irA(/Tarjetas/);
    await userEvent.click(screen.getByText("Banco Nacional de Arequipa", { selector: "small" }));
    expect(screen.getByRole("heading", { level: 1, name: "¡Hola, Diego!" })).toBeInTheDocument();
  });

  it("CP-06 Los accesos rápidos llevan a su sección", async () => {
    render(<Home />);
    await userEvent.click(screen.getByRole("button", { name: /Transferir dinero/ }));
    expect(screen.getByRole("heading", { name: "Nueva transferencia" })).toBeInTheDocument();
  });
});

// ======================================================
// CP-07 a CP-09: Ocultar / mostrar saldo
// ======================================================
describe("Visibilidad del saldo", () => {
  it("CP-07 'Ocultar saldo' enmascara el monto", async () => {
    render(<Home />);
    await userEvent.click(screen.getByRole("button", { name: /Ocultar saldo/ }));
    expect(screen.getByText("S/ ••••••")).toBeInTheDocument();
    expect(screen.queryByText(/12,480\.75/)).not.toBeInTheDocument();
  });

  it("CP-08 'Mostrar saldo' vuelve a mostrar el monto", async () => {
    render(<Home />);
    await userEvent.click(screen.getByRole("button", { name: /Ocultar saldo/ }));
    await userEvent.click(screen.getByRole("button", { name: /Mostrar saldo/ }));
    expect(screen.getAllByText(/12,480\.75/).length).toBeGreaterThan(0);
  });

  it("CP-09 El estado de ocultar se conserva al cambiar a 'Mis cuentas'", async () => {
    render(<Home />);
    await userEvent.click(screen.getByRole("button", { name: /Ocultar saldo/ }));
    await irA(/Mis cuentas/);
    expect(screen.queryByText(/12,480\.75/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mostrar" })).toBeInTheDocument();
  });
});

// ======================================================
// CP-10 a CP-19: Transferencias (validaciones)
// ======================================================
describe("Transferencias", () => {
  const abrir = async () => {
    render(<Home />);
    await irA(/Transferencias/);
  };

  it("CP-10 El formulario muestra los campos y la advertencia de modo demostración", async () => {
    await abrir();
    expect(screen.getByLabelText(/Cuenta de destino/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Monto a transferir/i)).toBeInTheDocument();
    expect(screen.getByText(/Modo demostración/)).toBeInTheDocument();
  });

  it("CP-11 Rechaza destino vacío", async () => {
    await abrir();
    enviarTransferencia("", "100");
    expect(screen.getByRole("status")).toHaveTextContent("Completa el número de cuenta y un monto válido.");
  });

  it("CP-12 Rechaza destino con solo espacios", async () => {
    await abrir();
    enviarTransferencia("    ", "100");
    expect(screen.getByRole("status")).toHaveTextContent("Completa el número de cuenta y un monto válido.");
  });

  it.each([["0"], ["-50"], [""]])("CP-13 Rechaza monto inválido (%s)", async (monto) => {
    await abrir();
    enviarTransferencia("123456789", monto);
    expect(screen.getByRole("status")).toHaveTextContent("Completa el número de cuenta y un monto válido.");
  });

  it("CP-14 Rechaza monto mayor al saldo disponible", async () => {
    await abrir();
    enviarTransferencia("123456789", "12480.76");
    expect(screen.getByRole("status")).toHaveTextContent("El monto supera el saldo disponible");
  });

  it("CP-15 Acepta monto igual al saldo (valor límite)", async () => {
    await abrir();
    enviarTransferencia("123456789", "12480.75");
    expect(screen.getByRole("status")).toHaveTextContent("Transferencia simulada correctamente");
  });

  it("CP-16 Transferencia válida: aviso, redirección a Movimientos y registro del movimiento", async () => {
    await abrir();
    enviarTransferencia("987654321", "250.50");
    expect(screen.getByRole("status")).toHaveTextContent("Transferencia simulada correctamente");
    expect(screen.getByRole("heading", { level: 1, name: "Movimientos" })).toBeInTheDocument();
    expect(screen.getByText("Transferencia a 987654321")).toBeInTheDocument();
    expect(screen.getByText(/250\.50/)).toBeInTheDocument();
  });

  it("CP-17 El resumen refleja el monto escrito y comisión S/ 0.00", async () => {
    await abrir();
    fireEvent.change(screen.getByLabelText(/Monto a transferir/i), { target: { value: "300" } });
    const resumen = screen.getByText("Monto de la operación").parentElement!;
    expect(resumen).toHaveTextContent("300.00");
    expect(resumen).toHaveTextContent("Comisión");
    expect(resumen).toHaveTextContent("0.00");
  });

  it("CP-18 Los inputs tienen restricciones nativas (required, min, max, minLength)", async () => {
    await abrir();
    const destino = screen.getByLabelText(/Cuenta de destino/i);
    const monto = screen.getByLabelText(/Monto a transferir/i);
    expect(destino).toBeRequired();
    expect(destino).toHaveAttribute("minlength", "4");
    expect(monto).toBeRequired();
    expect(monto).toHaveAttribute("min", "0.01");
    expect(monto).toHaveAttribute("max", "12480.75");
  });

  it("CP-19 Los campos se limpian tras una transferencia exitosa", async () => {
    await abrir();
    enviarTransferencia("987654321", "10");
    await irA(/Transferencias/);
    expect(screen.getByLabelText(/Cuenta de destino/i)).toHaveValue("");
    expect(screen.getByLabelText(/Monto a transferir/i)).toHaveValue(null);
  });
});

// ======================================================
// CP-20 a CP-25: Movimientos (listado y búsqueda)
// ======================================================
describe("Movimientos", () => {
  const abrir = async () => {
    render(<Home />);
    await irA(/Movimientos/);
  };

  it("CP-20 Lista los 4 movimientos iniciales", async () => {
    await abrir();
    for (const t of ["Compra en Plaza Vea", "Transferencia recibida", "Pago de internet", "Depósito en cuenta"]) {
      expect(screen.getByText(t)).toBeInTheDocument();
    }
  });

  it("CP-21 Resumen muestra solo los movimientos recientes (máx. 4)", () => {
    render(<Home />);
    expect(screen.getByText("Movimientos recientes")).toBeInTheDocument();
    expect(screen.getAllByText(/^OP-\d+ ·/).length).toBe(4);
  });

  it("CP-22 La búsqueda filtra por título (sin distinguir mayúsculas)", async () => {
    await abrir();
    await userEvent.type(screen.getByRole("textbox", { name: "Buscar movimiento" }), "PLAZA");
    expect(screen.getByText("Compra en Plaza Vea")).toBeInTheDocument();
    expect(screen.queryByText("Pago de internet")).not.toBeInTheDocument();
  });

  it("CP-23 La búsqueda filtra por ID y por categoría", async () => {
    await abrir();
    const caja = screen.getByRole("textbox", { name: "Buscar movimiento" });
    await userEvent.type(caja, "OP-20479");
    expect(screen.getByText("Pago de internet")).toBeInTheDocument();
    expect(screen.queryByText("Compra en Plaza Vea")).not.toBeInTheDocument();
    await userEvent.clear(caja);
    await userEvent.type(caja, "servicios");
    expect(screen.getByText("Pago de internet")).toBeInTheDocument();
  });

  it("CP-24 Sin coincidencias muestra el mensaje de estado vacío", async () => {
    await abrir();
    await userEvent.type(screen.getByRole("textbox", { name: "Buscar movimiento" }), "zzzz");
    expect(screen.getByText("No se encontraron movimientos con esa búsqueda.")).toBeInTheDocument();
  });

  it("CP-25 Ingresos con '+' y gastos con '−'", async () => {
    await abrir();
    expect(screen.getByText(/^\+.*850\.00/)).toBeInTheDocument();
    expect(screen.getByText(/^−.*128\.50/)).toBeInTheDocument();
  });
});

// ======================================================
// CP-26 a CP-30: Avisos, menú móvil, layout
// ======================================================
describe("Avisos, menú móvil y layout", () => {
  it("CP-26 El botón de notificaciones muestra aviso y se puede cerrar", async () => {
    render(<Home />);
    await userEvent.click(screen.getByRole("button", { name: "Notificaciones" }));
    expect(screen.getByRole("status")).toHaveTextContent("No tienes notificaciones nuevas.");
    await userEvent.click(screen.getByRole("button", { name: "Cerrar aviso" }));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("CP-27 Cambiar de pestaña limpia el aviso anterior", async () => {
    render(<Home />);
    await userEvent.click(screen.getByRole("button", { name: "Notificaciones" }));
    await irA(/Tarjetas/);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("CP-28 Botones 'demo' (reporte, ayuda, bloqueo de tarjeta) avisan que no hay backend", async () => {
    render(<Home />);
    await userEvent.click(screen.getByRole("button", { name: /Descargar reporte/ }));
    expect(screen.getByRole("status")).toHaveTextContent("Reporte de demostración");
    await userEvent.click(screen.getByRole("button", { name: /Ir al centro de ayuda/ }));
    expect(screen.getByRole("status")).toHaveTextContent("Centro de ayuda");
    await irA(/Tarjetas/);
    await userEvent.click(screen.getByRole("button", { name: "Administrar tarjeta" }));
    expect(screen.getByRole("status")).toHaveTextContent("requiere conexión con el backend");
  });

  it("CP-29 El menú móvil alterna la clase 'sidebar-open' y se cierra al elegir opción", async () => {
    const { container } = render(<Home />);
    const sidebar = container.querySelector("aside")!;
    expect(sidebar).not.toHaveClass("sidebar-open");
    await userEvent.click(screen.getByRole("button", { name: "Abrir menú" }));
    expect(sidebar).toHaveClass("sidebar-open");
    await irA(/Mis cuentas/);
    expect(sidebar).not.toHaveClass("sidebar-open");
  });

  it("CP-30 Layout: idioma 'es' y metadatos del sitio", () => {
    expect(metadata.title).toBe("Banco Nacional de Arequipa | Banca personal");
    const html = RootLayout({ children: <p>x</p> });
    expect((html as { props: { lang: string } }).props.lang).toBe("es");
  });
});

// ======================================================
// CP-31 a CP-33: Accesos rápidos, perfil y productos
// ======================================================
describe("Accesos rápidos, perfil y productos", () => {
  it("CP-31 Accesos rápidos y 'Ver todos' llevan a su sección", async () => {
    render(<Home />);
    await userEvent.click(screen.getByRole("button", { name: /Ver mis cuentas/ }));
    expect(screen.getByRole("heading", { level: 1, name: "Mis cuentas" })).toBeInTheDocument();
    await irA(/Resumen/);
    await userEvent.click(screen.getByRole("button", { name: /Mis tarjetas/ }));
    expect(screen.getByRole("heading", { level: 1, name: "Tarjetas" })).toBeInTheDocument();
    await irA(/Resumen/);
    await userEvent.click(screen.getByRole("button", { name: /Ver todos/ }));
    expect(screen.getByRole("heading", { level: 1, name: "Movimientos" })).toBeInTheDocument();
  });

  it("CP-32 El botón de opciones de perfil indica que la sesión es de demostración", async () => {
    render(<Home />);
    await userEvent.click(screen.getByRole("button", { name: "Opciones de perfil" }));
    expect(screen.getByRole("status")).toHaveTextContent("Sesión de demostración activa.");
  });

  it("CP-33 'Abrir una cuenta' lleva a la pestaña Crear cuenta", async () => {
    render(<Home />);
    await irA(/Mis cuentas/);
    await userEvent.click(screen.getByRole("button", { name: "Abrir una cuenta" }));
    expect(screen.getByRole("heading", { level: 1, name: "Crear cuenta" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Abrir cuenta de ahorros" })).toBeInTheDocument();
  });
});

// ======================================================
// Defectos detectados (it.fails = el test pasa mientras el defecto exista)
// Cuando se corrija el defecto, estos tests fallarán y habrá que quitar ".fails"
// ======================================================
describe("Defectos conocidos (DEF)", () => {
  it.fails("DEF-01 Tras transferir, el saldo disponible debería disminuir", async () => {
    render(<Home />);
    await irA(/Transferencias/);
    enviarTransferencia("987654321", "1000");
    await irA(/Resumen/);
    expect(screen.queryAllByText(/12,480\.75/).length).toBe(0);
  });

  it.fails("DEF-02 No debería permitirse transferir dos veces el saldo completo", async () => {
    render(<Home />);
    await irA(/Transferencias/);
    enviarTransferencia("987654321", "12480.75");
    await irA(/Transferencias/);
    enviarTransferencia("987654321", "12480.75");
    expect(screen.getByRole("status")).toHaveTextContent("supera el saldo");
  });

  it.fails("DEF-03 La fecha del encabezado debería ser la fecha actual y no estar fija", () => {
    render(<Home />);
    const hoy = new Date().toLocaleDateString("es-PE", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
    expect(screen.getByText(/DE 20\d\d$/).textContent!.toLowerCase()).toContain(hoy.split(" ")[0].toLowerCase());
  });
});