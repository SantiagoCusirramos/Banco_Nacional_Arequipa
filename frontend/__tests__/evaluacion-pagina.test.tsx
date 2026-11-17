import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  apiEvaluacion: { get: vi.fn(), post: vi.fn() },
  api: { get: vi.fn() },
}));
import { api, apiEvaluacion } from "@/lib/api";
import EvaluacionPage from "../app/evaluacion/page";

const get = vi.mocked(apiEvaluacion.get);
const post = vi.mocked(apiEvaluacion.post);
const perfil = vi.mocked(api.get);
const escribir = (campo: HTMLElement, valor: string) => fireEvent.change(campo, { target: { value: valor } });

// Las rutas de Evaluación devuelven lo que COREDB responde (CONTRATO_CREDITOS.md §3).
const ID = "0198b000-0000-7000-8000-000000000001";
const ID_EVA = "4a1b0c2d-0000-5000-8000-000000000001";
const ANALISTA = { id_usuario: "u-1", username: "ana.analista", nombre: "Ana Analista", rol: "ANALISTA", modulo: null,
  acciones: ["APROBAR_CREDITO", "EVALUAR_CREDITO", "VER_CREDITO"] };
const AUDITOR = { id_usuario: "u-2", username: "aldo.auditor", nombre: "Aldo Auditor", rol: "AUDITOR", modulo: null,
  acciones: ["VER_AUDITORIA", "VER_CREDITO"] };

const SOLICITUD = {
  idSolicitud: ID, versionSolicitud: 1, ronda: 1, codCliente: "CLI0000001", montoSolicitado: "15000.00",
  moneda: "PEN", plazoMeses: 2, condicionPagoDoble: false, estado: "EN_EVALUACION",
  fechaCreacion: "2026-11-15T15:00:00Z", numeroCuotas: 2, totalCuotas: "15377.11", primerVencimiento: "2026-12-15",
};
const CUOTA = { otrosConceptos: "0.00", estadoCuota: "PENDIENTE" };
const DETALLE = {
  ...SOLICITUD,
  calendario: {
    idCalendario: "c-1", tipo: "PRELIMINAR", metodo: "FRANCES", tasa: "0.2200",
    cuotas: [
      { numeroCuota: 1, fechaVencimiento: "2026-12-15", capital: "7373.33", interes: "250.00", cuotaTotal: "7623.33",
        saldoCapital: "7626.67", saldoPendiente: "7623.33", ...CUOTA },
      { numeroCuota: 2, fechaVencimiento: "2027-01-14", capital: "7626.67", interes: "127.11", cuotaTotal: "7753.78",
        saldoCapital: "0.00", saldoPendiente: "7753.78", ...CUOTA },
    ],
  },
  evaluaciones: [],
  historial: [{ estado: "EN_EVALUACION", fechaHora: "2026-11-15T15:00:00Z", actor: "svc-evaluacion", motivo: null }],
};
const EVALUACION = {
  idEvaluacion: ID_EVA, ronda: 1, fechaEvaluacion: "2026-11-15T15:05:00Z", score: "850", limite: "16800.00",
  regla: "R-B", resultadoRegla: "OBSERVADO", ingresoMensual: "4000.00", deudaMensual: "0.00",
  resultadoVerificacion: "VERIFICADO", decision: null, comentario: null, fechaDecision: null, idAnalista: null,
  resultado: "OBSERVADO", esUltima: true,
};
const OBSERVADA = { ...DETALLE, evaluaciones: [EVALUACION] };
const APROBADA = {
  ...DETALLE, estado: "APROBADA",
  evaluaciones: [{ ...EVALUACION, limite: "21000.00", regla: "R-A", resultadoRegla: "APROBADO", resultado: "APROBADO",
    ingresoMensual: "5000.00" }],
  historial: [...DETALLE.historial,
    { estado: "APROBADA", fechaHora: "2026-11-15T15:05:00Z", actor: "ana.analista", motivo: null }],
};

function servidor(detalle: unknown) {
  get.mockImplementation(async (url: string) => {
    if (url === "/solicitudes") return { data: [SOLICITUD] };
    if (url === `/solicitudes/${ID}`) return { data: detalle };
    if (url === "/resultados-sol") return { data: { configurado: false, ventanaDias: 7, items: [] } };
    throw new Error(`GET no esperado: ${url}`);
  });
}

async function abrirSolicitud() {
  render(<EvaluacionPage />);
  await userEvent.click(await screen.findByRole("button", { name: `Abrir ${ID}` }));
  await screen.findByRole("table", { name: "Calendario de pagos" });
}

beforeEach(() => {
  get.mockReset();
  post.mockReset();
  perfil.mockReset();
  perfil.mockResolvedValue({ data: ANALISTA });
});

describe("Página del módulo Evaluación", () => {
  it("EV-01 Muestra la bandeja y abre la solicitud con el calendario de SOL", async () => {
    servidor(DETALLE);
    await abrirSolicitud();
    expect(get).toHaveBeenCalledWith("/solicitudes", { params: {} });
    const calendario = screen.getByRole("table", { name: "Calendario de pagos" });
    expect(within(calendario).getAllByRole("row")).toHaveLength(4);   // encabezado, 2 cuotas y total
    expect(within(calendario).getByText("15/12/2026")).toBeInTheDocument();
    expect(within(calendario).getByText("S/ 15,377.11")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Registrar y evaluar" })).toBeInTheDocument();
  });

  it("EV-02 El analista registra la situación financiera y ve el resultado de la regla", async () => {
    servidor(DETALLE);
    post.mockResolvedValue({ data: { idEvaluacion: ID_EVA, idSolicitud: ID, resultado: "APROBADO", regla: "R-A",
      score: 850, limite: "21000.00", ratio: "0.7143", estadoSolicitud: "APROBADA" } });
    await abrirSolicitud();
    get.mockImplementation(async (url: string) => {
      if (url === "/solicitudes") return { data: [{ ...SOLICITUD, estado: "APROBADA" }] };
      if (url === `/solicitudes/${ID}`) return { data: APROBADA };
      throw new Error(`GET no esperado: ${url}`);
    });
    escribir(screen.getByLabelText("Ingreso mensual (S/)"), "5000.00");
    await userEvent.click(screen.getByLabelText(/Verifiqué la situación financiera/));
    await userEvent.click(screen.getByRole("button", { name: "Registrar y evaluar" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith(`/solicitudes/${ID}/evaluaciones`, {
      versionSolicitud: 1, ingresoMensual: "5000.00", deudaMensual: "0.00", riesgo: "BUENO", verificada: true,
    }));
    expect(await screen.findByRole("status")).toHaveTextContent("la regla resultó Aprobado (71.43 %)");
    expect(screen.getByText("S/ 21,000.00")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Revocar aprobación" })).toBeInTheDocument();
  });

  it("EV-03 Un caso OBSERVADO lo decide el analista: aprobar o rechazar, sin devolverlo a SOL", async () => {
    servidor(OBSERVADA);
    post.mockResolvedValue({ data: { idEvaluacion: ID_EVA, idSolicitud: ID, decision: "RECHAZADO",
      estadoSolicitud: "RECHAZADA" } });
    await abrirSolicitud();
    const opciones = within(screen.getByRole("radiogroup", { name: "Decisión" })).getAllByRole("radio");
    expect(opciones.map((o) => (o as HTMLInputElement).value)).toEqual(["APROBADO", "RECHAZADO"]);
    await userEvent.click(screen.getByLabelText("Rechazar"));
    escribir(screen.getByLabelText("Comentario"), "Ingresos sin sustento suficiente.");
    await userEvent.click(screen.getByRole("button", { name: "Registrar decisión" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith(`/evaluaciones/${ID_EVA}/decision`, {
      decision: "RECHAZADO", comentario: "Ingresos sin sustento suficiente.",
    }));
  });

  it("EV-04 El auditor consulta pero no evalúa ni decide", async () => {
    perfil.mockResolvedValue({ data: AUDITOR });
    servidor(OBSERVADA);
    await abrirSolicitud();
    expect(screen.queryByRole("button", { name: "Registrar y evaluar" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Registrar decisión" })).not.toBeInTheDocument();
    expect(screen.getByText(/lo decide un analista/)).toBeInTheDocument();
  });

  it("EV-05 Sin sesión pide iniciarla", async () => {
    perfil.mockRejectedValue(new AxiosError("Unauthorized", "ERR_BAD_REQUEST", undefined, undefined, {
      status: 401, statusText: "", headers: {}, config: {} as never, data: {},
    }));
    render(<EvaluacionPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Tu sesión no está iniciada o ya venció.");
    expect(get).not.toHaveBeenCalled();
  });

  it("EV-06 El error de COREDB se muestra con su mensaje", async () => {
    servidor(OBSERVADA);
    post.mockRejectedValue(new AxiosError("Unprocessable", "ERR_BAD_REQUEST", undefined, undefined, {
      status: 422, statusText: "", headers: {}, config: {} as never,
      data: { error: { code: "ANALISTA_REQUERIDO", message: "El usuario no es un analista registrado." } },
    }));
    await abrirSolicitud();
    escribir(screen.getByLabelText("Comentario"), "Sustento revisado con el cliente.");
    await userEvent.click(screen.getByRole("button", { name: "Registrar decisión" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("El usuario no es un analista registrado.");
  });
});
