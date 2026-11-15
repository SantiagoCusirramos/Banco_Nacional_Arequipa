"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Alerta, AlertaError, Boton, Encabezado, FilaVacia, InsigniaEstado, Tarjeta, td, th } from "@/app/desembolso/_componentes/ui";
import { api } from "@/lib/desembolso/api";
import { fecha } from "@/lib/desembolso/formato";
import { useSesion } from "@/lib/desembolso/sesion";
import type { Reversion } from "@/lib/desembolso/tipos";

export default function Reversiones() {
  const sesion = useSesion();
  const [lista, setLista] = useState<Reversion[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [ocupado, setOcupado] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    try {
      setLista((await api.get<Reversion[]>("reversiones")).data);
    } catch (e) {
      setError(e);
    }
  }, []);

  // Carga inicial: el estado se fija al llegar la respuesta, no durante el efecto.
  useEffect(() => {
    api.get<Reversion[]>("reversiones").then((x) => setLista(x.data)).catch(setError);
  }, []);

  async function decidir(r: Reversion, aprobar: boolean) {
    setError(null);
    setOcupado(r.id);
    try {
      await api.post(`reversiones/${r.id}/decision`, { aprobar });
      await cargar();
    } catch (e) {
      setError(e);
    } finally {
      setOcupado(null);
    }
  }

  return (
    <>
      <Encabezado titulo="Reversiones" descripcion="Extornos de desembolsos confirmados (RF-10, CU-07)" />
      {!sesion.reversion_habilitada && (
        <div className="mb-6">
          <Alerta tipo="info" titulo="Política de reversión pendiente de aprobación (PC-05)">
            La funcionalidad está implementada con autorización de un segundo supervisor, pero permanece deshabilitada hasta que el Comité
            de Créditos apruebe causales, plazo y autoridad del extorno. Mientras tanto, una falla técnica se atiende como incidente.
          </Alerta>
        </div>
      )}
      {error ? <div className="mb-4"><AlertaError error={error} /></div> : null}
      <Tarjeta titulo="Solicitudes">
        <div className="-m-5 overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-100">
            <thead className="bg-slate-50">
              <tr>
                <th className={th}>Orden</th>
                <th className={th}>Motivo</th>
                <th className={th}>Solicitante</th>
                <th className={th}>Autorizador</th>
                <th className={th}>Estado</th>
                <th className={th}>Fecha</th>
                <th className={th}></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {lista?.length === 0 && <FilaVacia columnas={7}>No hay solicitudes de reversión.</FilaVacia>}
              {lista?.map((r) => (
                <tr key={r.id}>
                  <td className={td}>
                    <Link href={`/desembolso/ordenes/${r.orden_id}`} className="font-mono font-semibold text-marca-600 hover:underline">
                      {r.codigo_orden}
                    </Link>
                  </td>
                  <td className={`${td} max-w-xs`}>{r.motivo}</td>
                  <td className={td}>{r.solicitante_id}</td>
                  <td className={td}>{r.autorizador_id ?? "—"}</td>
                  <td className={td}>
                    <InsigniaEstado estado={r.estado} />
                  </td>
                  <td className={`${td} text-xs`}>{fecha(r.creado_en)}</td>
                  <td className={`${td} whitespace-nowrap`}>
                    {sesion.rol === "SUPERVISOR" && r.estado === "SOLICITADA" && r.solicitante_id !== sesion.usuario && (
                      <div className="flex gap-2">
                        <Boton variante="peligro" cargando={ocupado === r.id} onClick={() => decidir(r, true)}>
                          Autorizar
                        </Boton>
                        <Boton variante="secundario" disabled={ocupado === r.id} onClick={() => decidir(r, false)}>
                          Rechazar
                        </Boton>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Tarjeta>
    </>
  );
}
