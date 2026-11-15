"use client";

import { useState } from "react";
import { Alerta, AlertaError, Boton, Encabezado, FilaVacia, InsigniaEstado, Tarjeta, estiloEntrada, td, th } from "@/app/desembolso/_componentes/ui";
import { api } from "@/lib/desembolso/api";
import { dinero, hoyLima } from "@/lib/desembolso/formato";

interface Reporte {
  fecha: string;
  moneda: string | null;
  estado: "CONCILIADO" | "CON_DIFERENCIAS";
  totales: { ordenes: number; importe_ordenes: string; abonos_cuentas: number; importe_cuentas: string; acuses_cobranza: number };
  ordenes: { codigo_orden: string; credito_id: string; importe: string; moneda: string; estado: string; entrega_estado: string; operacion_financiera_id: string }[];
  diferencias: { tipo: string; codigo_orden: string | null; detalle: string }[];
}

export default function Conciliacion() {
  const [fecha, setFecha] = useState(hoyLima());
  const [moneda, setMoneda] = useState("PEN");
  const [reporte, setReporte] = useState<Reporte | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [cargando, setCargando] = useState(false);

  async function conciliar() {
    setError(null);
    setCargando(true);
    try {
      setReporte((await api.post<Reporte>("conciliaciones", { fecha, moneda: moneda || null })).data);
    } catch (e) {
      setError(e);
      setReporte(null);
    } finally {
      setCargando(false);
    }
  }

  const m = reporte?.moneda ?? "PEN";
  return (
    <>
      <Encabezado titulo="Conciliación diaria" descripcion="Órdenes de Desembolso frente a abonos de Cuentas y acuses de Cobranza (RF-09)" />
      <Tarjeta className="mb-6">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label htmlFor="fecha" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">
              Fecha efectiva
            </label>
            <input id="fecha" type="date" className={estiloEntrada} value={fecha} onChange={(e) => setFecha(e.target.value)} />
          </div>
          <div>
            <label htmlFor="moneda" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">
              Moneda
            </label>
            <select id="moneda" className={`${estiloEntrada} w-40`} value={moneda} onChange={(e) => setMoneda(e.target.value)}>
              <option value="PEN">Soles (PEN)</option>
              <option value="USD">Dólares (USD)</option>
            </select>
          </div>
          <Boton onClick={conciliar} cargando={cargando}>
            Conciliar
          </Boton>
        </div>
      </Tarjeta>
      {error ? <div className="mb-4"><AlertaError error={error} /></div> : null}
      {reporte && (
        <>
          <div className="mb-6">
            {reporte.estado === "CONCILIADO" ? (
              <Alerta tipo="exito" titulo={`Conciliado: los tres orígenes coinciden para el ${reporte.fecha}.`} />
            ) : (
              <Alerta tipo="aviso" titulo={`Se encontraron ${reporte.diferencias.length} diferencias para revisión.`} />
            )}
          </div>
          <div className="mb-6 grid gap-3 md:grid-cols-5">
            {[
              ["Órdenes confirmadas", String(reporte.totales.ordenes)],
              ["Importe en Desembolso", dinero(reporte.totales.importe_ordenes, m)],
              ["Abonos en Cuentas", String(reporte.totales.abonos_cuentas)],
              ["Importe en Cuentas", dinero(reporte.totales.importe_cuentas, m)],
              ["Acuses de Cobranza", String(reporte.totales.acuses_cobranza)],
            ].map(([etiqueta, valor]) => (
              <div key={etiqueta} className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{etiqueta}</p>
                <p className="tabular mt-1 text-xl font-semibold text-slate-900">{valor}</p>
              </div>
            ))}
          </div>
          <div className="grid gap-6 lg:grid-cols-3">
            <Tarjeta titulo="Órdenes del día" className="lg:col-span-2">
              <div className="-m-5 overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-100">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className={th}>Orden</th>
                      <th className={th}>Crédito</th>
                      <th className={`${th} text-right`}>Importe</th>
                      <th className={th}>Operación</th>
                      <th className={th}>Estado</th>
                      <th className={th}>Entrega</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {reporte.ordenes.length === 0 && <FilaVacia columnas={6}>No hay desembolsos confirmados en la fecha.</FilaVacia>}
                    {reporte.ordenes.map((o) => (
                      <tr key={o.codigo_orden}>
                        <td className={`${td} font-mono font-semibold`}>{o.codigo_orden}</td>
                        <td className={td}>{o.credito_id}</td>
                        <td className={`${td} tabular text-right`}>{dinero(o.importe, o.moneda)}</td>
                        <td className={`${td} font-mono text-xs`}>{o.operacion_financiera_id}</td>
                        <td className={td}>
                          <InsigniaEstado estado={o.estado} />
                        </td>
                        <td className={td}>
                          <InsigniaEstado estado={o.entrega_estado} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Tarjeta>
            <Tarjeta titulo="Diferencias">
              {reporte.diferencias.length === 0 ? (
                <p className="text-sm text-slate-500">Sin diferencias.</p>
              ) : (
                <ul className="space-y-3">
                  {reporte.diferencias.map((d, i) => (
                    <li key={i} className="text-sm">
                      <InsigniaEstado estado="FALLIDO" etiqueta={d.tipo.replaceAll("_", " ")} />
                      <p className="mt-1 text-slate-700">
                        {d.codigo_orden && <span className="font-mono font-semibold">{d.codigo_orden} · </span>}
                        {d.detalle}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </Tarjeta>
          </div>
        </>
      )}
    </>
  );
}
