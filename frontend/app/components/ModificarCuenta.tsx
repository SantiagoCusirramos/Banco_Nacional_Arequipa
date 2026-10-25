"use client";

import { useState } from "react";
import {
  ESTADOS_CUENTA,
  mensajeDeError,
  modificarCuenta,
  verCuenta,
  type Cuenta,
  type EstadoCuenta,
} from "@/lib/cuentas";
import { CuentaResumen } from "./CuentaResumen";

const DESCRIPCION_ESTADO: Record<EstadoCuenta, string> = {
  ACTIVA: "Cuenta operativa.",
  INACTIVA: "No origina débitos (RGN-09).",
  BLOQUEADA: "No origina débitos (RGN-09).",
  EMBARGO: "Cuenta con embargo registrado.",
};

type Props = {
  cuentaInicial?: Cuenta | null;
  onNotice: (mensaje: string) => void;
};

export function ModificarCuenta({ cuentaInicial = null, onNotice }: Props) {
  const [numCuenta, setNumCuenta] = useState(cuentaInicial?.num_cuenta ?? "");
  const [cuenta, setCuenta] = useState<Cuenta | null>(cuentaInicial);
  const [nuevoEstado, setNuevoEstado] = useState<string>(cuentaInicial?.estado_cuenta ?? "");
  const [buscando, setBuscando] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [errorBusqueda, setErrorBusqueda] = useState("");
  const [errorGuardado, setErrorGuardado] = useState("");

  async function buscar(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const numero = numCuenta.trim();
    if (!numero) {
      setErrorBusqueda("Ingresa el número de cuenta.");
      return;
    }
    setBuscando(true);
    setErrorBusqueda("");
    setErrorGuardado("");
    onNotice("");
    try {
      const encontrada = await verCuenta(numero);
      setCuenta(encontrada);
      setNuevoEstado(encontrada.estado_cuenta);
    } catch (err) {
      setCuenta(null);
      setErrorBusqueda(mensajeDeError(err));
    } finally {
      setBuscando(false);
    }
  }

  async function guardar(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!cuenta) return;
    if (!ESTADOS_CUENTA.includes(nuevoEstado as EstadoCuenta)) {
      setErrorGuardado("Selecciona un estado válido.");
      return;
    }
    if (nuevoEstado === cuenta.estado_cuenta) {
      setErrorGuardado("La cuenta ya se encuentra en ese estado.");
      return;
    }
    setGuardando(true);
    setErrorGuardado("");
    try {
      const actualizada = await modificarCuenta(cuenta.num_cuenta, nuevoEstado as EstadoCuenta);
      setCuenta(actualizada);
      setNuevoEstado(actualizada.estado_cuenta);
      onNotice(`Cuenta ${actualizada.num_cuenta} actualizada: estado ${actualizada.estado_cuenta}.`);
    } catch (err) {
      setErrorGuardado(mensajeDeError(err));
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
            <p>Busca la cuenta por su número y cambia su estado.</p>
          </div>
        </div>
        <form className="fx-search" onSubmit={buscar} noValidate>
          <div className="fx-field fx-grow">
            <label htmlFor="num_cuenta">Número de cuenta</label>
            <input id="num_cuenta" autoComplete="off" inputMode="numeric" placeholder="Ej. 14 dígitos" maxLength={20} value={numCuenta} onChange={(e) => setNumCuenta(e.target.value)} aria-invalid={!!errorBusqueda} />
          </div>
          <button className="primary-button" type="submit" disabled={buscando}>{buscando ? "Buscando…" : "Buscar cuenta"}</button>
        </form>
        {errorBusqueda && <div className="fx-alert" role="alert">{errorBusqueda}</div>}
      </div>

      {cuenta && (
        <>
          <CuentaResumen cuenta={cuenta} />
          <form className="form-card" onSubmit={guardar} noValidate>
            <fieldset className="fx-estados">
              <legend>Nuevo estado de la cuenta</legend>
              <div className="fx-estado-grid">
                {ESTADOS_CUENTA.map((estado) => (
                  <label key={estado} className={`fx-estado ${nuevoEstado === estado ? "selected" : ""}`}>
                    <input type="radio" name="estado_cuenta" value={estado} checked={nuevoEstado === estado} onChange={() => { setNuevoEstado(estado); setErrorGuardado(""); }} />
                    <span><strong>{estado}</strong><small>{DESCRIPCION_ESTADO[estado]}</small></span>
                  </label>
                ))}
              </div>
            </fieldset>
            {errorGuardado && <div className="fx-alert" role="alert">{errorGuardado}</div>}
            <button className="primary-button" type="submit" disabled={guardando || nuevoEstado === cuenta.estado_cuenta}>
              {guardando ? "Guardando…" : "Guardar cambios"} <span>→</span>
            </button>
          </form>
        </>
      )}
    </div>
  );
}
