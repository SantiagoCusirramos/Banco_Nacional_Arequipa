"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { VerificarDocumento } from "@/app/desembolso/_componentes/Identidad";
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
import { etiquetaSolicitud } from "@/lib/continuidad";
import { api } from "@/lib/desembolso/api";
import { ETIQUETA_ESTADO, MOTIVOS_CUENTA, dinero, fecha, porcentaje } from "@/lib/desembolso/formato";
import { useSesion } from "@/lib/desembolso/sesion";
import type { Confirmada, Cuenta, OrdenDetalle, Validacion, Verificacion } from "@/lib/desembolso/tipos";

const EDITABLES = ["PREPARADA", "VALIDADA"];
const PASOS = ["Preparación", "Validación", "Confirmación", "Resultado"];

/** La última validación de un tipo (COREDB las devuelve en orden de registro). */
function ultima(validaciones: Validacion[], tipo: string): Validacion | undefined {
  return validaciones.filter((v) => v.tipo === tipo).at(-1);
}

export default function PaginaOrden() {
  const { id } = useParams<{ id: string }>();
  const [orden, setOrden] = useState<OrdenDetalle | null>(null);
  const [error, setError] = useState<unknown>(null);

  const cargar = useCallback(async () => {
    const r = await api.get<OrdenDetalle>(`ordenes/${id}`);
    setOrden(r.data);
  }, [id]);

  useEffect(() => {
    api.get<OrdenDetalle>(`ordenes/${id}`).then((r) => setOrden(r.data)).catch(setError);
  }, [id]);

  if (!orden) {
    return error ? <AlertaError error={error} /> : <p className="flex items-center gap-2 text-sm text-slate-500"><Giro /> Cargando orden…</p>;
  }
  const editable = EDITABLES.includes(orden.estado);
  const indice = !editable ? 3 : orden.estado === "VALIDADA" ? 2 : 1;

  // Tras una acción se vuelve a leer la orden, también si falló: COREDB tiene el estado verdadero.
  async function actuar(accion: () => Promise<unknown>) {
    setError(null);
    try {
      await accion();
    } catch (e) {
      setError(e);
    }
    try {
      await cargar();
    } catch (e) {
      setError(e);
    }
  }

  return (
    <>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Orden de desembolso</p>
          <h1 className="flex items-center gap-3 text-2xl font-semibold text-slate-900">
            {orden.codigoOrden}
            <InsigniaEstado estado={orden.estado} etiqueta={ETIQUETA_ESTADO[orden.estado]} />
          </h1>
        </div>
        <Pasos actual={indice} />
      </div>
      {error ? <div className="mb-4"><AlertaError error={error} /></div> : null}
      {editable ? <Preparacion orden={orden} actuar={actuar} onError={setError} /> : <Resultado orden={orden} />}
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
  return (
    <Tarjeta titulo="Cliente y crédito">
      <dl className="grid grid-cols-2 gap-x-6 gap-y-4 md:grid-cols-3">
        <Dato etiqueta="Cliente">{orden.codCliente}</Dato>
        <Dato etiqueta="Solicitud">
          <span className="font-mono text-xs">{etiquetaSolicitud(orden)}</span>
        </Dato>
        <Dato etiqueta="Plazo y tasa">
          {orden.plazoMeses} meses{orden.calendario ? ` · ${porcentaje(orden.calendario.tasa)}` : ""}
        </Dato>
        <Dato etiqueta="Canal">{orden.canal === "HB" ? "Home banking" : "Ventanilla"}</Dato>
        <Dato etiqueta="Preparada por">{orden.usuarioPreparacion}</Dato>
        <Dato etiqueta="Solicitud en COREDB">
          <InsigniaEstado estado={orden.estadoSolicitud} />
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
  actuar,
  onError,
}: {
  orden: OrdenDetalle;
  actuar: (accion: () => Promise<unknown>) => Promise<void>;
  onError: (e: unknown) => void;
}) {
  const sesion = useSesion();
  // Solo quien desembolsa consulta las cuentas y actúa; el auditor ve la orden sin acciones.
  const opera = sesion.puedeOperar;
  const [cuentas, setCuentas] = useState<Cuenta[] | null>(null);
  const [eligiendo, setEligiendo] = useState<string | null>(null);
  const [confirmando, setConfirmando] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [rechazando, setRechazando] = useState(false);
  const identidad = ultima(orden.validaciones, "IDENTIDAD");
  const cuenta = ultima(orden.validaciones, "CUENTA");

  useEffect(() => {
    if (!opera) return;
    api
      .get<Cuenta[]>(`clientes/${encodeURIComponent(orden.codCliente)}/cuentas`, { params: { moneda: orden.moneda } })
      .then((r) => setCuentas(r.data))
      .catch(onError);
  }, [orden.codCliente, orden.moneda, onError, opera]);

  async function registrarIdentidad(v: Verificacion) {
    if (v.resultado !== "APROBADO") {
      onError(new Error(v.motivo ?? "No se pudo verificar la identidad: el documento no corresponde a un cliente activo."));
      return;
    }
    await actuar(() =>
      api.post(`ordenes/${orden.idOrden}/validaciones`, {
        tipo: "IDENTIDAD",
        resultado: "APROBADA",
        referenciaEvidencia: String(v.idValidacion),
        detalle: "Documento original verificado en ventanilla.",
      }),
    );
  }

  async function elegir(numCuenta: string) {
    setEligiendo(numCuenta);
    await actuar(() => api.put(`ordenes/${orden.idOrden}/cuenta`, { numCuenta }));
    setEligiendo(null);
  }

  async function confirmar() {
    setConfirmando(true);
    await actuar(() => api.post<Confirmada>(`ordenes/${orden.idOrden}/confirmacion`));
    setConfirmando(false);
  }

  async function rechazar() {
    setRechazando(true);
    await actuar(() => api.post(`ordenes/${orden.idOrden}/rechazo`, { motivo: motivo.trim() }));
    setRechazando(false);
  }

  const identidadOk = identidad ? identidad.resultado === "APROBADA" : null;
  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="space-y-6 lg:col-span-2">
        <ResumenCredito orden={orden} />
        <Tarjeta titulo="Identidad del titular" accion={identidad && <InsigniaEstado estado={identidad.resultado} />}>
          <p className="mb-4 text-sm text-slate-600">
            Verificación en ventanilla: revise el documento original y a la persona. Vale el mismo día; si la orden se confirma otro día,
            hay que verificarla de nuevo.
          </p>
          {identidad && (
            <p className="mb-4 text-sm text-slate-700">
              Verificación n.° {identidad.referenciaEvidencia} · {fecha(identidad.fecha)}
            </p>
          )}
          {opera && (
            <VerificarDocumento
              boton={identidadOk ? "Verificar nuevamente" : "Validar identidad"}
              onVerificado={registrarIdentidad}
              onError={onError}
            />
          )}
        </Tarjeta>
        <Tarjeta titulo="Cuenta de abono">
          <p className="mb-4 text-sm text-slate-600">
            Cuenta elegida: <span className="font-mono font-semibold text-slate-900">{orden.numCuenta}</span>. Solo se admite una cuenta de
            ahorros individual, activa, del titular y en la moneda del crédito.
          </p>
          {opera &&
            (!cuentas ? (
              <p className="flex items-center gap-2 text-sm text-slate-500">
                <Giro /> Consultando cuentas…
              </p>
            ) : (
              <ul className="grid gap-3 md:grid-cols-2">
                {cuentas.map((c) => {
                  const elegida = orden.numCuenta === c.numCuenta;
                  return (
                    <li key={c.numCuenta}>
                      <button
                        type="button"
                        disabled={!c.elegible || elegida || eligiendo !== null}
                        onClick={() => elegir(c.numCuenta)}
                        className={`w-full rounded-lg p-4 text-left ring-1 transition ${
                          elegida
                            ? "bg-marca-50 ring-2 ring-marca-600"
                            : c.elegible
                              ? "bg-white ring-slate-200 hover:ring-marca-300"
                              : "cursor-not-allowed bg-slate-50 ring-slate-200 opacity-75"
                        }`}
                      >
                        <span className="flex items-center justify-between">
                          <span className="font-mono text-base font-semibold text-slate-900">{c.numCuenta}</span>
                          {eligiendo === c.numCuenta ? <Giro /> : elegida ? <Insignia tono="info">Seleccionada</Insignia> : null}
                        </span>
                        <span className="mt-1 block text-sm text-slate-600">
                          {c.moneda} · {c.regimen.toLowerCase().replaceAll("_", " ")}
                        </span>
                        <span className="mt-2 block">
                          {c.elegible ? (
                            <Insignia tono="exito">Elegible</Insignia>
                          ) : (
                            <Insignia tono="error">{MOTIVOS_CUENTA[c.motivo ?? ""] ?? c.motivo}</Insignia>
                          )}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            ))}
        </Tarjeta>
      </div>
      <div className="space-y-6">
        <Tarjeta titulo="Importe a desembolsar">
          <Dato etiqueta="Importe" grande>
            {dinero(orden.importe, orden.moneda)}
          </Dato>
          <p className="mt-2 text-xs text-slate-500">El monto aprobado; no se edita en agencia.</p>
          <ul className="mt-5 space-y-3 border-t border-slate-100 pt-5">
            <Check ok texto="Aprobación vigente" detalle={`Solicitud ${orden.estadoSolicitud.toLowerCase()}`} />
            <Check ok={identidadOk} texto="Identidad del titular" detalle={identidad ? identidad.resultado : "Pendiente"} />
            <Check ok={cuenta ? cuenta.resultado === "APROBADA" : null} texto="Cuenta de abono" detalle={orden.numCuenta} />
          </ul>
          {opera && (
            <>
              <div className="mt-5">
                <Alerta tipo="aviso" titulo="Al confirmar">
                  COREDB abona la cuenta una sola vez, crea el crédito con su calendario oficial y deja la solicitud desembolsada. Si la
                  respuesta no llega, confirme otra vez: devuelve el mismo crédito, sin otro abono.
                </Alerta>
              </div>
              <Boton className="mt-4 w-full" disabled={orden.estado !== "VALIDADA"} cargando={confirmando} onClick={confirmar}>
                Confirmar desembolso
              </Boton>
              <div className="mt-6 border-t border-slate-100 pt-4">
                <label htmlFor="motivo-rechazo" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">
                  Motivo del rechazo
                </label>
                <input id="motivo-rechazo" value={motivo} onChange={(e) => setMotivo(e.target.value)} maxLength={255} className={estiloEntrada} />
                <Boton variante="peligro" className="mt-2 w-full" disabled={motivo.trim().length < 5} cargando={rechazando} onClick={rechazar}>
                  Rechazar orden
                </Boton>
              </div>
            </>
          )}
        </Tarjeta>
        <CalendarioDeLaSolicitud orden={orden} />
      </div>
    </div>
  );
}

function CalendarioDeLaSolicitud({ orden }: { orden: OrdenDetalle }) {
  const [abierto, setAbierto] = useState(false);
  const cuotas = orden.calendario?.cuotas ?? [];
  if (cuotas.length === 0) return null;
  const visibles = abierto ? cuotas : cuotas.slice(0, 3);
  const oficial = orden.calendario?.tipo === "OFICIAL";
  return (
    <Tarjeta
      titulo={oficial ? "Calendario oficial del crédito" : "Calendario de Solicitud"}
      accion={
        cuotas.length > 3 ? (
          <Boton variante="fantasma" onClick={() => setAbierto(!abierto)}>
            {abierto ? "Ver menos" : `Ver las ${cuotas.length}`}
          </Boton>
        ) : null
      }
    >
      <p className="mb-3 text-xs text-slate-500">
        {oficial
          ? "Copia sin cambios del calendario de Solicitud (RN-SOL-006), creada al confirmar el desembolso."
          : "Lo arma Solicitud (RN-SOL-006); al confirmar, COREDB lo copia sin cambios como calendario oficial del crédito."}
      </p>
      <div className="overflow-x-auto">
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
      </div>
    </Tarjeta>
  );
}

function Resultado({ orden }: { orden: OrdenDetalle }) {
  const confirmada = orden.estado === "CONFIRMADA";
  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="lg:col-span-2">
        <section className="overflow-hidden rounded-xl bg-white shadow-sm ring-1 ring-slate-200">
          <div className={`${confirmada ? "bg-emerald-600" : "bg-rose-600"} px-6 py-5 text-white`}>
            <p className="text-xl font-semibold">{confirmada ? "Desembolso confirmado" : `Orden ${ETIQUETA_ESTADO[orden.estado].toLowerCase()}`}</p>
            <p className="mt-1 text-sm text-white/90">
              {confirmada
                ? "COREDB abonó la cuenta del titular, creó el crédito y dejó la solicitud desembolsada."
                : orden.motivoRechazo ?? "La orden no se desembolsó. La aprobación admite otra orden mientras siga vigente."}
            </p>
          </div>
          <dl className="grid grid-cols-2 gap-x-8 gap-y-5 p-6 md:grid-cols-3">
            <Dato etiqueta="Importe" grande>
              {dinero(orden.importe, orden.moneda)}
            </Dato>
            <Dato etiqueta="Crédito">{orden.codCredito ?? "—"}</Dato>
            <Dato etiqueta="Fecha">{fecha(orden.fechaActualizacion)}</Dato>
            <Dato etiqueta="Cliente">{orden.codCliente}</Dato>
            <Dato etiqueta="Cuenta de abono">
              <span className="font-mono">{orden.numCuenta}</span>
            </Dato>
            <Dato etiqueta="Abono">
              <span className="font-mono text-xs">{orden.uuidTransaccionAbono ?? "—"}</span>
            </Dato>
          </dl>
          <div className="flex flex-wrap gap-3 border-t border-slate-100 px-6 py-4">
            {confirmada && (
              <EnlaceBoton href={`/desembolso/ordenes/${orden.idOrden}/constancia`} variante="primario">
                Ver constancia
              </EnlaceBoton>
            )}
            <EnlaceBoton href="/desembolso">Nuevo desembolso</EnlaceBoton>
            {confirmada && (
              <Link href={`/billetera?codCliente=${encodeURIComponent(orden.codCliente)}&numCuenta=${encodeURIComponent(orden.numCuenta)}`} className="rounded-lg px-4 py-2 text-sm font-semibold text-marca-700 ring-1 ring-marca-200 hover:bg-marca-50">
                Afiliar a Chaski
              </Link>
            )}
          </div>
        </section>
      </div>
      <CalendarioDeLaSolicitud orden={orden} />
    </div>
  );
}

function Trazabilidad({ orden }: { orden: OrdenDetalle }) {
  return (
    <Tarjeta titulo="Trazabilidad" className="mt-6">
      <div className="-mx-5 overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-100">
          <thead className="bg-slate-50">
            <tr>
              <th className={th}>Validación</th>
              <th className={th}>Resultado</th>
              <th className={th}>Evidencia</th>
              <th className={th}>Detalle</th>
              <th className={th}>Fecha</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {orden.validaciones.map((v) => (
              <tr key={v.idValidacion}>
                <td className={`${td} font-medium`}>{v.tipo}</td>
                <td className={td}>
                  <InsigniaEstado estado={v.resultado} />
                </td>
                <td className={`${td} font-mono text-xs`}>{v.referenciaEvidencia}</td>
                <td className={`${td} max-w-sm text-xs`}>{v.detalle}</td>
                <td className={`${td} whitespace-nowrap text-xs`}>{fecha(v.fecha)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mb-2 mt-5 text-xs font-semibold uppercase tracking-wide text-slate-500">Bitácora</p>
      <ul className="space-y-1.5 text-sm">
        {orden.eventos.map((e, i) => (
          <li key={`${e.fechaHora}-${i}`} className="flex gap-3">
            <span className="w-32 shrink-0 text-xs text-slate-500">{fecha(e.fechaHora)}</span>
            <span className="w-40 shrink-0 font-medium">{e.accion}</span>
            <span className="w-28 shrink-0">{e.resultado ?? ""}</span>
            <span className="text-slate-500">{e.actor}</span>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-xs text-slate-500">
        <Link href="/desembolso/ordenes" className="font-semibold text-marca-600 hover:underline">
          ← Volver a las órdenes
        </Link>
      </p>
    </Tarjeta>
  );
}
