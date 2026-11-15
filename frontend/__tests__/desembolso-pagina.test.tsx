import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "o-1" }),
  usePathname: () => "/desembolso/ordenes/o-1",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));
vi.mock("@/lib/desembolso/api", async (original) => ({
  ...(await original<typeof import("@/lib/desembolso/api")>()),
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn() },
}));
import { api, ErrorApi } from "@/lib/desembolso/api";
import { ProveedorSesion } from "@/lib/desembolso/sesion";
import type { OrdenDetalle, Sesion } from "@/lib/desembolso/tipos";
import { ConSesion } from "../app/desembolso/_componentes/ConSesion";
import PaginaOrden from "../app/desembolso/ordenes/[id]/page";

const get = vi.mocked(api.get);
const post = vi.mocked(api.post);

const OPERADOR: Sesion = { usuario: "operador1", nombre: "operador1", rol: "OPERADOR",
  permisos: ["DESEMBOLSO_EJECUTAR", "DESEMBOLSO_LEER"], agencia_id: "AG001", agencia_nombre: "Agencia principal",
  reversion_habilitada: false };
const AUDITOR: Sesion = { ...OPERADOR, usuario: "auditor1", nombre: "auditor1", rol: "AUDITOR", permisos: ["DESEMBOLSO_LEER"] };

const CALENDARIO = Array.from({ length: 24 }, (_, i) => ({
  numeroCuota: i + 1, fechaVencimiento: `2027-${String((i % 12) + 1).padStart(2, "0")}-15`, amortizacion: "416.67",
  interes: "100.00", cuotaTotal: "516.67", saldoFinal: "0.00",
}));
const ORDEN: OrdenDetalle = {
  id: "o-1", codigo_orden: "DES-2026-000001", estado: "PREPARADA", entrega_estado: "PENDIENTE", motivo_rechazo: null,
  aprobacion_id: "APR-2026-000001", aprobacion_version: 1, credito_id: "CRE-2026-000001", cliente_id: "CLI000000001",
  cuenta_id: null, importe: "10000.00", moneda: "PEN", operacion_financiera_id: null, fecha_efectiva: null,
  idempotency_key: "k-1", usuario_preparacion: "operador1", usuario_confirmacion: null, correlation_id: "c-1", version: 1,
  creado_en: "2026-11-15T20:00:00+00:00", actualizado_en: "2026-11-15T20:00:00+00:00", cuenta_enmascarada: null,
  identidad: null, solicitud_id: "0198b000-0000-7000-8000-000000000001", calendario: CALENDARIO,
  aprobacion: { aprobacion_id: "APR-2026-000001", version: 1, credito_id: "CRE-2026-000001", cliente_id: "CLI000000001",
    cliente_nombre: "Juan Perez Quispe", cliente_documento: "****0001", producto: "Crédito Personal", importe: "10000.00",
    moneda: "PEN", plazo_meses: 24, tasa_tea: "22.00", estado: "VIGENTE", vigente_hasta: "2026-12-15T12:00:00-05:00" },
  validaciones: [], eventos: [], reversiones: [], acciones: [],
};

function servidor(orden: OrdenDetalle) {
  get.mockImplementation(async (url: string) => {
    if (url === "ordenes/o-1") return { data: orden };
    if (url === "ordenes/o-1/cuentas-elegibles") return { data: [] };
    throw new Error(`GET no esperado: ${url}`);
  });
}

beforeEach(() => {
  get.mockReset();
  post.mockReset();
});

describe("Pantallas del módulo Desembolso", () => {
  it("DS-01 El auditor ve la orden sin pedir cuentas ni acciones de operador", async () => {
    servidor(ORDEN);
    render(<ProveedorSesion sesion={AUDITOR}><PaginaOrden /></ProveedorSesion>);
    expect(await screen.findByText("El operador aún no elige la cuenta destino.")).toBeInTheDocument();
    expect(get).not.toHaveBeenCalledWith("ordenes/o-1/cuentas-elegibles");
    expect(screen.queryByRole("button", { name: "Validar identidad" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Continuar a confirmación" })).not.toBeInTheDocument();
  });

  it("DS-02 El operador verifica la identidad con el documento original", async () => {
    servidor(ORDEN);
    post.mockResolvedValue({ data: { ...ORDEN, identidad: { resultado: "APROBADA", vence_en: null, detalle: "Coincide" } } });
    render(<ProveedorSesion sesion={OPERADOR}><PaginaOrden /></ProveedorSesion>);
    const boton = await screen.findByRole("button", { name: "Validar identidad" });
    await waitFor(() => expect(get).toHaveBeenCalledWith("ordenes/o-1/cuentas-elegibles"));
    expect(boton).toBeDisabled();   // falta el documento y la constancia de la verificación
    fireEvent.change(screen.getByLabelText("Número del documento presentado"), { target: { value: "70000001" } });
    await userEvent.click(screen.getByLabelText("Verifiqué el documento original y a la persona"));
    await userEvent.click(boton);
    await waitFor(() => expect(post).toHaveBeenCalledWith("ordenes/o-1/identidad",
      { metodo: "VERIFICACION_PRESENCIAL", numero_documento: "70000001" }));
  });

  it("DS-03 Muestra el calendario de Solicitud que irá a Cobranza", async () => {
    servidor(ORDEN);
    render(<ProveedorSesion sesion={OPERADOR}><PaginaOrden /></ProveedorSesion>);
    expect(await screen.findByText("Calendario de Solicitud")).toBeInTheDocument();
    expect(screen.getAllByText("S/ 516.67")).toHaveLength(3);
    await userEvent.click(screen.getByRole("button", { name: "Ver las 24" }));
    expect(screen.getAllByText("S/ 516.67")).toHaveLength(24);
  });

  it("DS-04 Sin sesión de COREDB pide iniciarla", async () => {
    get.mockRejectedValue(new ErrorApi("Sesión vencida", "NO_AUTENTICADO", 401));
    render(<ConSesion><p>contenido</p></ConSesion>);
    expect(await screen.findByText("Tu sesión no está iniciada o ya venció.")).toBeInTheDocument();
    expect(screen.queryByText("contenido")).not.toBeInTheDocument();
  });
});
