"use client";

import { useState } from "react";
import {
  ESTADOS_CUENTA,
  cambiarEstadoCuenta,
  mensajeDeError,
  verCuenta,
  type Cuenta,
  type EstadoCuenta,
} from "@/lib/cuentas";
import { CuentaResumen } from "./CuentaResumen";

const DESCRIPCION_ESTADO: Record<EstadoCuenta, string> = {
  ACTIVA: "Cuenta operativa.",
  BLOQUEADA: "No origina débitos (RGN-09).",
  BLOQUEADA_PREVENTIVA: "Bloqueo preventivo: no origina débitos.",
  INACTIVA: "Cuenta inactiva y reversible.",
  EMBARGO: "Bloqueo por embargo: no origina débitos.",
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
  const [estadoNuevo, setEstadoNuevo] = useState<EstadoCuenta | "">(cuentaInicial?.estado_cuenta as EstadoCuenta ?? "");
  const [motivo, setMotivo] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [errorCambio, setErrorCambio] = useState("");

  async function buscar(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const numero = numCuenta.trim();
    if (!numero) {
      setErrorBusqueda("Ingresa el número de cuenta.");
      return;
    }
    setBuscando(true);
    setErrorBusqueda("");
    setErrorCambio("");
    onNotice("");
    try {
      const encontrada = await verCuenta(numero);
      setCuenta(encontrada);
      setEstadoNuevo(encontrada.estado_cuenta as EstadoCuenta);
      setMotivo("");
    } catch (err) {
      setCuenta(null);
      setErrorBusqueda(mensajeDeError(err));
    } finally {
      setBuscando(false);
    }
  }

  async function guardar(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!cuenta || !estadoNuevo) return;
    setGuardando(true);
    setErrorCambio("");
    onNotice("");
    try {
      const modificada = await cambiarEstadoCuenta(cuenta.num_cuenta, estadoNuevo, motivo.trim() || undefined);
      setCuenta(modificada);
      setEstadoNuevo(modificada.estado_cuenta as EstadoCuenta);
      onNotice(`Estado de la cuenta cambiado a ${modificada.estado_cuenta}.`);
    } catch (err) {
      setErrorCambio(mensajeDeError(err));
    } finally {
      setGuardando(false);
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
            <form onSubmit={guardar} noValidate>
              <fieldset className="fx-estados" disabled={cuenta.estado_cuenta === "CANCELADA" || guardando}>
                <legend>Estado de la cuenta</legend>
                <div className="fx-estado-grid">
                  {ESTADOS_CUENTA.map((estado) => (
                    <label key={estado} className={`fx-estado ${estadoNuevo === estado ? "selected" : ""}`}>
                      <input
                        type="radio"
                        name="estado_cuenta"
                        value={estado}
                        checked={estadoNuevo === estado}
                        onChange={() => setEstadoNuevo(estado)}
                      />
                      <span><strong>{estado}</strong><small>{DESCRIPCION_ESTADO[estado]}</small></span>
                    </label>
                  ))}
                </div>
              </fieldset>
              <div className="fx-field">
                <label htmlFor="motivo_estado_cuenta">Motivo</label>
                <input
                  id="motivo_estado_cuenta"
                  value={motivo}
                  maxLength={255}
                  disabled={cuenta.estado_cuenta === "CANCELADA" || guardando}
                  onChange={(event) => setMotivo(event.target.value)}
                  placeholder="Motivo del cambio"
                />
              </div>
              {cuenta.estado_cuenta === "CANCELADA" && (
                <div className="demo-warning" role="note">
                  Una cuenta CANCELADA es final y no admite otro cambio.
                </div>
              )}
              {estadoNuevo === "CANCELADA" && (Number(cuenta.saldo_disponible) !== 0 || Number(cuenta.saldo_contable) !== 0) && (
                <div className="demo-warning" role="note">
                  La cuenta debe tener saldo contable y disponible iguales a cero antes de cancelarla.
                </div>
              )}
              {errorCambio && <div className="fx-alert" role="alert">{errorCambio}</div>}
              <button
                className="primary-button"
                type="submit"
                disabled={
                  guardando ||
                  cuenta.estado_cuenta === "CANCELADA" ||
                  estadoNuevo === cuenta.estado_cuenta ||
                  (estadoNuevo === "CANCELADA" && (Number(cuenta.saldo_disponible) !== 0 || Number(cuenta.saldo_contable) !== 0))
                }
              >
                {guardando ? "Guardando…" : "Cambiar estado"}
              </button>
            </form>
          </div>
        </>
      )}
    </div>
  );
}
