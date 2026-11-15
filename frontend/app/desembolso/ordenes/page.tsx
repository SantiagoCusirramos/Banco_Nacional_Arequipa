"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AlertaError, Boton, Encabezado, FilaVacia, InsigniaEstado, Tarjeta, estiloEntrada, td, th } from "@/app/desembolso/_componentes/ui";
import { api } from "@/lib/desembolso/api";
import { ETIQUETA_ESTADO, dinero, fecha } from "@/lib/desembolso/formato";
import type { EstadoOrden, OrdenResumen } from "@/lib/desembolso/tipos";

interface Pagina {
  items: OrdenResumen[];
  total: number;
  pagina: number;
  tamano: number;
}

export default function Historial() {
  const router = useRouter();
  const [filtros, setFiltros] = useState({ texto: "", estado: "", desde: "", hasta: "" });
  const [pagina, setPagina] = useState(1);
  const [datos, setDatos] = useState<Pagina | null>(null);
  const [error, setError] = useState<unknown>(null);

  const cargar = useCallback(
    async (numero: number) => {
      setError(null);
      const params = Object.fromEntries(Object.entries(filtros).filter(([, v]) => v));
      try {
        const r = await api.get<Pagina>("ordenes", { params: { ...params, pagina: numero, tamano: 15 } });
        setDatos(r.data);
        setPagina(numero);
      } catch (e) {
        setError(e);
      }
    },
    [filtros],
  );

  // Solo la carga inicial: los filtros se aplican con el boton "Filtrar".
  const [cargaInicial] = useState(() => cargar);
  useEffect(() => {
    cargaInicial(1);
  }, [cargaInicial]);

  const paginas = datos ? Math.max(1, Math.ceil(datos.total / datos.tamano)) : 1;
  return (
    <>
      <Encabezado titulo="Historial de órdenes" descripcion="Consulta de estado, historial y constancias (RF-08)" />
      <Tarjeta className="mb-6">
        <form
          className="grid gap-3 md:grid-cols-6"
          onSubmit={(e) => {
            e.preventDefault();
            cargar(1);
          }}
        >
          <input
            aria-label="Texto"
            placeholder="Código, crédito o cliente"
            className={`${estiloEntrada} md:col-span-2`}
            value={filtros.texto}
            onChange={(e) => setFiltros({ ...filtros, texto: e.target.value })}
          />
          <select aria-label="Estado" className={estiloEntrada} value={filtros.estado} onChange={(e) => setFiltros({ ...filtros, estado: e.target.value })}>
            <option value="">Todos los estados</option>
            {Object.entries(ETIQUETA_ESTADO).map(([valor, texto]) => (
              <option key={valor} value={valor}>
                {texto}
              </option>
            ))}
          </select>
          <input aria-label="Desde" type="date" className={estiloEntrada} value={filtros.desde} onChange={(e) => setFiltros({ ...filtros, desde: e.target.value })} />
          <input aria-label="Hasta" type="date" className={estiloEntrada} value={filtros.hasta} onChange={(e) => setFiltros({ ...filtros, hasta: e.target.value })} />
          <Boton type="submit">Filtrar</Boton>
        </form>
      </Tarjeta>
      {error ? <div className="mb-4"><AlertaError error={error} /></div> : null}
      <Tarjeta titulo={datos ? `${datos.total} órdenes` : "Órdenes"}>
        <div className="-m-5 overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-100">
            <thead className="bg-slate-50">
              <tr>
                <th className={th}>Orden</th>
                <th className={th}>Crédito</th>
                <th className={`${th} text-right`}>Importe</th>
                <th className={th}>Estado</th>
                <th className={th}>Entrega</th>
                <th className={th}>Operación</th>
                <th className={th}>Creada</th>
                <th className={th}>Operador</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {datos?.items.length === 0 && <FilaVacia columnas={8}>No hay órdenes con esos filtros.</FilaVacia>}
              {datos?.items.map((o) => (
                <tr key={o.id} onClick={() => router.push(`/desembolso/ordenes/${o.id}`)} className="cursor-pointer hover:bg-marca-50/50">
                  <td className={`${td} font-mono font-semibold text-slate-900`}>{o.codigo_orden}</td>
                  <td className={td}>
                    {o.credito_id}
                    <span className="block text-xs text-slate-500">{o.cliente_id}</span>
                  </td>
                  <td className={`${td} tabular text-right font-semibold`}>{dinero(o.importe, o.moneda)}</td>
                  <td className={td}>
                    <InsigniaEstado estado={o.estado} etiqueta={ETIQUETA_ESTADO[o.estado as EstadoOrden]} />
                  </td>
                  <td className={td}>
                    {["CONFIRMADA", "REVERTIDA"].includes(o.estado) ? <InsigniaEstado estado={o.entrega_estado} /> : <span className="text-slate-400">—</span>}
                  </td>
                  <td className={`${td} font-mono text-xs`}>{o.operacion_financiera_id ?? "—"}</td>
                  <td className={`${td} whitespace-nowrap text-xs`}>{fecha(o.creado_en)}</td>
                  <td className={`${td} text-xs`}>{o.usuario_preparacion}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {datos && paginas > 1 && (
          <div className="mt-8 flex items-center justify-end gap-3 text-sm">
            <Boton variante="secundario" disabled={pagina <= 1} onClick={() => cargar(pagina - 1)}>
              Anterior
            </Boton>
            <span>
              Página {pagina} de {paginas}
            </span>
            <Boton variante="secundario" disabled={pagina >= paginas} onClick={() => cargar(pagina + 1)}>
              Siguiente
            </Boton>
          </div>
        )}
      </Tarjeta>
    </>
  );
}
