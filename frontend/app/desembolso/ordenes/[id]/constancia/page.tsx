"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Alerta, AlertaError, Boton, EnlaceBoton, Giro } from "@/app/desembolso/_componentes/ui";
import { api } from "@/lib/desembolso/api";
import { dinero, fecha, porcentaje } from "@/lib/desembolso/formato";
import type { OrdenDetalle } from "@/lib/desembolso/tipos";

function Fila({ etiqueta, valor }: { etiqueta: string; valor: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-6 border-b border-dashed border-slate-200 py-2 text-sm">
      <span className="text-slate-500">{etiqueta}</span>
      <span className="text-right font-medium text-slate-900">{valor}</span>
    </div>
  );
}

// La constancia se arma con el detalle de la orden confirmada y el calendario oficial del crédito.
export default function PaginaConstancia() {
  const { id } = useParams<{ id: string }>();
  const [o, setO] = useState<OrdenDetalle | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api.get<OrdenDetalle>(`ordenes/${id}`).then((r) => setO(r.data)).catch(setError);
  }, [id]);

  if (error) return <AlertaError error={error} />;
  if (!o) return <p className="flex items-center gap-2 text-sm text-slate-500"><Giro /> Generando constancia…</p>;
  if (o.estado !== "CONFIRMADA") {
    return <Alerta tipo="aviso" titulo="La orden no está confirmada">La constancia se emite después de confirmar el desembolso.</Alerta>;
  }
  const cuotas = o.calendario?.cuotas ?? [];
  return (
    <div className="mx-auto max-w-2xl">
      <div className="no-imprimir mb-4 flex justify-between">
        <EnlaceBoton href={`/desembolso/ordenes/${id}`}>← Volver a la orden</EnlaceBoton>
        <Boton onClick={() => window.print()}>Imprimir constancia</Boton>
      </div>
      <article className="rounded-xl bg-white p-10 shadow-sm ring-1 ring-slate-200 print:shadow-none print:ring-0">
        <header className="flex items-start justify-between border-b-2 border-marca-700 pb-5">
          <div className="flex items-center gap-3">
            <span className="grid h-12 w-12 place-items-center rounded-lg bg-marca-700 text-base font-black text-white">BNA</span>
            <div>
              <p className="text-lg font-semibold text-slate-900">Banco Nacional de Arequipa</p>
              <p className="text-xs text-slate-500">{o.idAgencia ?? "Ventanilla"}</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-xs uppercase tracking-wide text-slate-500">Constancia de desembolso</p>
            <p className="font-mono text-lg font-semibold text-slate-900">{o.codigoOrden}</p>
          </div>
        </header>
        <section className="my-6 rounded-lg bg-marca-50 px-6 py-5 text-center">
          <p className="text-xs uppercase tracking-wide text-marca-700">Importe desembolsado</p>
          <p className="tabular mt-1 text-3xl font-semibold text-slate-900">{dinero(o.importe, o.moneda)}</p>
          <p className="mt-1 text-sm text-slate-600">Abonado en la cuenta {o.numCuenta}</p>
        </section>
        <Fila etiqueta="Cliente" valor={o.codCliente} />
        <Fila etiqueta="Crédito" valor={o.codCredito} />
        <Fila etiqueta="Plazo y tasa" valor={`${o.plazoMeses} meses${o.calendario ? ` · ${porcentaje(o.calendario.tasa)}` : ""}`} />
        <Fila etiqueta="Operación de abono" valor={<span className="font-mono text-xs">{o.uuidTransaccionAbono}</span>} />
        <Fila etiqueta="Fecha" valor={fecha(o.fechaActualizacion)} />
        <Fila etiqueta="Preparada / confirmada por" valor={`${o.usuarioPreparacion} / ${o.usuarioConfirmacion ?? "—"}`} />
        {cuotas.length > 0 && (
          <div className="overflow-x-auto">
          <table className="mt-6 min-w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="py-1 pr-2">Cuota</th>
                <th className="py-1 pr-2">Vence</th>
                <th className="py-1 text-right">Importe</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {cuotas.map((c) => (
                <tr key={c.numeroCuota}>
                  <td className="py-1 pr-2">{c.numeroCuota}</td>
                  <td className="py-1 pr-2">{fecha(c.fechaVencimiento, false)}</td>
                  <td className="tabular py-1 text-right">{dinero(c.cuotaTotal, o.moneda)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
        <footer className="mt-8 text-center text-xs text-slate-500">
          <p>Constancia del módulo de Desembolso con la confirmación de COREDB: abono, crédito y calendario oficial en una sola operación.</p>
        </footer>
      </article>
    </div>
  );
}
