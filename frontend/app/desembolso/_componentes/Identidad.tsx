"use client";

import { useState } from "react";
import { api } from "@/lib/desembolso/api";
import type { Verificacion } from "@/lib/desembolso/tipos";
import { Boton, Etiqueta, estiloEntrada } from "./ui";

const TIPOS = [
  { codigo: "DNI", texto: "DNI" },
  { codigo: "CE", texto: "Carné de extranjería" },
  { codigo: "PTP", texto: "PTP" },
  { codigo: "PASAPORTE", texto: "Pasaporte" },
];

/**
 * Verificación del documento en ventanilla. COREDB la registra y la aprueba solo para un cliente
 * ACTIVO; su `idValidacion` es la evidencia IDENTIDAD de la orden y vale el mismo día (T7).
 */
export function VerificarDocumento({
  boton = "Verificar identidad",
  onVerificado,
  onError,
}: {
  boton?: string;
  onVerificado: (v: Verificacion) => void | Promise<void>;
  onError: (e: unknown) => void;
}) {
  const [tipo, setTipo] = useState("DNI");
  const [numero, setNumero] = useState("");
  const [verificado, setVerificado] = useState(false);
  const [enviando, setEnviando] = useState(false);

  async function verificar() {
    onError(null);
    setEnviando(true);
    try {
      const r = await api.post<Verificacion>("identidad", {
        tipoDocumento: tipo,
        numeroDocumento: numero.trim(),
        identidadVerificada: true,
      });
      setNumero("");
      setVerificado(false);
      await onVerificado(r.data);
    } catch (e) {
      onError(e);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div>
        <Etiqueta htmlFor="tipo-documento">Tipo de documento</Etiqueta>
        <select id="tipo-documento" value={tipo} onChange={(e) => setTipo(e.target.value)} className={`${estiloEntrada} w-48`}>
          {TIPOS.map((t) => (
            <option key={t.codigo} value={t.codigo}>
              {t.texto}
            </option>
          ))}
        </select>
      </div>
      <div>
        <Etiqueta htmlFor="numero-documento">Número del documento presentado</Etiqueta>
        <input
          id="numero-documento"
          value={numero}
          onChange={(e) => setNumero(e.target.value)}
          maxLength={12}
          autoComplete="off"
          className={`${estiloEntrada} w-56`}
        />
      </div>
      <label className="flex items-center gap-2 pb-2 text-sm text-slate-700">
        <input type="checkbox" checked={verificado} onChange={(e) => setVerificado(e.target.checked)} />
        Verifiqué el documento original y a la persona
      </label>
      <Boton onClick={verificar} cargando={enviando} disabled={!verificado || numero.trim().length < 6}>
        {boton}
      </Boton>
    </div>
  );
}
