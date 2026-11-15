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

const ID = "EVA-2026-000001";
const ANALISTA = { id_usuario: "u-1", username: "ana.analista", rol: "ANALISTA", modulo: null,
  acciones: ["APROBAR_CREDITO", "EVALUAR_CREDITO", "VER_CREDITO"] };
const AUDITOR = { id_usuario: "u-2", username: "aldo.auditor", rol: "AUDITOR", modulo: null,
  acciones: ["VER_AUDITORIA", "VER_CREDITO"] };

const EVALUACION = {
  idEvaluacion: ID, idSolicitud: "0198b000-0000-7000-8000-000000000001", versionSolicitud: 1, ronda: 1,
  estado: "PENDIENTE", version: 1,
  cliente: { idCliente: "CLI000000001", nombre: "Juan Perez Quispe", tipoDocumento: "DNI", numeroDocumento: "****0001" },
  producto: "Crédito Personal", destino: "Mejoras en la vivienda", montoSolicitado: "15000.00", moneda: "PEN",
  plazoMeses: 2, tasaTea: "0.2200", motor: null, motivo: null, decididoPor: null, decididoEn: null,
  recibidoEn: "2026-11-15T15:00:00+00:00", actualizadoEn: "2026-11-15T15:00:00+00:00",
};
const DETALLE = {
  ...EVALUACION,
  cliente: { ...EVALUACION.cliente, numeroDocumento: "70000001" },
  expediente: {
    idOperacion: "op-1", acuse: `ACK-${ID}`, versionContrato: "CR-INT-02-PROPUESTA-v2", actorEnvio: "asesor.bna",
    simulado: false, recibidoEn: "2026-11-15T15:00:00+00:00", fechaBase: "2026-11-15", garantias: [], fiadores: 0,
    politica: { version: "SOL-DEMO-2026-01", estadoAprobacion: "PROPUESTO_PENDIENTE_COMITE" },
    calendario: {
      estado: "PRELIMINAR", cuotaReferencial: "7623.33", interesesTotales: "377.11", totalPagar: "15377.11",
      cuotas: [
        { numeroCuota: 1, fechaVencimiento: "2026-12-15", amortizacion: "7373.33", interes: "250.00",
          cuotaTotal: "7623.33", saldoFinal: "7626.67" },
        { numeroCuota: 2, fechaVencimiento: "2027-01-14", amortizacion: "7626.67", interes: "127.11",
          cuotaTotal: "7753.78", saldoFinal: "0.00" },
      ],
    },
  },
  situacionFinanciera: null, aprobacion: null, envioSol: null,
  historial: [{ id: 1, fecha: "2026-11-15T15:00:00+00:00", evento: "EXPEDIENTE_RECIBIDO", actor: "SOL:asesor.bna",
    idEvaluacion: ID, idAprobacion: null, idCorrelacion: "c-1", detalle: null }],
};
const MOTOR = { resultado: "APROBADO", score: 850, limite: "21000.00", ratio: "0.7143", regla: "RN-EVA-002-P · demo v1" };
const APROBADO = {
  ...DETALLE, estado: "APROBADO", version: 2, motor: MOTOR, decididoPor: "MOTOR",
  decididoEn: "2026-11-15T15:05:00+00:00", motivo: "Aprobado por la regla RN-EVA-002-P · demo v1. Monto / límite: 71.43 %.",
  situacionFinanciera: { ingresoMensual: "5000.00", deudaMensual: "0.00", riesgo: "BUENO", verificada: true,
    registradoPor: "ana.analista", registradoEn: "2026-11-15T15:05:00+00:00" },
  aprobacion: { idAprobacion: "APR-2026-000001", version: 1, codCredito: "CRE-2026-000001", estado: "VIGENTE",
    montoAprobado: "15000.00", moneda: "PEN", plazoMeses: 2, tasaTea: "0.2200", vigenteHasta: "2026-12-15T15:05:00+00:00",
    aprobadaPor: "MOTOR", aprobadaEn: "2026-11-15T15:05:00+00:00", desembolso: null, revocacion: null },
  envioSol: { idOperacion: "op-res-1", idEvaluacion: ID, interfaz: "CR-INT-03", decision: "APROBADO", estado: "PENDIENTE",
    intentos: 0, siguienteIntento: "2026-11-15T15:05:00+00:00", ultimoError: null,
    creadoEn: "2026-11-15T15:05:00+00:00", entregadoEn: null },
};
const EN_REVISION = { ...DETALLE, estado: "EN_REVISION", version: 2, motor: { ...MOTOR, resultado: "OBSERVADO", ratio: "0.8929" } };

function servidor(detalle: unknown, conteos: Record<string, number> = { PENDIENTE: 1 }) {
  get.mockImplementation(async (url: string) => {
    if (url === "/evaluaciones") return { data: { items: [EVALUACION], conteos } };
    if (url === `/evaluaciones/${ID}`) return { data: detalle };
    throw new Error(`GET no esperado: ${url}`);
  });
}

async function abrirExpediente() {
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
  it("EV-01 Muestra la bandeja y abre el expediente con el calendario de SOL", async () => {
    servidor(DETALLE);
    await abrirExpediente();
    expect(get).toHaveBeenCalledWith("/evaluaciones", { params: {} });
    const calendario = screen.getByRole("table", { name: "Calendario de pagos" });
    expect(within(calendario).getAllByRole("row")).toHaveLength(4);   // encabezado, 2 cuotas y total
    expect(within(calendario).getByText("15/12/2026")).toBeInTheDocument();
    expect(within(calendario).getByText("S/ 15,377.11")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Registrar y evaluar" })).toBeInTheDocument();
  });

  it("EV-02 El analista registra la situación financiera y ve la aprobación", async () => {
    servidor(DETALLE);
    post.mockResolvedValue({ data: APROBADO });
    await abrirExpediente();
    escribir(screen.getByLabelText("Ingreso mensual (S/)"), "5000.00");
    await userEvent.click(screen.getByLabelText(/Verifiqué la situación financiera/));
    await userEvent.click(screen.getByRole("button", { name: "Registrar y evaluar" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith(`/evaluaciones/${ID}/situacion-financiera`, {
      ingresoMensual: "5000.00", deudaMensual: "0.00", riesgo: "BUENO", verificada: true, version: 1,
    }));
    expect(await screen.findByRole("status")).toHaveTextContent("la evaluación resultó Aprobado");
    expect(screen.getByText("CRE-2026-000001")).toBeInTheDocument();
    expect(screen.getByText("71.43 %")).toBeInTheDocument();
  });

  it("EV-03 Un caso en revisión lo decide el analista", async () => {
    servidor(EN_REVISION, { EN_REVISION: 1 });
    post.mockResolvedValue({ data: { ...EN_REVISION, estado: "OBSERVADO", version: 3 } });
    await abrirExpediente();
    await userEvent.click(screen.getByLabelText("Observar: Solicitud corrige"));
    escribir(screen.getByLabelText("Observaciones para Solicitud"), "Precisar el destino declarado.");
    await userEvent.click(screen.getByRole("button", { name: "Registrar decisión" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith(`/evaluaciones/${ID}/decision`, {
      decision: "OBSERVADO", observaciones: "Precisar el destino declarado.", version: 2,
    }));
  });

  it("EV-04 El auditor consulta pero no evalúa ni decide", async () => {
    perfil.mockResolvedValue({ data: AUDITOR });
    servidor(DETALLE);
    await abrirExpediente();
    expect(screen.queryByRole("button", { name: "Registrar y evaluar" })).not.toBeInTheDocument();
    expect(screen.getByText(/un analista debe registrar la situación financiera/)).toBeInTheDocument();
  });

  it("EV-05 Sin sesión pide iniciarla", async () => {
    perfil.mockRejectedValue(new AxiosError("Unauthorized", "ERR_BAD_REQUEST", undefined, undefined, {
      status: 401, statusText: "", headers: {}, config: {} as never, data: {},
    }));
    render(<EvaluacionPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Tu sesión no está iniciada o ya venció.");
    expect(get).not.toHaveBeenCalled();
  });
});
