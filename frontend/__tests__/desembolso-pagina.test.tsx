import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "o-1" }),
  usePathname: () => "/desembolso/ordenes/o-1",
  useRouter: () => ({ push, replace: vi.fn() }),
}));
vi.mock("@/lib/desembolso/api", async (original) => ({
  ...(await original<typeof import("@/lib/desembolso/api")>()),
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn() },
}));
import { api, ErrorApi } from "@/lib/desembolso/api";
import { ProveedorSesion } from "@/lib/desembolso/sesion";
import type { Aprobacion, Cuenta, OrdenDetalle, Sesion } from "@/lib/desembolso/tipos";
import { ConSesion } from "../app/desembolso/_componentes/ConSesion";
import PaginaOrden from "../app/desembolso/ordenes/[id]/page";
import Desembolsar from "../app/desembolso/page";

const get = vi.mocked(api.get);
const post = vi.mocked(api.post);

const OPERADOR: Sesion = { usuario: "operador1", rol: "OPERADOR", perfil: "OPERADOR", puedeOperar: true, puedeConciliar: false };
const AUDITOR: Sesion = { usuario: "auditor1", rol: "AUDITOR", perfil: "AUDITOR", puedeOperar: false, puedeConciliar: true };

const CUOTAS = Array.from({ length: 12 }, (_, i) => ({
  numeroCuota: i + 1, fechaVencimiento: `2027-${String(i + 1).padStart(2, "0")}-15`, capital: "1250.00",
  interes: "100.00", cuotaTotal: "1350.00", saldoCapital: "0.00",
}));
const ORDEN: OrdenDetalle = {
  idOrden: "o-1", codigoOrden: "DES-2026-000001", estado: "PREPARADA", motivoRechazo: null, importe: "15000.00",
  moneda: "PEN", numCuenta: "CTA-0000000000000001", canal: "VEN", idAgencia: null, idEvaluacion: "e-1",
  idSolicitud: "0198b000-0000-7000-8000-000000000001", codCliente: "C000000123", usuarioPreparacion: "operador1",
  usuarioConfirmacion: null, uuidTransaccionAbono: null, codCredito: null,
  fechaCreacion: "2026-11-16T20:00:00Z", fechaActualizacion: "2026-11-16T20:00:00Z",
  validaciones: [{ idValidacion: "v-1", tipo: "CUENTA", resultado: "APROBADA", referenciaEvidencia: "CTA-0000000000000001",
    detalle: null, venceEn: null, fecha: "2026-11-16T20:00:00Z" }],
  eventos: [{ accion: "PREPARAR_ORDEN", resultado: "PREPARADA", actor: "operador1", correlationId: null,
    fechaHora: "2026-11-16T20:00:00Z" }],
  estadoSolicitud: "APROBADA", plazoMeses: 12,
  calendario: { idCalendario: "c-1", tipo: "PRELIMINAR", metodo: "FRANCES", tasa: "0.1268", cuotas: CUOTAS },
};
const CUENTAS: Cuenta[] = [
  { numCuenta: "CTA-0000000000000001", moneda: "PEN", regimen: "INDIVIDUAL", estadoCuenta: "ACTIVA", elegible: true, motivo: null },
  { numCuenta: "CTA-0000000000000002", moneda: "PEN", regimen: "MANCOMUNADA_INDISTINTA", estadoCuenta: "ACTIVA", elegible: false,
    motivo: "CUENTA_MANCOMUNADA" },
];
const APROBACION: Aprobacion = {
  idEvaluacion: "e-1", idSolicitud: ORDEN.idSolicitud, codCliente: "C000000123", ronda: 1, monto: "15000.00", moneda: "PEN",
  plazoMeses: 12, limiteAprobado: "21000.00", fechaAprobacion: "2026-11-16T19:00:00Z", vigenteHasta: "2026-12-16T19:00:00Z",
  idCalendario: "c-1", ordenAbierta: null,
};

function servidor(orden: OrdenDetalle) {
  get.mockImplementation(async (url: string) => {
    if (url === "ordenes/o-1") return { data: orden };
    if (url === "clientes/C000000123/cuentas") return { data: CUENTAS };
    if (url === "aprobaciones") return { data: [APROBACION] };
    throw new Error(`GET no esperado: ${url}`);
  });
}

async function verificarDocumento(boton: string) {
  fireEvent.change(screen.getByLabelText("Número del documento presentado"), { target: { value: "70000001" } });
  await userEvent.click(screen.getByLabelText("Verifiqué el documento original y a la persona"));
  await userEvent.click(screen.getByRole("button", { name: boton }));
}

const VERIFICADO = { idValidacion: 77, resultado: "APROBADO", motivo: null, codCliente: "C000000123",
  nombre: "Juan Perez Quispe", estadoCliente: "ACTIVO" };

beforeEach(() => {
  get.mockReset();
  post.mockReset();
  push.mockReset();
});

describe("Pantallas del módulo Desembolso", () => {
  it("DS-01 El auditor ve la orden sin pedir cuentas ni acciones de operador", async () => {
    servidor(ORDEN);
    render(<ProveedorSesion sesion={AUDITOR}><PaginaOrden /></ProveedorSesion>);
    expect(await screen.findByText("Cliente y crédito")).toBeInTheDocument();
    expect(get).not.toHaveBeenCalledWith("clientes/C000000123/cuentas", expect.anything());
    expect(screen.queryByRole("button", { name: "Validar identidad" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirmar desembolso" })).not.toBeInTheDocument();
  });

  it("DS-02 El operador verifica el documento y lo registra como evidencia de la orden", async () => {
    servidor(ORDEN);
    post.mockResolvedValue({ data: VERIFICADO });
    render(<ProveedorSesion sesion={OPERADOR}><PaginaOrden /></ProveedorSesion>);
    const boton = await screen.findByRole("button", { name: "Validar identidad" });
    expect(boton).toBeDisabled();   // falta el documento y la constancia de la verificación
    await verificarDocumento("Validar identidad");
    await waitFor(() => expect(post).toHaveBeenCalledWith("identidad",
      { tipoDocumento: "DNI", numeroDocumento: "70000001", identidadVerificada: true }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("ordenes/o-1/validaciones", expect.objectContaining(
      { tipo: "IDENTIDAD", resultado: "APROBADA", referenciaEvidencia: "77" })));
  });

  it("DS-03 Muestra el calendario de Solicitud que COREDB copiará como oficial", async () => {
    servidor(ORDEN);
    render(<ProveedorSesion sesion={OPERADOR}><PaginaOrden /></ProveedorSesion>);
    expect(await screen.findByText("Calendario de Solicitud")).toBeInTheDocument();
    expect(screen.getAllByText("S/ 1,350.00")).toHaveLength(3);
    await userEvent.click(screen.getByRole("button", { name: "Ver las 12" }));
    expect(screen.getAllByText("S/ 1,350.00")).toHaveLength(12);
  });

  it("DS-04 Sin sesión de COREDB pide iniciarla", async () => {
    get.mockRejectedValue(new ErrorApi("Sesión vencida", "NO_AUTENTICADO", 401));
    render(<ConSesion><p>contenido</p></ConSesion>);
    expect(await screen.findByText("Tu sesión no está iniciada o ya venció.")).toBeInTheDocument();
    expect(screen.queryByText("contenido")).not.toBeInTheDocument();
  });

  it("DS-05 Verificado el documento, prepara la orden con una cuenta elegible y le registra la identidad", async () => {
    servidor(ORDEN);
    post.mockImplementation(async (url: string) => {
      if (url === "identidad") return { data: VERIFICADO };
      if (url === "ordenes") return { data: { ...ORDEN, idOrden: "o-9" } };
      return { data: { ...ORDEN, estado: "VALIDADA" } };
    });
    render(<ProveedorSesion sesion={OPERADOR}><Desembolsar /></ProveedorSesion>);
    await verificarDocumento("Verificar identidad");
    expect(await screen.findByText("Juan Perez Quispe · C000000123")).toBeInTheDocument();
    expect(get).toHaveBeenCalledWith("aprobaciones", { params: { codCliente: "C000000123" } });
    // La cuenta mancomunada no se ofrece: se explica por qué.
    expect(screen.getByText(/solo se abona en una cuenta individual/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Preparar desembolso" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/desembolso/ordenes/o-9"));
    const [, cuerpo, opciones] = post.mock.calls.find(([url]) => url === "ordenes")!;
    expect(cuerpo).toEqual({ idEvaluacion: "e-1", numCuenta: "CTA-0000000000000001" });
    expect((opciones as { headers: Record<string, string> }).headers["X-Idempotency-Key"]).toMatch(/^[0-9a-f-]{36}$/);
    expect(post).toHaveBeenCalledWith("ordenes/o-9/validaciones", expect.objectContaining({ referenciaEvidencia: "77" }));
  });

  it("DS-06 Una orden VALIDADA se confirma y muestra el crédito creado", async () => {
    let orden: OrdenDetalle = { ...ORDEN, estado: "VALIDADA" };
    get.mockImplementation(async (url: string) => {
      if (url === "ordenes/o-1") return { data: orden };
      return { data: CUENTAS };
    });
    post.mockImplementation(async () => {
      orden = { ...orden, estado: "CONFIRMADA", codCredito: "CRE-2026-000007", uuidTransaccionAbono: "u-1",
        calendario: { ...ORDEN.calendario!, tipo: "OFICIAL" } };
      return { data: { idOrden: "o-1", codCredito: "CRE-2026-000007" } };
    });
    render(<ProveedorSesion sesion={OPERADOR}><PaginaOrden /></ProveedorSesion>);
    await userEvent.click(await screen.findByRole("button", { name: "Confirmar desembolso" }));
    expect(post).toHaveBeenCalledWith("ordenes/o-1/confirmacion");
    expect(await screen.findByText("Desembolso confirmado")).toBeInTheDocument();
    expect(screen.getByText("CRE-2026-000007")).toBeInTheDocument();
    expect(screen.getByText("Calendario oficial del crédito")).toBeInTheDocument();
  });

  it("DS-07 Una orden PREPARADA no se puede confirmar todavía", async () => {
    servidor(ORDEN);
    render(<ProveedorSesion sesion={OPERADOR}><PaginaOrden /></ProveedorSesion>);
    expect(await screen.findByRole("button", { name: "Confirmar desembolso" })).toBeDisabled();
    expect(await screen.findByRole("button", { name: /CTA-0000000000000002/ })).toBeDisabled();
  });
});
