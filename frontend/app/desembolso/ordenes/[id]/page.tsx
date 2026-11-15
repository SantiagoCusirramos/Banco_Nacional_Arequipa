"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  Alerta,
  AlertaError,
  Boton,
  Dato,
  EnlaceBoton,
  Giro,
  Insignia,
  InsigniaEstado,
  Tarjeta,
  estiloEntrada,
  td,
  th,
} from "@/app/desembolso/_componentes/ui";
import { api, nuevaClave } from "@/lib/desembolso/api";
import { ETIQUETA_ESTADO, MOTIVOS_CUENTA, dinero, fecha } from "@/lib/desembolso/formato";
import { puede, useSesion } from "@/lib/desembolso/sesion";
import type { CuentaElegible, OrdenDetalle } from "@/lib/desembolso/tipos";

const EDITABLES = ["PREPARADA", "VALIDADA"];
const PASOS = ["Consulta", "Preparación", "Confirmación", "Resultado"];

export default function PaginaOrden() {
  const { id } = useParams<{ id: string }>();
  const [orden, setOrden] = useState<OrdenDetalle | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [paso, setPaso] = useState<"preparacion" | "confirmacion">("preparacion");

  const cargar = useCallback(async () => {
    const r = await api.get<OrdenDetalle>(`ordenes/${id}`);
    setOrden(r.data);
    return r.data;
  }, [id]);

  // Carga inicial: el estado se fija al llegar la respuesta, no durante el efecto.
  useEffect(() => {
    api.get<OrdenDetalle>(`ordenes/${id}`).then((r) => setOrden(r.data)).catch(setError);
  }, [id]);

  if (!orden) {
    return error ? <AlertaError error={error} /> : <p className="flex items-center gap-2 text-sm text-slate-500"><Giro /> Cargando orden…</p>;
  }
  const editable = EDITABLES.includes(orden.estado);
  const indice = !editable ? 3 : paso === "confirmacion" && orden.estado === "VALIDADA" ? 2 : 1;

  return (
    <>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Orden de desembolso</p>
          <h1 className="flex items-center gap-3 text-2xl font-semibold text-slate-900">
            {orden.codigo_orden}
            <InsigniaEstado estado={orden.estado} etiqueta={ETIQUETA_ESTADO[orden.estado]} />
          </h1>
        </div>
        <Pasos actual={indice} />
      </div>
      {error ? <div className="mb-4"><AlertaError error={error} /></div> : null}
      {editable && indice === 1 && (
        <Preparacion orden={orden} onCambio={setOrden} onError={setError} onContinuar={() => setPaso("confirmacion")} />
      )}
      {editable && indice === 2 && (
        <Confirmacion
          orden={orden}
          onVolver={() => setPaso("preparacion")}
          onResultado={(o) => {
            setError(null);
            setOrden(o);
          }}
          onError={async (e) => {
            setError(e);
            await cargar();
          }}
        />
      )}
      {!editable && <Resultado orden={orden} onCambio={setOrden} onError={setError} />}
      <Trazabilidad orden={orden} />
    </>
  );
}

function Pasos({ actual }: { actual: number }) {
  return (
    <ol className="flex items-center gap-2 text-xs font-semibold">
      {PASOS.map((p, i) => (
        <li key={p} className="flex items-center gap-2">
          <span
            className={`grid h-6 w-6 place-items-center rounded-full ${
              i < actual ? "bg-emerald-600 text-white" : i === actual ? "bg-marca-700 text-white" : "bg-slate-200 text-slate-500"
            }`}
          >
            {i < actual ? "✓" : i + 1}
          </span>
          <span className={i === actual ? "text-slate-900" : "text-slate-500"}>{p}</span>
          {i < PASOS.length - 1 && <span className="mx-1 h-px w-6 bg-slate-300" />}
        </li>
      ))}
    </ol>
  );
}

function ResumenCredito({ orden }: { orden: OrdenDetalle }) {
  const a = orden.aprobacion;
  return (
    <Tarjeta titulo="Cliente y crédito">
      <dl className="grid grid-cols-2 gap-x-6 gap-y-4 md:grid-cols-3">
        <Dato etiqueta="Cliente">{a?.cliente_nombre ?? orden.cliente_id}</Dato>
        <Dato etiqueta="Documento">{a?.cliente_documento ?? "—"}</Dato>
        <Dato etiqueta="Crédito">{orden.credito_id}</Dato>
        <Dato etiqueta="Producto">{a?.producto ?? "—"}</Dato>
        <Dato etiqueta="Plazo y tasa">{a ? `${a.plazo_meses} meses · TEA ${a.tasa_tea}%` : "—"}</Dato>
        <Dato etiqueta="Aprobación">
          {orden.aprobacion_id} · v{orden.aprobacion_version}
          {a?.vigente_hasta && <span className="block text-xs text-slate-500">vigente hasta {fecha(a.vigente_hasta, false)}</span>}
        </Dato>
      </dl>
    </Tarjeta>
  );
}

function Check({ ok, texto, detalle }: { ok: boolean | null; texto: string; detalle?: string | null }) {
  return (
    <li className="flex gap-3">
      <span
        className={`mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full text-xs font-bold ${
          ok === null ? "bg-slate-200 text-slate-500" : ok ? "bg-emerald-600 text-white" : "bg-rose-600 text-white"
        }`}
      >
        {ok === null ? "·" : ok ? "✓" : "✕"}
      </span>
      <span>
        <span className="text-sm font-medium text-slate-800">{texto}</span>
        {detalle && <span className="block text-xs text-slate-500">{detalle}</span>}
      </span>
    </li>
  );
}

function Preparacion({
  orden,
  onCambio,
  onError,
  onContinuar,
}: {
  orden: OrdenDetalle;
  onCambio: (o: OrdenDetalle) => void;
  onError: (e: unknown) => void;
  onContinuar: () => void;
}) {
  const sesion = useSesion();
  // Solo quien ejecuta desembolsos consulta las cuentas y actúa; el auditor ve la orden sin acciones.
  const ejecuta = puede(sesion, "DESEMBOLSO_EJECUTAR");
  const [documento, setDocumento] = useState("");
  const [verificado, setVerificado] = useState(false);
  const [validando, setValidando] = useState(false);
  const [cuentas, setCuentas] = useState<CuentaElegible[] | null>(null);
  const [eligiendo, setEligiendo] = useState<string | null>(null);
  const identidad = orden.identidad;

  useEffect(() => {
    if (!ejecuta) return;
    api.get<CuentaElegible[]>(`ordenes/${orden.id}/cuentas-elegibles`).then((r) => setCuentas(r.data)).catch(onError);
  }, [orden.id, onError, ejecuta]);

  async function validarIdentidad() {
    onError(null);
    setValidando(true);
    try {
      const r = await api.post<OrdenDetalle>(`ordenes/${orden.id}/identidad`, {
        metodo: "VERIFICACION_PRESENCIAL",
        numero_documento: documento.trim(),
      });
      setDocumento("");
      setVerificado(false);
      onCambio(r.data);
    } catch (e) {
      onError(e);
      const r = await api.get<OrdenDetalle>(`ordenes/${orden.id}`);
      onCambio(r.data);
    } finally {
      setValidando(false);
    }
  }

  async function elegir(cuentaId: string) {
    onError(null);
    setEligiendo(cuentaId);
    try {
      const r = await api.put<OrdenDetalle>(`ordenes/${orden.id}/cuenta-destino`, { cuenta_id: cuentaId, version: orden.version });
      onCambio(r.data);
    } catch (e) {
      onError(e);
      onCambio((await api.get<OrdenDetalle>(`ordenes/${orden.id}`)).data);
    } finally {
      setEligiendo(null);
    }
  }

  const identidadOk = identidad ? identidad.resultado === "APROBADA" : null;
  const cuentaOk = orden.cuenta_id ? true : null;
  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="space-y-6 lg:col-span-2">
        <ResumenCredito orden={orden} />
        <Tarjeta
          titulo="Identidad del titular"
          accion={identidad && <InsigniaEstado estado={identidad.resultado} etiqueta={identidad.resultado} />}
        >
          <p className="mb-4 text-sm text-slate-600">
            Verificación presencial: revise el documento original del titular y regístrelo. Se compara con el titular del crédito
            según Evaluación. El módulo Clientes todavía no está en el producto, así que no hay validación biométrica.
          </p>
          {identidad?.detalle && (
            <p className="mb-4 text-sm text-slate-700">
              {identidad.detalle}
              {identidad.vence_en && identidadOk && <span className="text-slate-500"> · vigente hasta {fecha(identidad.vence_en)}</span>}
            </p>
          )}
          {ejecuta && (
            <div className="flex flex-wrap items-end gap-3">
              <div>
                <label htmlFor="documento" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">
                  Número del documento presentado
                </label>
                <input
                  id="documento"
                  value={documento}
                  onChange={(e) => setDocumento(e.target.value)}
                  maxLength={12}
                  autoComplete="off"
                  className={`${estiloEntrada} w-56`}
                />
              </div>
              <label className="flex items-center gap-2 pb-2 text-sm text-slate-700">
                <input type="checkbox" checked={verificado} onChange={(e) => setVerificado(e.target.checked)} />
                Verifiqué el documento original y a la persona
              </label>
              <Boton
                variante={identidadOk ? "secundario" : "primario"}
                onClick={validarIdentidad}
                cargando={validando}
                disabled={!verificado || documento.trim().length < 6}
              >
                {identidadOk ? "Validar nuevamente" : "Validar identidad"}
              </Boton>
            </div>
          )}
        </Tarjeta>
        <Tarjeta titulo="Cuenta destino">
          <p className="mb-4 text-sm text-slate-600">
            Cuentas del titular informadas por Cuentas. Solo se admite una cuenta de ahorros individual, activa y en la moneda del crédito.
          </p>
          {!ejecuta ? (
            <p className="text-sm text-slate-700">
              {orden.cuenta_enmascarada ? `Cuenta elegida: ${orden.cuenta_enmascarada}` : "El operador aún no elige la cuenta destino."}
            </p>
          ) : !cuentas ? (
            <p className="flex items-center gap-2 text-sm text-slate-500">
              <Giro /> Consultando cuentas…
            </p>
          ) : (
            <ul className="grid gap-3 md:grid-cols-2">
              {cuentas.map((c) => {
                const elegida = orden.cuenta_id === c.cuenta_id;
                return (
                  <li key={c.cuenta_id}>
                    <button
                      type="button"
                      disabled={!c.elegible || eligiendo !== null}
                      onClick={() => elegir(c.cuenta_id)}
                      className={`w-full rounded-lg p-4 text-left ring-1 transition ${
                        elegida
                          ? "bg-marca-50 ring-2 ring-marca-600"
                          : c.elegible
                            ? "bg-white ring-slate-200 hover:ring-marca-300"
                            : "cursor-not-allowed bg-slate-50 ring-slate-200 opacity-75"
                      }`}
                    >
                      <span className="flex items-center justify-between">
                        <span className="font-mono text-base font-semibold text-slate-900">{c.numero_enmascarado}</span>
                        {eligiendo === c.cuenta_id ? <Giro /> : elegida ? <Insignia tono="info">Seleccionada</Insignia> : null}
                      </span>
                      <span className="mt-1 block text-sm text-slate-600">
                        {c.producto} · {c.moneda} · {c.titularidad.toLowerCase()}
                      </span>
                      <span className="mt-2 block">
                        {c.elegible ? (
                          <Insignia tono="exito">Elegible</Insignia>
                        ) : (
                          <Insignia tono={c.motivo === "MONEDA_DISTINTA" ? "aviso" : "error"}>
                            {MOTIVOS_CUENTA[c.motivo ?? ""] ?? c.motivo}
                          </Insignia>
                        )}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
          {cuentas?.some((c) => c.motivo === "MONEDA_DISTINTA") && (
            <div className="mt-4">
              <Alerta tipo="aviso" titulo="Moneda distinta bloqueada">
                El escenario base no admite conversión de moneda (RN-04). Las cuentas en otra moneda no pueden recibir este desembolso.
              </Alerta>
            </div>
          )}
        </Tarjeta>
      </div>
      <div className="space-y-6">
        <Tarjeta titulo="Importe a desembolsar">
          <dl className="space-y-4">
            <Dato etiqueta="Importe" grande>
              {dinero(orden.importe, orden.moneda)}
            </Dato>
            <p className="text-xs text-slate-500">Importe y moneda derivados de la aprobación; no se editan en agencia (RN-04).</p>
          </dl>
          <ul className="mt-5 space-y-3 border-t border-slate-100 pt-5">
            <Check ok texto="Aprobación habilitada" detalle={`${orden.aprobacion_id} · v${orden.aprobacion_version}`} />
            <Check ok={identidadOk} texto="Identidad del titular" detalle={identidad ? identidad.resultado : "Pendiente"} />
            <Check ok={cuentaOk} texto="Cuenta destino" detalle={orden.cuenta_enmascarada ?? "Pendiente"} />
          </ul>
          {ejecuta && (
            <Boton className="mt-6 w-full" disabled={orden.estado !== "VALIDADA"} onClick={onContinuar}>
              Continuar a confirmación
            </Boton>
          )}
        </Tarjeta>
        <CalendarioSolicitud orden={orden} />
      </div>
    </div>
  );
}

function CalendarioSolicitud({ orden }: { orden: OrdenDetalle }) {
  const [abierto, setAbierto] = useState(false);
  const cuotas = orden.calendario ?? [];
  if (cuotas.length === 0) return null;
  const visibles = abierto ? cuotas : cuotas.slice(0, 3);
  return (
    <Tarjeta
      titulo="Calendario de Solicitud"
      accion={
        cuotas.length > 3 ? (
          <Boton variante="fantasma" onClick={() => setAbierto(!abierto)}>
            {abierto ? "Ver menos" : `Ver las ${cuotas.length}`}
          </Boton>
        ) : null
      }
    >
      <p className="mb-3 text-xs text-slate-500">
        Lo arma Solicitud (RN-SOL-006) y se entrega sin cambios a Cobranza al confirmar el desembolso.
      </p>
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
            <th className="py-1 pr-2">N.°</th>
            <th className="py-1 pr-2">Vence</th>
            <th className="py-1 text-right">Cuota</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {visibles.map((c) => (
            <tr key={c.numeroCuota}>
              <td className="py-1.5 pr-2">{c.numeroCuota}</td>
              <td className="py-1.5 pr-2">{fecha(c.fechaVencimiento, false)}</td>
              <td className="tabular py-1.5 text-right font-medium">{dinero(c.cuotaTotal, orden.moneda)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Tarjeta>
  );
}

function Confirmacion({
  orden,
  onVolver,
  onResultado,
  onError,
}: {
  orden: OrdenDetalle;
  onVolver: () => void;
  onResultado: (o: OrdenDetalle) => void;
  onError: (e: unknown) => void;
}) {
  const [enviando, setEnviando] = useState(false);
  const a = orden.aprobacion;

  async function confirmar() {
    setEnviando(true);
    try {
      const r = await api.post<OrdenDetalle>(
        `ordenes/${orden.id}/confirmacion`,
        { version: orden.version },
        { headers: { "X-Idempotency-Key": orden.idempotency_key } },
      );
      onResultado(r.data);
    } catch (e) {
      await onError(e);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <Tarjeta titulo="Confirmación del desembolso">
        <dl className="grid grid-cols-2 gap-x-8 gap-y-5">
          <Dato etiqueta="Cliente">
            {a?.cliente_nombre ?? orden.cliente_id}
            <span className="block text-xs text-slate-500">DNI {a?.cliente_documento ?? "—"}</span>
          </Dato>
          <Dato etiqueta="Crédito">
            {orden.credito_id}
            <span className="block text-xs text-slate-500">{a?.producto}</span>
          </Dato>
          <Dato etiqueta="Cuenta destino">
            <span className="font-mono text-base font-semibold">{orden.cuenta_enmascarada}</span>
          </Dato>
          <Dato etiqueta="Moneda">{orden.moneda === "USD" ? "Dólares (USD)" : "Soles (PEN)"}</Dato>
          <div className="col-span-2 rounded-lg bg-marca-50 px-5 py-4">
            <Dato etiqueta="Importe a abonar" grande>
              {dinero(orden.importe, orden.moneda)}
            </Dato>
          </div>
        </dl>
        <div className="mt-6">
          <Alerta tipo="aviso" titulo="Antes de confirmar">
            Se revalidarán la aprobación, la cuenta y la identidad, y se solicitará el abono a Cuentas una sola vez. Si la respuesta no
            llega, la orden quedará por verificar y no se generará otro abono.
          </Alerta>
        </div>
        <div className="mt-6 flex justify-between">
          <Boton variante="secundario" onClick={onVolver} disabled={enviando}>
            Volver a preparación
          </Boton>
          <Boton onClick={confirmar} cargando={enviando}>
            Confirmar desembolso
          </Boton>
        </div>
      </Tarjeta>
    </div>
  );
}

function Resultado({ orden, onCambio, onError }: { orden: OrdenDetalle; onCambio: (o: OrdenDetalle) => void; onError: (e: unknown) => void }) {
  const [verificando, setVerificando] = useState(false);
  const evento = orden.eventos.find((e) => e.tipo === "desembolso.confirmado");
  const aviso = orden.eventos.find((e) => e.tipo === "aprobacion.desembolsada");

  async function verificar() {
    onError(null);
    setVerificando(true);
    try {
      onCambio((await api.post<OrdenDetalle>(`ordenes/${orden.id}/verificacion`)).data);
    } catch (e) {
      onError(e);
    } finally {
      setVerificando(false);
    }
  }

  const encabezados: Record<string, { tono: string; titulo: string; texto: string }> = {
    CONFIRMADA: {
      tono: "bg-emerald-600",
      titulo: "Desembolso confirmado",
      texto: "Cuentas confirmó el abono en la cuenta del titular.",
    },
    POR_VERIFICAR: {
      tono: "bg-amber-500",
      titulo: "Resultado en verificación",
      texto: "Cuentas no respondió a tiempo. No se generará otro abono: consulte el resultado por la misma referencia.",
    },
    EN_PROCESO: {
      tono: "bg-amber-500",
      titulo: "Desembolso en proceso",
      texto: "La solicitud de abono está en curso.",
    },
    RECHAZADA: { tono: "bg-rose-600", titulo: "Desembolso rechazado", texto: orden.motivo_rechazo ?? "La orden fue rechazada." },
    REVERTIDA: { tono: "bg-violet-600", titulo: "Desembolso revertido", texto: "El abono fue revertido mediante una operación independiente." },
  };
  const e = encabezados[orden.estado];
  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="lg:col-span-2">
        <section className="overflow-hidden rounded-xl bg-white shadow-sm ring-1 ring-slate-200">
          <div className={`${e.tono} px-6 py-5 text-white`}>
            <p className="text-xl font-semibold">{e.titulo}</p>
            <p className="mt-1 text-sm text-white/90">{e.texto}</p>
          </div>
          <dl className="grid grid-cols-2 gap-x-8 gap-y-5 p-6 md:grid-cols-3">
            <Dato etiqueta="Importe" grande>
              {dinero(orden.importe, orden.moneda)}
            </Dato>
            <Dato etiqueta="Operación financiera">
              <span className="font-mono">{orden.operacion_financiera_id ?? "—"}</span>
            </Dato>
            <Dato etiqueta="Fecha efectiva">{fecha(orden.fecha_efectiva)}</Dato>
            <Dato etiqueta="Cliente">{orden.aprobacion?.cliente_nombre ?? orden.cliente_id}</Dato>
            <Dato etiqueta="Cuenta destino">
              <span className="font-mono">{orden.cuenta_enmascarada ?? "—"}</span>
            </Dato>
            <Dato etiqueta="Crédito">{orden.credito_id}</Dato>
          </dl>
          <div className="flex flex-wrap gap-3 border-t border-slate-100 px-6 py-4">
            {orden.acciones.includes("VERIFICAR") && (
              <Boton onClick={verificar} cargando={verificando}>
                Verificar resultado
              </Boton>
            )}
            {orden.acciones.includes("CONSTANCIA") && (
              <EnlaceBoton href={`/desembolso/ordenes/${orden.id}/constancia`} variante="primario">
                Ver constancia
              </EnlaceBoton>
            )}
            <EnlaceBoton href="/desembolso">Nueva consulta</EnlaceBoton>
          </div>
        </section>
        {orden.acciones.includes("SOLICITAR_REVERSION") && <SolicitarReversion orden={orden} onCambio={onCambio} onError={onError} />}
      </div>
      <Tarjeta titulo="Entrega a Cobranza">
        <div className="space-y-3">
          <p className="flex items-center justify-between text-sm">
            Estado <InsigniaEstado estado={orden.entrega_estado} />
          </p>
          {evento ? (
            <>
              <p className="text-sm text-slate-600">Evento {evento.tipo} · intentos {evento.intentos}</p>
              {evento.confirmacion_id && (
                <p className="text-sm">
                  Acuse <span className="font-mono font-semibold">{evento.confirmacion_id}</span>
                </p>
              )}
              {evento.ultimo_error && <p className="text-xs text-rose-600">{evento.ultimo_error}</p>}
            </>
          ) : (
            <p className="text-sm text-slate-500">Se genera al confirmar el abono.</p>
          )}
          {aviso && (
            <p className="flex items-center justify-between border-t border-slate-100 pt-3 text-sm">
              Aviso a Evaluación <InsigniaEstado estado={aviso.estado} />
            </p>
          )}
          <p className="border-t border-slate-100 pt-3 text-xs text-slate-500">
            Una falla de entrega no cambia el estado financiero: el evento se reintenta hasta recibir el acuse (RN-08). Cobranza recibe el
            calendario de Solicitud sin cambios.
          </p>
        </div>
      </Tarjeta>
    </div>
  );
}

function SolicitarReversion({ orden, onCambio, onError }: { orden: OrdenDetalle; onCambio: (o: OrdenDetalle) => void; onError: (e: unknown) => void }) {
  const [motivo, setMotivo] = useState("");
  const [enviando, setEnviando] = useState(false);
  async function solicitar() {
    setEnviando(true);
    try {
      await api.post(`ordenes/${orden.id}/reversiones`, { motivo, origen: "SOLICITUD_SERVICIO" }, { headers: { "X-Idempotency-Key": nuevaClave() } });
      onCambio((await api.get<OrdenDetalle>(`ordenes/${orden.id}`)).data);
    } catch (e) {
      onError(e);
    } finally {
      setEnviando(false);
    }
  }
  return (
    <Tarjeta titulo="Solicitar reversión" className="mt-6">
      <p className="mb-3 text-sm text-slate-600">La reversión requiere la autorización de un supervisor distinto del solicitante.</p>
      <div className="flex gap-3">
        <input value={motivo} onChange={(e) => setMotivo(e.target.value)} placeholder="Motivo de la reversión" className={estiloEntrada} />
        <Boton variante="peligro" disabled={motivo.trim().length < 5} cargando={enviando} onClick={solicitar}>
          Solicitar
        </Boton>
      </div>
    </Tarjeta>
  );
}

function Trazabilidad({ orden }: { orden: OrdenDetalle }) {
  const [bitacora, setBitacora] = useState<{ id: number; actor_id: string; accion: string; resultado: string; creado_en: string }[] | null>(
    null,
  );
  return (
    <Tarjeta
      titulo="Trazabilidad"
      className="mt-6"
      accion={
        orden.acciones.includes("VER_AUDITORIA") && !bitacora ? (
          <Boton variante="fantasma" onClick={() => api.get(`ordenes/${orden.id}/auditoria`).then((r) => setBitacora(r.data))}>
            Ver bitácora
          </Boton>
        ) : null
      }
    >
      <p className="mb-3 text-xs text-slate-500">
        Correlación <span className="font-mono">{orden.correlation_id}</span> · preparada por {orden.usuario_preparacion}
        {orden.usuario_confirmacion && ` · confirmada por ${orden.usuario_confirmacion}`}
      </p>
      <div className="-mx-5 overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-100">
          <thead className="bg-slate-50">
            <tr>
              <th className={th}>Validación</th>
              <th className={th}>Fase</th>
              <th className={th}>Proveedor</th>
              <th className={th}>Resultado</th>
              <th className={th}>Detalle</th>
              <th className={th}>Fecha</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {orden.validaciones.map((v) => (
              <tr key={v.id}>
                <td className={`${td} font-medium`}>{v.tipo}</td>
                <td className={td}>{v.fase === "EJECUCION" ? "Ejecución" : "Preparación"}</td>
                <td className={td}>{v.proveedor}</td>
                <td className={td}>
                  <InsigniaEstado estado={v.resultado} />
                </td>
                <td className={`${td} max-w-sm text-xs`}>{v.detalle}</td>
                <td className={`${td} whitespace-nowrap text-xs`}>{fecha(v.creado_en)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {bitacora && (
        <div className="mt-5">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Bitácora (solo inserción)</p>
          <ul className="space-y-1.5 text-sm">
            {bitacora.map((b) => (
              <li key={b.id} className="flex gap-3">
                <span className="w-32 shrink-0 text-xs text-slate-500">{fecha(b.creado_en)}</span>
                <span className="w-28 shrink-0 font-medium">{b.accion}</span>
                <span className="w-44 shrink-0">{b.resultado}</span>
                <span className="text-slate-500">{b.actor_id}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      <p className="mt-4 text-xs text-slate-500">
        <Link href="/desembolso/ordenes" className="font-semibold text-marca-600 hover:underline">
          ← Volver al historial
        </Link>
      </p>
    </Tarjeta>
  );
}
