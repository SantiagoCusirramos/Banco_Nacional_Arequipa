import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { BancaPersonal } from "../app/components/BancaPersonal";
import RootLayout, { metadata } from "../app/layout";

// La banca personal con una sesión ya iniciada; la exigencia de sesión se prueba en sesion.test.tsx.
const alSalir = vi.fn();
const USUARIO = { id_usuario: "u-1", username: "operador1", nombre: "María López", rol: "OPERADOR",
  acciones: ["VER_CUENTA", "VER_TARJETA", "BLOQUEAR_TARJETA", "AFILIAR_BILLETERA", "CREAR_CLIENTE",
    "CREAR_SOLICITUD_CREDITO", "EVALUAR_CREDITO", "DESEMBOLSAR_CREDITO", "REGISTRAR_PAGO"] };
const Home = () => <BancaPersonal usuario={USUARIO} onSalir={alSalir} />;

const nav = () => screen.getByRole("navigation", { name: "Navegación principal" });
const irA = (nombre: RegExp) => userEvent.click(within(nav()).getByRole("button", { name: nombre }));
const PANTALLAS = ["/cuenta", "/tarjetas", "/tarjetas/desbloqueo", "/evaluacion", "/desembolso", "/captacion", "/billetera", "/solicitud-credito",
  "/pagar-cuota", "/homebanking/index.html"];

describe("Portada (K-6)", () => {
  it("CP-01 Saluda con el nombre del usuario de la sesión", () => {
    render(<Home />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("¡Hola, María López!");
  });

  it("CP-02 Enlaza las nueve pantallas reales y el Home Banking, en el menú y en el resumen", () => {
    const { container } = render(<Home />);
    const enMenu = within(nav()).getAllByRole("link").map((a) => a.getAttribute("href"));
    expect([...enMenu].sort()).toEqual([...PANTALLAS].sort());
    const enResumen = [...container.querySelectorAll(".quick-grid a")].map((a) => a.getAttribute("href"));
    expect([...enResumen].sort()).toEqual([...PANTALLAS].sort());
  });

  it("CP-03 No queda ningún dato fijo de una persona ni movimientos simulados", () => {
    const { container } = render(<Home />);
    const texto = container.textContent ?? "";
    for (const fijo of ["Diego", "DIEGO", "4821", "VARGAS", "Modo demostración", "Descargar reporte"]) {
      expect(texto).not.toContain(fijo);
    }
  });

  it("CP-04 'Crear cuenta' y 'Modificar cuenta' siguen siendo pestañas reales", async () => {
    render(<Home />);
    await irA(/Crear cuenta/);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Crear cuenta");
    await irA(/Modificar cuenta/);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Modificar cuenta");
    await irA(/Resumen/);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("¡Hola, María López!");
  });
});

describe("Perfil y menú móvil", () => {
  it("CP-05 El perfil muestra al usuario de la sesión y su botón la cierra", async () => {
    render(<Home />);
    expect(screen.getAllByText("María López").length).toBeGreaterThan(0);
    expect(screen.getByText("OPERADOR")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Cerrar sesión" }));
    expect(alSalir).toHaveBeenCalledTimes(1);
  });

  it("CP-06 El menú móvil alterna la clase 'sidebar-open' y se cierra al elegir una pestaña", async () => {
    const { container } = render(<Home />);
    const sidebar = container.querySelector("aside")!;
    expect(sidebar).not.toHaveClass("sidebar-open");
    await userEvent.click(screen.getByRole("button", { name: "Abrir menú" }));
    expect(sidebar).toHaveClass("sidebar-open");
    await irA(/Crear cuenta/);
    expect(sidebar).not.toHaveClass("sidebar-open");
  });

  it("CP-07 Layout: idioma 'es' y metadatos del sitio", () => {
    expect(metadata.title).toBe("Banco Nacional de Arequipa | Banca personal");
    const html = RootLayout({ children: <p>x</p> });
    expect((html as { props: { lang: string } }).props.lang).toBe("es");
  });

  it("CP-08 La fecha del encabezado es la fecha actual", () => {
    render(<Home />);
    const hoy = new Date().toLocaleDateString("es-PE", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
    expect(screen.getByText(/DE 20\d\d$/).textContent!.toLowerCase()).toBe(hoy.toLowerCase());
  });
});
