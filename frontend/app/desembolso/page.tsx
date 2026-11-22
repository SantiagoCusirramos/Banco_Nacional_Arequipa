"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useRef, useState } from "react";
import { VerificarDocumento } from "@/app/desembolso/_componentes/Identidad";
import { Alerta, AlertaError, Boton, Encabezado, FilaVacia, Insignia, InsigniaEstado, Tarjeta, estiloEntrada, td, th } from "@/app/desembolso/_componentes/ui";
import { api, nuevaClave } from "@/lib/desembolso/api";
import { ETIQUETA_ESTADO, MOTIVOS_CUENTA, dinero, fecha } from "@/lib/desembolso/formato";
import { useSesion } from "@/lib/desembolso/sesion";
import type { Aprobacion, Cuenta, Orden, Verificacion } from "@/lib/desembolso/tipos";

// Pantalla 1. El operador verifica el documento del titular; con su cod_cliente se leen de COREDB las
// aprobaciones vigentes (CR-INT-04) y las cuentas que admiten el abono. Preparar crea la orden y le
// registra la identidad verificada hoy, así que queda VALIDADA y lista para confirmar.
export default function Desembolsar() {
  const sesion = useSesion();
  const router = useRouter();
  const params = useSearchParams();
  const idSolicitudFiltro = params.get("idSolicitud") ?? "";
  const [verificacion, setVerificacion] = useState<Verificacion | null>(null);
  const [aprobaciones, setAprobaciones] = useState<Aprobacion[] | null>(null);
  const [cuentas, setCuentas] = useState<Cuenta[]>([]);
  const [elegidas, setElegidas] = useState<Record<string, string>>({});
  const [preparando, setPreparando] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  // Una llave por aprobación mientras dure el intento: repetirlo devuelve la misma orden.
  const llaves = useRef(new Map<string, string>());

  async function alVerificar(v: Verificacion) {
    setVerificacion(v);
    setAprobaciones(null);
    if (v.resultado !== "APROBADO" || !v.codCliente) return;
    const [a, c] = await Promise.all([
      api.get<Aprobacion[]>("aprobaciones", { params: { codCliente: v.codCliente } }),
      api.get<Cuenta[]>(`clientes/${encodeURIComponent(v.codCliente)}/cuentas`),
    ]);
    setAprobaciones(a.data);
    setCuentas(c.data);
  }

  function elegiblesPara(a: Aprobacion): Cuenta[] {
    return cuentas.filter((c) => c.elegible && c.moneda === a.moneda);
  }

  async function preparar(a: Aprobacion) {
    if (!verificacion) return;
    const numCuenta = elegidas[a.idEvaluacion] ?? elegiblesPara(a)[0]?.numCuenta;
    if (!numCuenta) return;
    setError(null);
    setPreparando(a.idEvaluacion);
    const llave = llaves.current.get(a.idEvaluacion) ?? nuevaClave();
    llaves.current.set(a.idEvaluacion, llave);
    try {
      const r = await api.post<Orden>("ordenes", { idEvaluacion: a.idEvaluacion, numCuenta }, { headers: { "X-Idempotency-Key": llave } });
      llaves.current.delete(a.idEvaluacion);
      try {
        await api.post(`ordenes/${r.data.idOrden}/validaciones`, {
          tipo: "IDENTIDAD",
          resultado: "APROBADA",
          referenciaEvidencia: String(verificacion.idValidacion),
          detalle: "Documento original verificado en ventanilla.",
        });
      } catch {
        // La orden queda PREPARADA: en su pantalla se verifica la identidad otra vez.
      }
      router.push(`/desembolso/ordenes/${r.data.idOrden}`);
    } catch (e) {
      setError(e);
      setPreparando(null);
    }
  }

  if (!sesion.puedeOperar) {
    return (
      <>
        <Encabezado titulo="Desembolso de créditos" />
        <Alerta tipo="info" titulo="Tu perfil solo consulta">
          El desembolso lo hace un operador: verifica en ventanilla el documento del titular y abona el
          crédito. Puedes revisar las órdenes y sus constancias en{" "}
          <Link href="/desembolso/ordenes" className="font-semibold underline">
            Órdenes
          </Link>
          .
        </Alerta>
      </>
    );
  }

  const aprobado = verificacion?.resultado === "APROBADO";
  return (
    <>
      <Encabezado titulo="Desembolso de créditos" descripcion="Identidad del titular, aprobación vigente y cuenta de abono" />
      <Tarjeta titulo="1 · Identidad del titular" className="mb-6">
        <p className="mb-4 text-sm text-slate-600">
          Revise el documento original y a la persona. La verificación queda registrada en COREDB y vale para desembolsar hoy.
        </p>
        <VerificarDocumento onVerificado={alVerificar} onError={setError} />
        {verificacion && (
          <div className="mt-4">
            {aprobado ? (
              <Alerta tipo="exito" titulo={`${verificacion.nombre ?? "Titular"} · ${verificacion.codCliente}`}>
                Identidad verificada hoy (verificación n.° {verificacion.idValidacion}).
              </Alerta>
            ) : (
              <Alerta tipo="aviso" titulo="No se pudo verificar la identidad">
                {verificacion.motivo ?? "El documento no corresponde a un cliente activo."}
              </Alerta>
            )}
          </div>
        )}
      </Tarjeta>
      {error ? (
        <div className="mb-6">
          <AlertaError error={error} />
        </div>
      ) : null}
      {aprobado && aprobaciones && (() => { const filas = idSolicitudFiltro ? aprobaciones.filter((x) => x.idSolicitud === idSolicitudFiltro) : aprobaciones; return (
        <Tarjeta titulo={`2 · Aprobaciones vigentes (${filas.length})`}>
          <div className="-m-5 overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-100">
              <thead className="bg-slate-50">
                <tr>
                  <th className={th}>Solicitud</th>
                  <th className={`${th} text-right`}>Importe</th>
                  <th className={th}>Plazo</th>
                  <th className={th}>Vigente hasta</th>
                  <th className={th}>Cuenta de abono</th>
                  <th className={th}></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filas.length === 0 && <FilaVacia columnas={6}>El cliente no tiene aprobaciones pendientes de desembolso.</FilaVacia>}
                {filas.map((a) => {
                  const elegibles = elegiblesPara(a);
                  const otras = cuentas.filter((c) => !elegibles.includes(c));
                  return (
                    <tr key={a.idEvaluacion} className="align-top">
                      <td className={td}>
                        <p className="font-mono text-xs text-slate-900">{a.idSolicitud}</p>
                        <p className="text-xs text-slate-500">Ronda {a.ronda}</p>
                      </td>
                      <td className={`${td} tabular text-right font-semibold text-slate-900`}>{dinero(a.monto, a.moneda)}</td>
                      <td className={td}>{a.plazoMeses} meses</td>
                      <td className={td}>{fecha(a.vigenteHasta, false)}</td>
                      <td className={td}>
                        {a.ordenAbierta ? (
                          <span className="text-slate-500">—</span>
                        ) : elegibles.length === 0 ? (
                          <Insignia tono="aviso">Sin cuenta elegible</Insignia>
                        ) : (
                          <select
                            aria-label="Cuenta de abono"
                            className={`${estiloEntrada} w-64 font-mono`}
                            value={elegidas[a.idEvaluacion] ?? elegibles[0].numCuenta}
                            onChange={(e) => setElegidas({ ...elegidas, [a.idEvaluacion]: e.target.value })}
                          >
                            {elegibles.map((c) => (
                              <option key={c.numCuenta} value={c.numCuenta}>
                                {c.numCuenta} · {c.moneda}
                              </option>
                            ))}
                          </select>
                        )}
                        {!a.ordenAbierta &&
                          otras.map((c) => (
                            <p key={c.numCuenta} className="mt-1 text-xs text-slate-500">
                              <span className="font-mono">{c.numCuenta}</span>: {MOTIVOS_CUENTA[c.motivo ?? ""] ?? c.motivo ?? "otra moneda"}
                            </p>
                          ))}
                      </td>
                      <td className={`${td} text-right`}>
                        {a.ordenAbierta ? (
                          <Link href={`/desembolso/ordenes/${a.ordenAbierta.idOrden}`} className="text-sm font-semibold text-marca-600 hover:underline">
                            Ver {a.ordenAbierta.codigoOrden}
                            <span className="ml-2">
                              <InsigniaEstado estado={a.ordenAbierta.estado} etiqueta={ETIQUETA_ESTADO[a.ordenAbierta.estado]} />
                            </span>
                          </Link>
                        ) : (
                          <Boton onClick={() => preparar(a)} cargando={preparando === a.idEvaluacion} disabled={elegibles.length === 0}>
                            Preparar desembolso
                          </Boton>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Tarjeta>
      ); })()}
    </>
  );
}
