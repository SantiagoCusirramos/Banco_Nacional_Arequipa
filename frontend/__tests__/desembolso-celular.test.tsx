import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

// Hallazgo C9 de la prueba «solo con el mouse», visto otra vez en el recorrido final de la sesión 50:
// a 390 px el encabezado de Desembolso se salía por la derecha y «Volver al portal» y «Cerrar
// sesión» quedaban fuera de la pantalla. El encabezado debe poder partirse en filas.
vi.mock("next/navigation", () => ({ usePathname: () => "/desembolso", useRouter: () => ({ replace: vi.fn() }) }));
import { Marco } from "../app/desembolso/_componentes/Marco";
import { ProveedorSesion } from "@/lib/desembolso/sesion";

const SESION = { usuario: "operador.uno", rol: "OPERADOR", perfil: "OPERADOR" as const, puedeOperar: true, puedeConciliar: false };

describe("Encabezado de Desembolso en pantalla pequeña", () => {
  it("DC-01 el encabezado se parte en filas y la navegación se desplaza por su cuenta", () => {
    render(<ProveedorSesion sesion={SESION}><Marco><p>contenido</p></Marco></ProveedorSesion>);
    const nav = screen.getByRole("navigation", { name: "Navegación Desembolso" });
    expect(nav.parentElement?.className).toMatch(/\bflex-wrap\b/);
    expect(nav.className).toMatch(/\boverflow-x-auto\b/);
    expect(nav.className).toMatch(/\bmin-w-0\b/);
  });

  it("DC-02 «Volver al portal» y «Cerrar sesión» van juntos en un grupo que no se encoge", () => {
    render(<ProveedorSesion sesion={SESION}><Marco><p>contenido</p></Marco></ProveedorSesion>);
    const volver = screen.getByRole("link", { name: "Volver al portal" });
    const salir = screen.getByRole("button", { name: "Cerrar sesión" });
    expect(volver.parentElement).toBe(salir.parentElement);
    expect(volver.parentElement?.className).toMatch(/\bshrink-0\b/);
  });
});
