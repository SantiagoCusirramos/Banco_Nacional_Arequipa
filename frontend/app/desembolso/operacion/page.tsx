"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Alerta, AlertaError, Boton, Encabezado, FilaVacia, InsigniaEstado, Tarjeta, td, th } from "@/app/desembolso/_componentes/ui";
import { api } from "@/lib/desembolso/api";
import { ETIQUETA_ESTADO, dinero, fecha } from "@/lib/desembolso/formato";
import { useSesion } from "@/lib/desembolso/sesion";
import type { EstadoOrden } from "@/lib/desembolso/tipos";

interface Resumen {
  ordenes_por_estado: Record<string, number>;
  inciertas: { id: string; codigo_orden: string; credito_id: string; importe: string; moneda: string; estado: string; segundos_en_estado: number; alerta: boolean }[];
  entregas: { evento_id: string; orden_id: string; codigo_orden: string; credito_id: string; tipo: string; estado: string; intentos: number; siguiente_intento: string | null; ultimo_error: string | null; antiguedad_min: number }[];
  reversion_habilitada: boolean;
}

function duracion(segundos: number): string {
  if (segundos < 60) return `${segundos} s`;
  if (segundos < 3600) return `${Math.floor(segundos / 60)} min`;
  return `${Math.floor(segundos / 3600)} h ${Math.floor((segundos % 3600) / 60)} min`;
}

export default function Operacion() {
  const sesion = useSesion();
  const [r, setR] = useState<Resumen | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState<string | null>(null);
  const supervisor = sesion.rol === "SUPERVISOR";

  const cargar = useCallback(async () => {
    try {
      setR((await api.get<Resumen>("operacion/resumen")).data);
    } catch (e) {
      setError(e);
    }
  }, []);

  // Carga inicial: el estado se fija al llegar la respuesta, no durante el efecto.
  useEffect(() => {
    api.get<Resumen>("operacion/resumen").then((x) => setR(x.data)).catch(setError);
  }, []);

  async function ejecutar(nombre: string, ruta: string, describir: (d: Record<string, number>) => string) {
    setError(null);
    setOcupado(nombre);
    try {
      const d = (await api.post<Record<string, number>>(ruta)).data;
      setMensaje(describir(d));
      await cargar();
    } catch (e) {
      setError(e);
    } finally {
      setOcupado(null);
    }
  }

  const estados: EstadoOrden[] = ["PREPARADA", "VALIDADA", "EN_PROCESO", "POR_VERIFICAR", "CONFIRMADA", "RECHAZADA", "REVERTIDA"];
  return (
    <>
      <Encabezado
        titulo="Monitor operativo"
        descripcion="Órdenes con resultado incierto (INC-01) y entregas a Cobranza pendientes (INC-02)"
        accion={
          supervisor && (
            <div className="flex gap-2">
              <Boton
                variante="secundario"
                cargando={ocupado === "recuperacion"}
                onClick={() =>
                  ejecutar("recuperacion", "operacion/recuperacion", (d) => `Recuperación: ${d.revisadas} revisadas, ${d.confirmadas} confirmadas, ${d.rechazadas} rechazadas.`)
                }
              >
                Ejecutar recuperación
              </Boton>
              <Boton
                cargando={ocupado === "entregas"}
                onClick={() => ejecutar("entregas", "operacion/entregas", (d) => `Entregas: ${d.enviados} enviadas, ${d.confirmados} con acuse, ${d.reprogramados} reprogramadas.`)}
              >
                Ejecutar entregas
              </Boton>
            </div>
          )
        }
      />
      {mensaje && <div className="mb-4"><Alerta tipo="exito" titulo={mensaje} /></div>}
      {error ? <div className="mb-4"><AlertaError error={error} /></div> : null}
      {r && (
        <>
          <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-7">
            {estados.map((e) => (
              <div key={e} className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{ETIQUETA_ESTADO[e]}</p>
                <p className="tabular mt-1 text-2xl font-semibold text-slate-900">{r.ordenes_por_estado[e] ?? 0}</p>
              </div>
            ))}
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            <Tarjeta titulo="Órdenes con resultado incierto">
              <div className="-m-5 overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-100">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className={th}>Orden</th>
                      <th className={`${th} text-right`}>Importe</th>
                      <th className={th}>Estado</th>
                      <th className={th}>En estado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {r.inciertas.length === 0 && <FilaVacia columnas={4}>Sin órdenes inciertas.</FilaVacia>}
                    {r.inciertas.map((o) => (
                      <tr key={o.id}>
                        <td className={td}>
                          <Link href={`/desembolso/ordenes/${o.id}`} className="font-mono font-semibold text-marca-600 hover:underline">
                            {o.codigo_orden}
                          </Link>
                          <span className="block text-xs text-slate-500">{o.credito_id}</span>
                        </td>
                        <td className={`${td} tabular text-right`}>{dinero(o.importe, o.moneda)}</td>
                        <td className={td}>
                          <InsigniaEstado estado={o.estado} />
                        </td>
                        <td className={td}>
                          {duracion(o.segundos_en_estado)}
                          {o.alerta && <span className="ml-2 text-xs font-semibold text-rose-600">ALERTA</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Tarjeta>
            <Tarjeta titulo="Entregas a Cobranza pendientes">
              <div className="-m-5 overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-100">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className={th}>Orden</th>
                      <th className={th}>Estado</th>
                      <th className={th}>Intentos</th>
                      <th className={th}>Siguiente</th>
                      <th className={th}></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {r.entregas.length === 0 && <FilaVacia columnas={5}>Todas las entregas tienen acuse.</FilaVacia>}
                    {r.entregas.map((e) => (
                      <tr key={e.evento_id}>
                        <td className={td}>
                          <Link href={`/desembolso/ordenes/${e.orden_id}`} className="font-mono font-semibold text-marca-600 hover:underline">
                            {e.codigo_orden}
                          </Link>
                          <span className="block text-xs text-slate-500">{e.tipo}</span>
                          {e.ultimo_error && <span className="block max-w-56 text-xs text-rose-600">{e.ultimo_error}</span>}
                        </td>
                        <td className={td}>
                          <InsigniaEstado estado={e.estado} />
                        </td>
                        <td className={td}>{e.intentos}</td>
                        <td className={`${td} text-xs`}>{e.siguiente_intento ? `${fecha(e.siguiente_intento)} UTC` : "—"}</td>
                        <td className={td}>
                          {supervisor && e.estado === "FALLIDO" && (
                            <Boton
                              variante="secundario"
                              cargando={ocupado === e.evento_id}
                              onClick={() => ejecutar(e.evento_id, `operacion/entregas/${e.evento_id}/reintento`, () => "Evento reprogramado.")}
                            >
                              Reintentar
                            </Boton>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Tarjeta>
          </div>
        </>
      )}
    </>
  );
}
