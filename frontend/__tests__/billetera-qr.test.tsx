import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const toDataURL = vi.hoisted(() => vi.fn(async (texto: string) => `data:image/png;base64,${btoa(texto)}`));
vi.mock("qrcode", () => ({ toDataURL }));

vi.mock("@/lib/billetera", async (original) => ({
  ...(await original<typeof import("@/lib/billetera")>()),
  afiliar: vi.fn(),
  registrarComercio: vi.fn(),
}));

import { afiliar, registrarComercio } from "@/lib/billetera";
import BilleteraPage from "../app/billetera/page";

// Los campos son los de la respuesta real de COREDB (frontend/lib/billetera.ts, Comercio).
const COMERCIO = {
  id_comercio: "5c1e0000-0000-4000-8000-000000000001",
  ruc: "20123456789",
  razon_social: "Bodega Doña Rosa",
  num_cuenta: "001-1234567-8",
  estado: "ACTIVO",
  id_qr: "9f8e7d6c-5b4a-4321-9876-1234567890ab",
};
const CONFIG = {
  urlBilletera: "http://localhost:8020",
  urlCajero: "http://localhost:8019",
  urlApk: "https://github.com/SantiagoCusirramos/Banco_Nacional_Arequipa/releases/download/v1/chaski.apk",
};
const pngDe = (texto: string) => `data:image/png;base64,${btoa(texto)}`;

let fetchConfig: ReturnType<typeof vi.fn>;

beforeEach(() => {
  toDataURL.mockClear();
  vi.mocked(afiliar).mockReset();
  vi.mocked(registrarComercio).mockReset().mockResolvedValue(COMERCIO);
  fetchConfig = vi.fn(async () => Response.json(CONFIG));
  vi.stubGlobal("fetch", fetchConfig);
});

afterEach(() => vi.unstubAllGlobals());

async function registrar() {
  await userEvent.click(screen.getByRole("button", { name: "2. Registrar comercio" }));
  fireEvent.change(screen.getByLabelText("RUC (11 dígitos)"), { target: { value: COMERCIO.ruc } });
  fireEvent.change(screen.getByLabelText("Razón social"), { target: { value: COMERCIO.razon_social } });
  fireEvent.change(screen.getByLabelText("Cuenta de abono en soles"), { target: { value: COMERCIO.num_cuenta } });
  await userEvent.click(screen.getByRole("button", { name: "Registrar comercio" }));
}

describe("QR del comercio en la billetera Chaski", () => {
  it("dibuja la trama exacta CHASKI|<id_qr> y pone el nombre del comercio debajo", async () => {
    render(<BilleteraPage />);
    await registrar();

    const imagen = await screen.findByAltText(`QR de pago de ${COMERCIO.razon_social}`);
    expect(toDataURL).toHaveBeenCalledWith(`CHASKI|${COMERCIO.id_qr}`, expect.objectContaining({ type: "image/png" }));
    expect(imagen).toHaveAttribute("src", pngDe(`CHASKI|${COMERCIO.id_qr}`));
    expect(imagen.closest("figure")?.querySelector("figcaption")).toHaveTextContent(COMERCIO.razon_social);
  });

  it("deja el id del QR como texto legible", async () => {
    render(<BilleteraPage />);
    await registrar();
    expect(await screen.findByText(COMERCIO.id_qr)).toBeInTheDocument();
  });

  it("permite descargar el PNG con el RUC e imprimir solo el QR y el nombre", async () => {
    render(<BilleteraPage />);
    await registrar();
    const imagen = await screen.findByAltText(`QR de pago de ${COMERCIO.razon_social}`);

    expect(screen.getByRole("link", { name: "Descargar QR" })).toHaveAttribute("download", `qr-${COMERCIO.ruc}.png`);
    expect(screen.getByRole("link", { name: "Descargar QR" })).toHaveAttribute("href", imagen.getAttribute("src"));

    const impresionOriginal = window.print;
    const imprimir = vi.fn();
    window.print = imprimir;
    try {
      await userEvent.click(screen.getByRole("button", { name: "Imprimir" }));
    } finally {
      window.print = impresionOriginal;
    }
    expect(imprimir).toHaveBeenCalledTimes(1);
    expect(imagen.closest("[data-impresion-qr]")).toHaveTextContent(COMERCIO.razon_social);
  });
});

describe("Instalar Chaski en el celular de la clienta", () => {
  it("ofrece el APK y el QR de configuración con la trama exacta", async () => {
    render(<BilleteraPage />);

    const titulo = screen.getByRole("heading", { name: "Instalar Chaski en el celular de la clienta" });
    expect(titulo.closest("form")).toBeNull();
    expect(fetchConfig).toHaveBeenCalledWith("/api/config-publica");
    expect(screen.getByRole("link", { name: "Descargar Chaski (APK)" })).toHaveAttribute("href", CONFIG.urlApk);
    expect(screen.getByText(/Conectar con mi banco/)).toBeInTheDocument();

    const imagen = await screen.findByAltText("QR de configuración de Chaski");
    expect(toDataURL).toHaveBeenCalledWith(`CHASKI-SERVIDOR|${CONFIG.urlBilletera}`, expect.objectContaining({ type: "image/png" }));
    expect(imagen).toHaveAttribute("src", pngDe(`CHASKI-SERVIDOR|${CONFIG.urlBilletera}`));
  });

  it("explica la variable del administrador y no muestra QR roto si falta la URL de la billetera", async () => {
    fetchConfig.mockResolvedValueOnce(Response.json({ ...CONFIG, urlBilletera: null }));
    render(<BilleteraPage />);

    expect(await screen.findByText(/BNA_URL_BILLETERA/)).toBeInTheDocument();
    expect(screen.queryByAltText("QR de configuración de Chaski")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Descargar Chaski (APK)" })).toHaveAttribute("href", CONFIG.urlApk);
  });

  it("explica la variable del administrador si falta el APK", async () => {
    fetchConfig.mockResolvedValueOnce(Response.json({ ...CONFIG, urlApk: null }));
    render(<BilleteraPage />);

    expect(await screen.findByText(/BNA_URL_APK/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Descargar Chaski (APK)" })).not.toBeInTheDocument();
  });
});
