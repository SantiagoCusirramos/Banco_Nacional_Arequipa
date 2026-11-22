"use client";

import { useEffect, useState } from "react";
import {
  buscarSolicitantes, nombreCompleto, nombreSolicitante, obtenerCliente,
  type SolicitanteBuscado,
} from "@/lib/clientes";
import { enmascararDocumento } from "@/lib/continuidad";

type Props = {
  id: string;
  label: string;
  value: string;
  onChange: (codCliente: string) => void;
  error?: string;
  placeholder?: string;
};

const CODIGO_CLIENTE = /^[A-Z]+\d+$/i;

function textoError(err: unknown): string {
  const datos = (err as { response?: { data?: { error?: { message?: string }; message?: string; detail?: string } } })?.response?.data;
  if (datos?.error?.message) return datos.error.message;
  if (typeof datos?.message === "string" && datos.message) return datos.message;
  if (typeof datos?.detail === "string") return datos.detail;
  return err instanceof Error ? err.message : "No se pudo buscar al cliente.";
}

/**
 * Busca por documento o nombre sin pedirle al operador que copie un código. El texto viaja
 * en el cuerpo del POST; si reconoce un código, lo valida contra COREDB igual que antes.
 */
export default function SelectorCliente({ id, label, value, onChange, error, placeholder }: Props) {
  const [texto, setTexto] = useState(value);
  const [resultados, setResultados] = useState<SolicitanteBuscado[]>([]);
  const [mensaje, setMensaje] = useState("");
  const [buscando, setBuscando] = useState(false);

  useEffect(() => { setTexto(value); }, [value]);

  async function buscar() {
    const consulta = texto.trim();
    setResultados([]);
    setMensaje("");
    if (!consulta) {
      setMensaje("Ingresa el código del cliente para buscar.");
      return;
    }
    if (consulta.length < 3) {
      setMensaje("Escribe al menos 3 caracteres para buscar.");
      return;
    }
    setBuscando(true);
    try {
      if (CODIGO_CLIENTE.test(consulta)) {
        const cliente = await obtenerCliente(consulta.toUpperCase());
        if (!cliente.permite_operar) {
          setMensaje(`El cliente está ${cliente.estado_cliente} y no puede operar.`);
          onChange("");
          return;
        }
        setMensaje(`Cliente seleccionado: ${nombreCompleto(cliente)}`);
        onChange(cliente.cod_cliente);
        return;
      }
      const encontrados = (await buscarSolicitantes(consulta)).filter((s) => s.cod_cliente);
      setResultados(encontrados);
      if (!encontrados.length) setMensaje("No se encontró ningún cliente con ese documento o nombre.");
    } catch (err) {
      setMensaje(textoError(err));
    } finally {
      setBuscando(false);
    }
  }

  function elegir(s: SolicitanteBuscado) {
    if (!s.cod_cliente) return;
    setTexto(s.cod_cliente);
    setMensaje(`Cliente seleccionado: ${nombreSolicitante(s)}`);
    setResultados([]);
    onChange(s.cod_cliente);
  }

  return (
    <div className="fx-field">
      <label htmlFor={id}>{label}</label>
      <div className="fx-search">
        <input
          id={id}
          autoComplete="off"
          placeholder={placeholder ?? "Documento, nombre o código del cliente"}
          value={texto}
          onChange={(event) => {
            setTexto(event.target.value);
            setResultados([]);
            setMensaje("");
            onChange("");
          }}
        />
        <button
          className="outline-button"
          type="button"
          aria-label={`Buscar ${id}`}
          onClick={buscar}
          disabled={buscando}
        >
          {buscando ? "Buscando..." : "Buscar"}
        </button>
      </div>
      {resultados.length > 0 && (
        <div className="selector-opciones">
          {resultados.map((s) => (
            <button
              className="selector-opcion"
              type="button"
              key={s.id_solicitante}
              onClick={() => elegir(s)}
            >
              <strong>{nombreSolicitante(s)}</strong>
              <span>{s.tipo_documento} {enmascararDocumento(s.numero_documento)}</span>
              <span>{s.cod_cliente}</span>
            </button>
          ))}
        </div>
      )}
      {mensaje && <span className="fx-hint" role="status">{mensaje}</span>}
      {error && <span className="fx-error">{error}</span>}
    </div>
  );
}
