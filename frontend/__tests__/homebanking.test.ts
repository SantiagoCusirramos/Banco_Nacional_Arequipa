import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

// K-5: el Home Banking se sirve desde public/ y solo llama a los puentes que existen.
const HB = resolve(process.cwd(), "public/homebanking"); // vitest corre en frontend/
const JS = join(HB, "js");
// /api/solicitud-credito/auth/logout: cerrar sesión cierra también Solicitud de crédito.
const PUENTES = ["/api/core/coredb/", "/api/cuenta/", "/api/tarjeta/", "/api/cobranza/", "/api/solicitud-credito/auth/logout"];
const scripts = () => readdirSync(JS).filter((f) => f.endsWith(".js")).map((f) => [f, readFileSync(join(JS, f), "utf8")] as const);

describe("Home Banking (K-5)", () => {
  it("HB-01 Next lo sirve: está en public/ y ya no en app/", () => {
    expect(existsSync(join(HB, "index.html"))).toBe(true);
    expect(existsSync(resolve(process.cwd(), "app/homebanking"))).toBe(false);
    expect(scripts().length).toBeGreaterThan(5);
  });

  it("HB-02 Sin datos simulados ni rutas /bus/v1", () => {
    expect(existsSync(join(JS, "datos.js"))).toBe(false);
    for (const [archivo, texto] of scripts()) {
      expect(texto, archivo).not.toMatch(/\/bus\/v1/);
      expect(texto, archivo).not.toMatch(/DatosDemo|datosSimulados/);
    }
  });

  it("HB-03 Cada ruta que pide es un puente existente del frontend", () => {
    const rutas: string[] = [];
    for (const [, texto] of scripts()) {
      for (const m of texto.matchAll(/(?:fetch|invocarAPI|invocar)\(\s*['"`]([^'"`]+)['"`]/g)) rutas.push(m[1]);
    }
    expect(rutas.length).toBeGreaterThan(8);
    expect(rutas.filter((r) => !PUENTES.some((p) => r.startsWith(p)))).toEqual([]);
  });

  it("HB-04 Las operaciones que mueven dinero conservan la llave al reintentar", () => {
    const transferencias = readFileSync(join(JS, "transferencias.js"), "utf8");
    const creditos = readFileSync(join(JS, "creditos.js"), "utf8");
    // La llave solo se renueva al registrarse la operación o al editar los datos, nunca en el catch.
    for (const texto of [transferencias, creditos]) {
      const captura = texto.slice(texto.lastIndexOf("} catch (err) {"));
      expect(captura.slice(0, captura.indexOf("} finally"))).not.toMatch(/idemActual = null/);
    }
  });
});
