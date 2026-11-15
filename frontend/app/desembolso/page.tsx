"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { AlertaError, Boton, Encabezado, FilaVacia, InsigniaEstado, Tarjeta, estiloEntrada, td, th } from "@/app/desembolso/_componentes/ui";
import { api, nuevaClave } from "@/lib/desembolso/api";
import { dinero, fecha } from "@/lib/desembolso/formato";
import { puede, useSesion } from "@/lib/desembolso/sesion";
import type { CreditoHabilitado, OrdenDetalle } from "@/lib/desembolso/tipos";

const esquema = z.object({
  criterio: z.enum(["documento", "credito_id"]),
  valor: z.string().trim().min(3, "Ingrese al menos 3 caracteres").max(36),
});
type Busqueda = z.infer<typeof esquema>;

export default function Creditos() {
  const sesion = useSesion();
  const router = useRouter();
  const [creditos, setCreditos] = useState<CreditoHabilitado[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [preparando, setPreparando] = useState<string | null>(null);
  const claves = useRef(new Map<string, string>()); // una clave por aprobacion mientras dure el intento
  const { register, handleSubmit, formState } = useForm<Busqueda>({
    resolver: zodResolver(esquema),
    defaultValues: { criterio: "documento", valor: "" },
  });

  async function buscar(datos: Busqueda) {
    setError(null);
    try {
      const r = await api.get<CreditoHabilitado[]>("creditos-habilitados", { params: { [datos.criterio]: datos.valor } });
      setCreditos(r.data);
    } catch (e) {
      setError(e);
      setCreditos(null);
    }
  }

  async function preparar(c: CreditoHabilitado) {
    setError(null);
    setPreparando(c.aprobacion_id);
    const clave = claves.current.get(c.aprobacion_id) ?? nuevaClave();
    claves.current.set(c.aprobacion_id, clave);
    try {
      const r = await api.post<OrdenDetalle>("ordenes", { aprobacion_id: c.aprobacion_id }, { headers: { "X-Idempotency-Key": clave } });
      claves.current.delete(c.aprobacion_id);
      router.push(`/desembolso/ordenes/${r.data.id}`);
    } catch (e) {
      setError(e);
      setPreparando(null);
    }
  }

  return (
    <>
      <Encabezado titulo="Consulta de créditos habilitados" descripcion="Pantalla 1 · Aprobaciones emitidas por Evaluación (CR-INT-04)" />
      <Tarjeta className="mb-6">
        <form onSubmit={handleSubmit(buscar)} className="flex flex-wrap items-end gap-3" noValidate>
          <div>
            <label htmlFor="criterio" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">
              Buscar por
            </label>
            <select id="criterio" className={`${estiloEntrada} w-48`} {...register("criterio")}>
              <option value="documento">Documento del cliente</option>
              <option value="credito_id">Código de crédito</option>
            </select>
          </div>
          <div className="min-w-64 flex-1">
            <label htmlFor="valor" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">
              Valor
            </label>
            <input id="valor" placeholder="DNI o CRE-2026-0001" className={estiloEntrada} {...register("valor")} />
          </div>
          <Boton type="submit" cargando={formState.isSubmitting}>
            Buscar
          </Boton>
          {formState.errors.valor && <p className="w-full text-xs text-rose-600">{formState.errors.valor.message}</p>}
        </form>
      </Tarjeta>
      {error ? <div className="mb-6"><AlertaError error={error} /></div> : null}
      {creditos && (
        <Tarjeta titulo={`Resultados (${creditos.length})`}>
          <div className="-m-5 overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-100">
              <thead className="bg-slate-50">
                <tr>
                  <th className={th}>Crédito</th>
                  <th className={th}>Cliente</th>
                  <th className={th}>Producto</th>
                  <th className={`${th} text-right`}>Importe</th>
                  <th className={th}>Vigencia</th>
                  <th className={th}>Aprobación</th>
                  <th className={th}></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {creditos.length === 0 && <FilaVacia columnas={7}>No existen aprobaciones para el criterio de búsqueda.</FilaVacia>}
                {creditos.map((c) => (
                  <tr key={c.aprobacion_id} className="align-top">
                    <td className={td}>
                      <p className="font-semibold text-slate-900">{c.credito_id}</p>
                      <p className="text-xs text-slate-500">
                        {c.aprobacion_id} · v{c.version}
                      </p>
                    </td>
                    <td className={td}>
                      <p className="font-medium text-slate-900">{c.cliente_nombre}</p>
                      <p className="text-xs text-slate-500">DNI {c.cliente_documento}</p>
                    </td>
                    <td className={td}>
                      {c.producto}
                      <p className="text-xs text-slate-500">
                        {c.plazo_meses} meses · TEA {c.tasa_tea}%
                      </p>
                    </td>
                    <td className={`${td} tabular text-right font-semibold text-slate-900`}>{dinero(c.importe, c.moneda)}</td>
                    <td className={td}>{fecha(c.vigente_hasta, false)}</td>
                    <td className={td}>
                      <InsigniaEstado estado={c.estado} />
                      {c.motivo && <p className="mt-1 max-w-48 text-xs text-slate-500">{c.motivo}</p>}
                    </td>
                    <td className={`${td} text-right`}>
                      {c.orden_existente ? (
                        <Link href={`/desembolso/ordenes/${c.orden_existente.id}`} className="text-sm font-semibold text-marca-600 hover:underline">
                          Ver {c.orden_existente.codigo_orden}
                        </Link>
                      ) : c.habilitada && puede(sesion, "DESEMBOLSO_EJECUTAR") ? (
                        <Boton onClick={() => preparar(c)} cargando={preparando === c.aprobacion_id}>
                          Preparar desembolso
                        </Boton>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Tarjeta>
      )}
    </>
  );
}
