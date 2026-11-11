"use client";

import { useState } from "react";
import { ESTADOS_CUENTA, mensajeDeError, verCuenta, type Cuenta, type EstadoCuenta } from "@/lib/cuentas";
import { CuentaResumen } from "./CuentaResumen";

const DESCRIPCION_ESTADO: Record<EstadoCuenta, string> = {
  ACTIVA: "Cuenta operativa.",
  BLOQUEADA: "No origina débitos (RGN-09).",
  BLOQUEADA_PREVENTIVA: "Bloqueo preventivo: no origina débitos.",
  CANCELADA: "Cuenta cerrada.",
};

type Props = {
  cuentaInicial?: Cuenta | null;
  onNotice: (mensaje: string) => void;
};

export function ModificarCuenta({ cuentaInicial = null, onNotice }: Props) {
  const [numCuenta, setNumCuenta] = useState(cuentaInicial?.num_cuenta ?? "");
  const [cuenta, setCuenta] = useState<Cuenta | null>(cuentaInicial);
  const [buscando, setBuscando] = useState(false);
  const [errorBusqueda, setErrorBusqueda] = useState("");

  async function buscar(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const numero = numCuenta.trim();
    if (!numero) {
      setErrorBusqueda("Ingresa el número de cuenta.");
      return;
    }
    setBuscando(true);
    setErrorBusqueda("");
    onNotice("");
    try {
      setCuenta(await verCuenta(numero));
    } catch (err) {
      setCuenta(null);
      setErrorBusqueda(mensajeDeError(err));
    } finally {
      setBuscando(false);
    }
  }

  return (
    <div className="fx-stack">
      <div className="form-card">
        <div className="form-intro">
          <span className="form-icon">✎</span>
          <div>
            <h2>Modificar cuenta</h2>
            <p>Busca la cuenta por su número para ver su estado.</p>
          </div>
        </div>
        <form className="fx-search" onSubmit={buscar} noValidate>
          <div className="fx-field fx-grow">
            <label htmlFor="num_cuenta">Número de cuenta</label>
            <input id="num_cuenta" autoComplete="off" placeholder="Ej. 14 dígitos" maxLength={20} value={numCuenta} onChange={(e) => setNumCuenta(e.target.value)} />
          </div>
          <button className="primary-button" type="submit" disabled={buscando}>{buscando ? "Buscando…" : "Buscar cuenta"}</button>
        </form>
        {errorBusqueda && <div className="fx-alert" role="alert">{errorBusqueda}</div>}
      </div>

      {cuenta && (
        <>
          <CuentaResumen cuenta={cuenta} />
          <div className="form-card">
            <fieldset className="fx-estados" disabled>
              <legend>Estado de la cuenta</legend>
              <div className="fx-estado-grid">
                {ESTADOS_CUENTA.map((estado) => (
                  <label key={estado} className={`fx-estado ${cuenta.estado_cuenta === estado ? "selected" : ""}`}>
                    <input type="radio" name="estado_cuenta" value={estado} checked={cuenta.estado_cuenta === estado} readOnly />
                    <span><strong>{estado}</strong><small>{DESCRIPCION_ESTADO[estado]}</small></span>
                  </label>
                ))}
              </div>
            </fieldset>
            <div className="demo-warning" role="note">
              El cambio de estado de una cuenta todavía no está disponible: el CORE aún no ofrece esa operación.
            </div>
          </div>
        </>
      )}
    </div>
  );
}
