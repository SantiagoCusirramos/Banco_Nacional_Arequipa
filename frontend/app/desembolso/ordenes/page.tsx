"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AlertaError, Boton, Encabezado, FilaVacia, InsigniaEstado, Tarjeta, estiloEntrada, td, th } from "@/app/desembolso/_componentes/ui";
import { api } from "@/lib/desembolso/api";
import { ESTADOS_EN_USO, ETIQUETA_ESTADO, dinero, fecha } from "@/lib/desembolso/formato";
import type { Orden } from "@/lib/desembolso/tipos";

const TAMANO = 20;

export default function Ordenes() {
  const router = useRouter();
  const [filtros, setFiltros] = useState({ estado: "", codCliente: "" });
  const [offset, setOffset] = useState(0);
  const [ordenes, setOrdenes] = useState<Orden[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  const cargar = useCallback(
    async (desde: number) => {
      setError(null);
      const params = Object.fromEntries(Object.entries(filtros).filter(([, v]) => v.trim()));
      try {
        const r = await api.get<Orden[]>("ordenes", { params: { ...params, limite: TAMANO, offset: desde } });
        setOrdenes(r.data);
        setOffset(desde);
      } catch (e) {
        setError(e);
      }
    },
    [filtros],
  );

  // Solo la carga inicial: los filtros se aplican con el botón "Filtrar".
  const [cargaInicial] = useState(() => cargar);
  useEffect(() => {
    cargaInicial(0);
  }, [cargaInicial]);

  return (
    <>
      <Encabezado titulo="Órdenes de desembolso" descripcion="Monitor de órdenes, de la más reciente a la más antigua" />
      <Tarjeta className="mb-6">
        <form
          className="grid gap-3 md:grid-cols-4"
          onSubmit={(e) => {
            e.preventDefault();
            cargar(0);
          }}
        >
          <input
            aria-label="Código de cliente"
            placeholder="Código de cliente"
            maxLength={12}
            className={estiloEntrada}
            value={filtros.codCliente}
            onChange={(e) => setFiltros({ ...filtros, codCliente: e.target.value })}
          />
          <select aria-label="Estado" className={estiloEntrada} value={filtros.estado} onChange={(e) => setFiltros({ ...filtros, estado: e.target.value })}>
            <option value="">Todos los estados</option>
            {ESTADOS_EN_USO.map((valor) => (
              <option key={valor} value={valor}>
                {ETIQUETA_ESTADO[valor]}
              </option>
            ))}
          </select>
          <Boton type="submit">Filtrar</Boton>
        </form>
      </Tarjeta>
      {error ? <div className="mb-4"><AlertaError error={error} /></div> : null}
      <Tarjeta titulo="Órdenes">
        <div className="-m-5 overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-100">
            <thead className="bg-slate-50">
              <tr>
                <th className={th}>Orden</th>
                <th className={th}>Cliente</th>
                <th className={`${th} text-right`}>Importe</th>
                <th className={th}>Estado</th>
                <th className={th}>Crédito</th>
                <th className={th}>Creada</th>
                <th className={th}>Operador</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {ordenes?.length === 0 && <FilaVacia columnas={7}>No hay órdenes con esos filtros.</FilaVacia>}
              {ordenes?.map((o) => (
                <tr key={o.idOrden} onClick={() => router.push(`/desembolso/ordenes/${o.idOrden}`)} className="cursor-pointer hover:bg-marca-50/50">
                  <td className={`${td} font-mono font-semibold text-slate-900`}>{o.codigoOrden}</td>
                  <td className={td}>{o.codCliente}</td>
                  <td className={`${td} tabular text-right font-semibold`}>{dinero(o.importe, o.moneda)}</td>
                  <td className={td}>
                    <InsigniaEstado estado={o.estado} etiqueta={ETIQUETA_ESTADO[o.estado]} />
                  </td>
                  <td className={`${td} font-mono text-xs`}>{o.codCredito ?? "—"}</td>
                  <td className={`${td} whitespace-nowrap text-xs`}>{fecha(o.fechaCreacion)}</td>
                  <td className={`${td} text-xs`}>{o.usuarioPreparacion}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {ordenes && (offset > 0 || ordenes.length === TAMANO) && (
          <div className="mt-8 flex items-center justify-end gap-3 text-sm">
            <Boton variante="secundario" disabled={offset === 0} onClick={() => cargar(Math.max(0, offset - TAMANO))}>
              Anterior
            </Boton>
            <Boton variante="secundario" disabled={ordenes.length < TAMANO} onClick={() => cargar(offset + TAMANO)}>
              Siguiente
            </Boton>
          </div>
        )}
      </Tarjeta>
    </>
  );
}
