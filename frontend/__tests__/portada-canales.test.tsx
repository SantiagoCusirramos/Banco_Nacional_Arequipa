import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { BancaPersonal } from "../app/components/BancaPersonal";

// Hallazgos B3 y B5 de la prueba «solo con el mouse»: ninguna pantalla enlazaba al cajero ni a la
// descarga de Chaski (0 coincidencias de «cajero» en el portal). Ahora la portada los muestra con
// las URL públicas del despliegue (/api/config-publica), si están configuradas.
const USUARIO = { id_usuario: "u-1", username: "operador.uno", nombre: "Operador Uno", rol: "OPERADOR",
  acciones: ["VER_CUENTA", "AFILIAR_BILLETERA"] };

afterEach(() => vi.unstubAllGlobals());

describe("Portada: cajero y Chaski", () => {
  it("PO-01 con las URL configuradas, enlaza al cajero y a la descarga de Chaski", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({
      urlBilletera: "https://billetera.example", urlCajero: "https://cajero.example", urlApk: "https://github.com/x/releases" })));
    render(<BancaPersonal usuario={USUARIO} onSalir={() => {}} />);
    const cajero = await screen.findByRole("link", { name: /Cajero \(simulador\)/ });
    expect(cajero).toHaveAttribute("href", "https://cajero.example");
    expect(screen.getByRole("link", { name: /Descargar Chaski/ })).toHaveAttribute("href", "https://github.com/x/releases");
  });

  it("PO-02 sin URL no muestra enlaces rotos", async () => {
    const pedido = vi.fn(async () => Response.json({ urlBilletera: null, urlCajero: null, urlApk: null }));
    vi.stubGlobal("fetch", pedido);
    render(<BancaPersonal usuario={USUARIO} onSalir={() => {}} />);
    await vi.waitFor(() => expect(pedido).toHaveBeenCalledWith("/api/config-publica"));
    expect(screen.queryByRole("link", { name: /Cajero \(simulador\)/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Descargar Chaski/ })).not.toBeInTheDocument();
  });

  it("PO-03 si la configuración no responde, la portada sigue funcionando", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));
    render(<BancaPersonal usuario={USUARIO} onSalir={() => {}} />);
    expect(await screen.findByRole("navigation", { name: "Navegación principal" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Cajero/ })).not.toBeInTheDocument();
  });
});
