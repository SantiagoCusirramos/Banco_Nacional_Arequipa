import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { BancaPersonal } from "../app/components/BancaPersonal";
import { PANTALLAS, pantallasParaUsuario, puedeVerPantalla } from "@/lib/pantallas";

const salir = vi.fn();
const usuario = (rol: string, acciones: string[] = []) => ({
  id_usuario: "u-1", username: "u", nombre: "Ana Demo", rol, acciones,
});

describe("Mapa de pantallas del portal", () => {
  it("MR-01 define la ruta, roles y permisos habilitantes de cada pantalla", () => {
    const rutas = PANTALLAS.map((p) => p.href);
    expect(rutas).toEqual(expect.arrayContaining([
      "/cuenta", "/tarjetas", "/tarjetas/desbloqueo", "/billetera", "/captacion",
      "/solicitud-credito", "/evaluacion", "/desembolso", "/pagar-cuota", "/usuarios",
    ]));
    for (const p of PANTALLAS) {
      expect(p.label.length).toBeGreaterThan(0);
      expect(p.descripcion.length).toBeGreaterThan(0);
      expect(p.permisos.length).toBeGreaterThan(0);
    }
    const desbloqueo = PANTALLAS.find((p) => p.href === "/tarjetas/desbloqueo");
    expect(desbloqueo?.permisos).toContain("BLOQUEAR_TARJETA");
    const usuarios = PANTALLAS.find((p) => p.href === "/usuarios");
    expect(usuarios?.permisos).toEqual(["CREAR_USUARIO"]);
  });

  it("MR-02 filtra por acciones: un asesor no ve evaluación ni desembolso ni usuarios", () => {
    const acciones = ["VER_CLIENTE", "CREAR_CLIENTE", "MODIFICAR_CLIENTE", "CREAR_SOLICITUD_CREDITO",
      "VALIDAR_IDENTIDAD", "AFILIAR_BILLETERA", "CONSULTAR_DEUDA", "VER_CREDITO", "VER_CUENTA"];
    const visibles = pantallasParaUsuario(usuario("ASESOR", acciones)).map((p) => p.href);
    expect(visibles).toContain("/solicitud-credito");
    expect(visibles).toContain("/captacion");
    expect(visibles).not.toContain("/evaluacion");
    expect(visibles).not.toContain("/desembolso");
    expect(visibles).not.toContain("/usuarios");
    expect(visibles).toContain("/pagar-cuota");
  });

  it("MR-03 filtra por acciones: un analista ve evaluación pero no desembolso ni captación", () => {
    const acciones = ["APROBAR_CREDITO", "CONSULTAR_DEUDA", "EVALUAR_CREDITO", "VER_CLIENTE", "VER_CREDITO", "VER_CUENTA"];
    const visibles = pantallasParaUsuario(usuario("ANALISTA", acciones)).map((p) => p.href);
    expect(visibles).toContain("/evaluacion");
    expect(visibles).toContain("/cuenta");
    expect(visibles).not.toContain("/desembolso");
    expect(visibles).not.toContain("/captacion");
    expect(visibles).not.toContain("/solicitud-credito");
  });
});

describe("Menú del portal por rol", () => {
  it("MR-04 el menú y las tarjetas muestran solo pantallas permitidas", () => {
    const acciones = ["APROBAR_CREDITO", "CONSULTAR_DEUDA", "EVALUAR_CREDITO", "VER_CLIENTE", "VER_CREDITO", "VER_CUENTA"];
    render(<BancaPersonal usuario={usuario("ANALISTA", acciones)} onSalir={salir} />);
    const nav = screen.getByRole("navigation", { name: "Navegación principal" });
    expect(within(nav).getByRole("link", { name: /Evaluación/ })).toBeInTheDocument();
    expect(within(nav).queryByRole("link", { name: /Desembolso/ })).not.toBeInTheDocument();
    expect(within(nav).queryByRole("link", { name: /Captación/ })).not.toBeInTheDocument();
    expect(within(nav).queryByRole("link", { name: /Usuarios/ })).not.toBeInTheDocument();
  });

  it("MR-05 Usuarios aparece en el portal para quien tiene CREAR_USUARIO", () => {
    const acciones = ["CREAR_USUARIO", "ASIGNAR_ROLES", "VER_CUENTA"];
    render(<BancaPersonal usuario={usuario("ADMINISTRADOR", acciones)} onSalir={salir} />);
    const nav = screen.getByRole("navigation", { name: "Navegación principal" });
    expect(within(nav).getByRole("link", { name: /Usuarios/ })).toBeInTheDocument();
  });

  it("MR-06 el botón de salir es texto Cerrar sesión y Volver al portal apunta a /", async () => {
    const acciones = ["VER_CUENTA"];
    render(<BancaPersonal usuario={usuario("ANALISTA", acciones)} onSalir={salir} />);
    expect(screen.getByRole("button", { name: /Cerrar sesión/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Volver al portal/i })).toHaveAttribute("href", "/");
  });
});

describe("puedeVerPantalla", () => {
  it("MR-07 exige al menos un permiso habilitante", () => {
    expect(puedeVerPantalla(["VER_CUENTA"], "/cuenta")).toBe(true);
    expect(puedeVerPantalla([], "/cuenta")).toBe(false);
    expect(puedeVerPantalla(["CREAR_USUARIO"], "/usuarios")).toBe(true);
  });
});
