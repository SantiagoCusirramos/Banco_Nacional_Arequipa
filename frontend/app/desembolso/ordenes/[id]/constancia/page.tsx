"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AlertaError, Boton, EnlaceBoton, Giro } from "@/app/desembolso/_componentes/ui";
import { api } from "@/lib/desembolso/api";
import { dinero, fecha } from "@/lib/desembolso/formato";

interface Constancia {
  codigo_orden: string;
  estado: string;
  operacion_financiera_id: string;
  fecha_efectiva: string;
  credito_id: string;
  aprobacion_id: string;
  producto: string | null;
  plazo_meses: number | null;
  tasa_tea: string | null;
  cliente_nombre: string | null;
  cliente_documento: string | null;
  cuenta_enmascarada: string | null;
  importe: string;
  moneda: string;
  agencia: string | null;
  usuario_preparacion: string;
  usuario_confirmacion: string | null;
  entrega_estado: string;
  correlation_id: string;
  emitida_en: string;
  emitida_por: string;
}

function Fila({ etiqueta, valor }: { etiqueta: string; valor: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-6 border-b border-dashed border-slate-200 py-2 text-sm">
      <span className="text-slate-500">{etiqueta}</span>
      <span className="text-right font-medium text-slate-900">{valor}</span>
    </div>
  );
}

export default function PaginaConstancia() {
  const { id } = useParams<{ id: string }>();
  const [c, setC] = useState<Constancia | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api.get<Constancia>(`ordenes/${id}/constancia`).then((r) => setC(r.data)).catch(setError);
  }, [id]);

  if (error) return <AlertaError error={error} />;
  if (!c) return <p className="flex items-center gap-2 text-sm text-slate-500"><Giro /> Generando constancia…</p>;
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
              <p className="text-xs text-slate-500">{c.agencia}</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-xs uppercase tracking-wide text-slate-500">Constancia de desembolso</p>
            <p className="font-mono text-lg font-semibold text-slate-900">{c.codigo_orden}</p>
          </div>
        </header>
        <section className="my-6 rounded-lg bg-marca-50 px-6 py-5 text-center">
          <p className="text-xs uppercase tracking-wide text-marca-700">Importe desembolsado</p>
          <p className="tabular mt-1 text-3xl font-semibold text-slate-900">{dinero(c.importe, c.moneda)}</p>
          <p className="mt-1 text-sm text-slate-600">Abonado en la cuenta {c.cuenta_enmascarada}</p>
        </section>
        <Fila etiqueta="Titular" valor={c.cliente_nombre ?? "—"} />
        <Fila etiqueta="Documento" valor={c.cliente_documento ?? "—"} />
        <Fila etiqueta="Crédito" valor={`${c.credito_id} · ${c.producto ?? ""}`} />
        <Fila etiqueta="Plazo y tasa" valor={c.plazo_meses ? `${c.plazo_meses} meses · TEA ${c.tasa_tea}%` : "—"} />
        <Fila etiqueta="Aprobación" valor={c.aprobacion_id} />
        <Fila etiqueta="Operación financiera" valor={<span className="font-mono">{c.operacion_financiera_id}</span>} />
        <Fila etiqueta="Fecha efectiva" valor={fecha(c.fecha_efectiva)} />
        <Fila etiqueta="Estado" valor={c.estado} />
        <Fila etiqueta="Preparada / confirmada por" valor={`${c.usuario_preparacion} / ${c.usuario_confirmacion ?? "—"}`} />
        <footer className="mt-8 text-center text-xs text-slate-500">
          <p>
            Emitida el {fecha(c.emitida_en)} por {c.emitida_por} · correlación <span className="font-mono">{c.correlation_id}</span>
          </p>
          <p className="mt-1">Constancia generada por el módulo de Desembolso con la confirmación financiera de Cuentas.</p>
        </footer>
      </article>
    </div>
  );
}
