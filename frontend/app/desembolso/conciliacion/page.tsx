"use client";

import { useCallback, useEffect, useState } from "react";
import { Alerta, AlertaError, Boton, Encabezado, FilaVacia, Tarjeta, estiloEntrada, td, th } from "@/app/desembolso/_componentes/ui";
import { api } from "@/lib/desembolso/api";
import { dinero, fecha } from "@/lib/desembolso/formato";
import { useSesion } from "@/lib/desembolso/sesion";
import type { Conciliacion } from "@/lib/desembolso/tipos";

// Órdenes confirmadas frente a lo abonado en las cuentas, por día de negocio (Lima) y moneda. Sin
// fecha, los últimos días con desembolsos. Es del supervisor y del auditor (GENERAR_REPORTES).
export default function PaginaConciliacion() {
  const sesion = useSesion();
  const [dia, setDia] = useState("");
  const [filas, setFilas] = useState<Conciliacion[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  const cargar = useCallback(async (valor: string) => {
    setError(null);
    try {
      const r = await api.get<Conciliacion[]>("conciliacion", { params: valor ? { fecha: valor } : {} });
      setFilas(r.data);
    } catch (e) {
      setError(e);
    }
  }, []);

  // Carga inicial: el estado se fija al llegar la respuesta, no durante el efecto.
  useEffect(() => {
    if (!sesion.puedeConciliar) return;
    api.get<Conciliacion[]>("conciliacion").then((r) => setFilas(r.data)).catch(setError);
  }, [sesion.puedeConciliar]);

  if (!sesion.puedeConciliar) {
    return <Alerta tipo="info" titulo="La conciliación es del supervisor y del auditor." />;
  }
  return (
    <>
      <Encabezado titulo="Conciliación de desembolsos" descripcion="Órdenes confirmadas frente a lo abonado, por día y moneda" />
      <Tarjeta className="mb-6">
        <form
          className="flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            cargar(dia);
          }}
        >
          <input aria-label="Fecha" type="date" className={`${estiloEntrada} w-48`} value={dia} onChange={(e) => setDia(e.target.value)} />
          <Boton type="submit">Conciliar</Boton>
        </form>
      </Tarjeta>
      {error ? <div className="mb-4"><AlertaError error={error} /></div> : null}
      <Tarjeta titulo="Resultado">
        <div className="-m-5 overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-100">
            <thead className="bg-slate-50">
              <tr>
                <th className={th}>Fecha</th>
                <th className={th}>Moneda</th>
                <th className={`${th} text-right`}>Órdenes</th>
                <th className={`${th} text-right`}>Importe de las órdenes</th>
                <th className={`${th} text-right`}>Abonado</th>
                <th className={`${th} text-right`}>Sin abono</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filas?.length === 0 && <FilaVacia columnas={6}>No hay desembolsos confirmados en ese día.</FilaVacia>}
              {filas?.map((f) => {
                const cuadra = f.ordenesSinAbono === 0 && f.importeOrdenes === f.importeAbonado;
                return (
                  <tr key={`${f.fecha}-${f.moneda}`} className={cuadra ? "" : "bg-rose-50"}>
                    <td className={td}>{fecha(f.fecha, false)}</td>
                    <td className={td}>{f.moneda}</td>
                    <td className={`${td} tabular text-right`}>{f.ordenesConfirmadas}</td>
                    <td className={`${td} tabular text-right`}>{dinero(f.importeOrdenes, f.moneda)}</td>
                    <td className={`${td} tabular text-right`}>{dinero(f.importeAbonado, f.moneda)}</td>
                    <td className={`${td} tabular text-right font-semibold ${cuadra ? "" : "text-rose-700"}`}>{f.ordenesSinAbono}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Tarjeta>
    </>
  );
}
