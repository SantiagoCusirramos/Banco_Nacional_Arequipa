import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

// Hallazgo M4: en Usuarios, Billetera y ClaveNueva los botones y las tarjetas no seguían
// las clases del sistema (sol-button primary/secondary y el relleno de sol-card).
const leer = (ruta: string) => readFileSync(resolve(process.cwd(), ruta), "utf8");
const ARCHIVOS = ["app/usuarios/page.tsx", "app/billetera/page.tsx", "app/components/ClaveNueva.tsx"];

describe("Consistencia visual", () => {
  it("ES-01 todos los botones de acción usan sol-button primary o secondary", () => {
    for (const archivo of ARCHIVOS) {
      const fuente = leer(archivo);
      for (const boton of fuente.matchAll(/<(?:button|a)\b[^>]*className="sol-button([^"]*)"/g)) {
        expect(boton[1], `${archivo}: ${boton[0]}`).toMatch(/^ (primary|secondary)$/);
      }
    }
  });

  it("ES-02 las tarjetas tienen el relleno del sistema", () => {
    for (const archivo of ARCHIVOS) {
      const fuente = leer(archivo);
      for (const tarjeta of fuente.matchAll(/className="sol-card([^"]*)"[\s\S]{0,200}/g)) {
        expect(tarjeta[0], `${archivo}: ${tarjeta[0]}`).toMatch(/sol-card-pad|padding:/);
      }
    }
  });

  it("ES-03 el relleno del sistema existe en la hoja de estilos", () => {
    expect(leer("app/solicitud-credito/sol.css")).toMatch(/\.sol-card-pad\s*\{[^}]*padding:/);
  });
});
