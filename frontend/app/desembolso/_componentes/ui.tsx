"use client";

import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { mensajeError } from "@/lib/api";
import type { Tono } from "@/lib/desembolso/formato";
import { TONO_ESTADO } from "@/lib/desembolso/formato";

type Variante = "primario" | "secundario" | "peligro" | "fantasma";

const VARIANTES: Record<Variante, string> = {
  primario: "bg-marca-700 text-white hover:bg-marca-800 disabled:bg-slate-300",
  secundario: "bg-white text-marca-700 ring-1 ring-inset ring-marca-200 hover:bg-marca-50 disabled:text-slate-400",
  peligro: "bg-rose-600 text-white hover:bg-rose-700 disabled:bg-slate-300",
  fantasma: "text-marca-700 hover:bg-marca-50 disabled:text-slate-400",
};

export function Boton({
  variante = "primario",
  cargando = false,
  className = "",
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variante?: Variante; cargando?: boolean }) {
  return (
    <button
      {...props}
      disabled={props.disabled || cargando}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed ${VARIANTES[variante]} ${className}`}
    >
      {cargando && <Giro />}
      {children}
    </button>
  );
}

export function EnlaceBoton({ href, children, variante = "secundario" }: { href: string; children: ReactNode; variante?: Variante }) {
  return (
    <Link
      href={href}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition ${VARIANTES[variante]}`}
    >
      {children}
    </Link>
  );
}

export function Giro() {
  return <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden />;
}

export function Tarjeta({
  titulo,
  accion,
  children,
  className = "",
}: {
  titulo?: ReactNode;
  accion?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-xl bg-white shadow-sm ring-1 ring-slate-200 ${className}`}>
      {(titulo || accion) && (
        <header className="flex items-center justify-between gap-4 border-b border-slate-100 px-5 py-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">{titulo}</h2>
          {accion}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

const TONOS: Record<Tono, string> = {
  neutro: "bg-slate-100 text-slate-700 ring-slate-200",
  info: "bg-marca-50 text-marca-700 ring-marca-200",
  exito: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  aviso: "bg-amber-50 text-amber-800 ring-amber-200",
  error: "bg-rose-50 text-rose-700 ring-rose-200",
  especial: "bg-violet-50 text-violet-700 ring-violet-200",
};

export function Insignia({ tono, children }: { tono?: Tono; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${TONOS[tono ?? "neutro"]}`}>
      {children}
    </span>
  );
}

export function InsigniaEstado({ estado, etiqueta }: { estado: string; etiqueta?: string }) {
  return <Insignia tono={TONO_ESTADO[estado] ?? "neutro"}>{etiqueta ?? estado.replaceAll("_", " ")}</Insignia>;
}

const ALERTAS = {
  info: "bg-marca-50 text-marca-800 ring-marca-200",
  exito: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  aviso: "bg-amber-50 text-amber-900 ring-amber-200",
  error: "bg-rose-50 text-rose-800 ring-rose-200",
} as const;

export function Alerta({ tipo = "info", titulo, children }: { tipo?: keyof typeof ALERTAS; titulo?: ReactNode; children?: ReactNode }) {
  return (
    <div role={tipo === "error" ? "alert" : "status"} className={`rounded-lg px-4 py-3 text-sm ring-1 ring-inset ${ALERTAS[tipo]}`}>
      {titulo && <p className="font-semibold">{titulo}</p>}
      {children && <div className={titulo ? "mt-1" : ""}>{children}</div>}
    </div>
  );
}

export function AlertaError({ error }: { error: unknown }) {
  if (!error) return null;
  return <Alerta tipo="error" titulo={mensajeError(error)} />;
}

export function Dato({ etiqueta, children, grande = false }: { etiqueta: string; children: ReactNode; grande?: boolean }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{etiqueta}</dt>
      <dd className={`mt-0.5 ${grande ? "tabular text-2xl font-semibold text-slate-900" : "text-sm text-slate-800"}`}>{children}</dd>
    </div>
  );
}

export const estiloEntrada =
  "block w-full rounded-lg border-0 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm ring-1 ring-inset ring-slate-300 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-marca-500";

export function Etiqueta({ htmlFor, children }: { htmlFor: string; children: ReactNode }) {
  return (
    <label htmlFor={htmlFor} className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">
      {children}
    </label>
  );
}

export function FilaVacia({ columnas, children }: { columnas: number; children: ReactNode }) {
  return (
    <tr>
      <td colSpan={columnas} className="px-4 py-8 text-center text-sm text-slate-500">
        {children}
      </td>
    </tr>
  );
}

export function Encabezado({ titulo, descripcion, accion }: { titulo: string; descripcion?: string; accion?: ReactNode }) {
  return (
    <div className="mb-6 flex items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">{titulo}</h1>
        {descripcion && <p className="mt-1 text-sm text-slate-500">{descripcion}</p>}
      </div>
      {accion}
    </div>
  );
}

export const th = "px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500";
export const td = "px-4 py-3 text-sm text-slate-700";
