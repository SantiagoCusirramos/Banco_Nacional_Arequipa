import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SaltarContenido } from "../app/components/SaltarContenido";

// Bloque 7 del backlog de usabilidad: teclado, logo, ancho de 390 px y consistencia visual.
const leer = (ruta: string) => readFileSync(resolve(process.cwd(), ruta), "utf8");
const CON_DESTINO = [
  "app/components/BancaPersonal.tsx", "app/captacion/page.tsx", "app/cuenta/page.tsx",
  "app/evaluacion/page.tsx", "app/usuarios/page.tsx", "app/billetera/page.tsx",
  "app/tarjetas/page.tsx", "app/pagar-cuota/page.tsx", "app/solicitud-credito/page.tsx",
  "app/desembolso/_componentes/Marco.tsx",
];

describe("Accesibilidad y pantalla pequeña", () => {
  it("AC-01 «Saltar al contenido» enlaza con el contenido principal", () => {
    render(<><SaltarContenido /><main id="contenido">Contenido principal</main></>);
    const enlace = screen.getByRole("link", { name: "Saltar al contenido" });
    expect(enlace).toHaveAttribute("href", "#contenido");
    expect(document.getElementById("contenido")).toBeInTheDocument();
  });

  it("AC-02 el enlace va antes que la página y aparece al recibir el foco", () => {
    const layout = leer("app/layout.tsx");
    expect(layout).toContain("<SaltarContenido />");
    expect(layout.indexOf("SaltarContenido")).toBeLessThan(layout.indexOf("{children}"));
    const css = leer("app/globals.css");
    expect(css).toMatch(/\.saltar-contenido:focus\s*\{[^}]*(left|clip|transform)/);
  });

  it("AC-03 el portal y los módulos con menú lateral tienen el destino del salto", () => {
    for (const archivo of CON_DESTINO) expect(leer(archivo), archivo).toContain('id="contenido"');
  });

  it("AC-04 el logo dice BNA en el portal, el login y el Home Banking", () => {
    for (const archivo of ["app/login/page.tsx", "app/components/BancaPersonal.tsx"]) {
      const fuente = leer(archivo);
      expect(fuente, archivo).toContain("<strong>BNA</strong>");
      expect(fuente, archivo).not.toContain("<strong>BAN</strong>");
    }
    expect(leer("public/homebanking/index.html")).toMatch(/marca-logo">BNA/);
  });

  it("AC-05 las tablas de Captación, Evaluación y Desembolso tienen desplazamiento propio", () => {
    const captacion = leer("app/captacion/page.tsx");
    for (const tabla of captacion.matchAll(/<table className="cap-tabla">/g)) {
      expect(captacion.slice(Math.max(0, tabla.index - 250), tabla.index)).toContain('className="sol-tablewrap"');
    }
    const evaluacion = leer("app/evaluacion/page.tsx");
    expect((evaluacion.match(/className="sol-tablewrap"/g) || []).length).toBeGreaterThanOrEqual(3);
    for (const archivo of ["app/desembolso/ordenes/[id]/page.tsx", "app/desembolso/ordenes/[id]/constancia/page.tsx"]) {
      const fuente = leer(archivo);
      for (const tabla of fuente.matchAll(/<table /g)) {
        expect(fuente.slice(Math.max(0, tabla.index - 250), tabla.index), archivo).toContain("overflow-x-auto");
      }
    }
    expect(leer("app/solicitud-credito/sol.css")).toMatch(/\.sol-tablewrap\s*\{[^}]*overflow-x:\s*auto/);
  });

  it("AC-06 «Cerrar sesión» de Desembolso queda visible y las pestañas se pueden tocar", () => {
    const marco = leer("app/desembolso/_componentes/Marco.tsx");
    expect(marco).toContain("Cerrar sesión");
    // Que no se encoja ni se salga de la pantalla lo comprueba DC-02 (desembolso-celular.test.tsx) en el DOM.
    expect(leer("app/solicitud-credito/sol.css")).toMatch(/\.sol-sidebar nav button\s*\{[^}]*min-height:\s*48px/);
  });

  it("AC-07 la portada no desborda a lo ancho", () => {
    expect(leer("app/globals.css")).toMatch(/\.app-shell\s*\{[^}]*overflow-x:\s*hidden/);
  });
});
