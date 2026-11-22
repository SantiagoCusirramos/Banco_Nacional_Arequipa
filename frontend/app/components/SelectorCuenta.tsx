"use client";

import { useEffect, useState } from "react";
import { cuentasDeCliente, formatoMoneda, type Cuenta } from "@/lib/cuentas";
import { enmascararCuenta } from "@/lib/continuidad";

type Props = {
  id: string;
  label: string;
  codCliente: string;
  value: string;
  onChange: (numCuenta: string) => void;
  placeholder?: string;
};

/** Lista las cuentas del titular para no copiar el número a mano; la entrada manual sigue disponible. */
export default function SelectorCuenta({ id, label, codCliente, value, onChange, placeholder }: Props) {
  const [cuentas, setCuentas] = useState<Cuenta[]>([]);
  const [numero, setNumero] = useState(value);
  const [mensaje, setMensaje] = useState("");

  useEffect(() => { setNumero(value); }, [value]);

  useEffect(() => {
    let activo = true;
    setCuentas([]);
    if (!codCliente) return;
    cuentasDeCliente(codCliente)
      .then((encontradas) => { if (activo) setCuentas(encontradas); })
      .catch(() => { if (activo) setMensaje("No se pudieron cargar las cuentas del cliente."); });
    return () => { activo = false; };
  }, [codCliente]);

  function elegir(cuenta: Cuenta) {
    setNumero(cuenta.num_cuenta);
    setMensaje("");
    onChange(cuenta.num_cuenta);
  }

  return (
    <div className="fx-field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        autoComplete="off"
        placeholder={placeholder ?? "Número de cuenta"}
        value={numero}
        onChange={(event) => {
          setNumero(event.target.value);
          onChange(event.target.value);
        }}
      />
      {cuentas.length > 0 && (
        <div className="selector-opciones">
          {cuentas.map((cuenta) => (
            <button
              className="selector-opcion"
              type="button"
              key={cuenta.num_cuenta}
              onClick={() => elegir(cuenta)}
            >
              <strong>{enmascararCuenta(cuenta.num_cuenta)}</strong>
              <span>{cuenta.moneda}</span>
              <span>{formatoMoneda(cuenta.saldo_disponible, cuenta.moneda)}</span>
            </button>
          ))}
        </div>
      )}
      {mensaje && <span className="fx-hint" role="status">{mensaje}</span>}
    </div>
  );
}
