"use client";

import { FormEvent, useId, useState } from "react";
import { esTrivial, generarPin } from "@/lib/pin";

type Props = {
  /** Largo del PIN: 4 para el cajero, 6 para la clave web o Chaski. */
  digitos: number;
  /** Cómo se llama en pantalla: «PIN del cajero», «PIN de Chaski»… */
  nombre: string;
  /** Lo envía al servidor; si falla, lanza el error con el mensaje para mostrar. */
  asignar: (valor: string) => Promise<void>;
  /** Texto de los botones (por omisión «Generar y asignar» y «Asignar»). */
  textoGenerar?: string;
  textoAsignar?: string;
};

type Modo = "generar" | "clienta";

/**
 * Asignar un PIN sin que el empleado lo elija (hallazgo C6): por omisión el sistema lo genera y
 * se muestra una sola vez para entregarlo; o la clienta lo escribe dos veces en esta pantalla.
 */
export function ClaveNueva({ digitos, nombre, asignar, textoGenerar = "Generar y asignar", textoAsignar = "Asignar" }: Props) {
  const id = useId();
  const [modo, setModo] = useState<Modo>("generar");
  const [valor, setValor] = useState("");
  const [repetido, setRepetido] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [paraEntregar, setParaEntregar] = useState<string | null>(null);
  const soloDigitos = (v: string) => v.replace(/\D/g, "").slice(0, digitos);

  async function enviar(pin: string, mostrar: boolean) {
    setEnviando(true);
    setError("");
    try {
      await asignar(pin);
      if (mostrar) setParaEntregar(pin);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo asignar.");
    } finally {
      setEnviando(false);
    }
  }

  function generar() {
    if (enviando) return;
    setParaEntregar(null);
    void enviar(generarPin(digitos), true);
  }

  function escrito(e: FormEvent) {
    e.preventDefault();
    if (enviando) return;
    const a = valor, b = repetido;
    setValor(""); setRepetido("");
    if (a.length !== digitos) return setError(`El ${nombre} tiene ${digitos} dígitos.`);
    if (a !== b) return setError("Los dos valores no coinciden. Pide a la clienta que lo escriba otra vez.");
    if (esTrivial(a)) return setError("Es muy fácil de adivinar (todos iguales o seguidos). Pide otro a la clienta.");
    void enviar(a, false);
  }

  return (
    <div className="clave-nueva">
      <fieldset style={{ border: 0, padding: 0, margin: "0 0 12px" }}>
        <legend style={{ fontWeight: 600, marginBottom: "6px" }}>¿Quién pone el {nombre}?</legend>
        <label style={{ marginRight: "16px" }}>
          <input type="radio" name={`${id}-modo`} checked={modo === "generar"} onChange={() => { setModo("generar"); setError(""); }} />
          {" "}Generarlo al azar (recomendado)
        </label>
        <label>
          <input type="radio" name={`${id}-modo`} checked={modo === "clienta"} onChange={() => { setModo("clienta"); setError(""); setParaEntregar(null); }} />
          {" "}La clienta lo escribe
        </label>
      </fieldset>

      {error && <div role="alert" className="sol-alert error">{error}</div>}

      {modo === "generar" ? (
        <button type="button" className="sol-button primary" disabled={enviando} onClick={generar}>
          {enviando ? "Asignando…" : textoGenerar}
        </button>
      ) : (
        <form onSubmit={escrito} style={{ display: "grid", gap: "8px", maxWidth: "320px" }}>
          <p style={{ margin: 0 }}>Gira la pantalla hacia la clienta: el {nombre} solo lo conoce ella.</p>
          <label htmlFor={`${id}-1`}>{nombre} (lo escribe la clienta)</label>
          <input id={`${id}-1`} type="password" inputMode="numeric" autoComplete="off" value={valor}
            onChange={(e) => setValor(soloDigitos(e.target.value))} maxLength={digitos} />
          <label htmlFor={`${id}-2`}>Repite el {nombre}</label>
          <input id={`${id}-2`} type="password" inputMode="numeric" autoComplete="off" value={repetido}
            onChange={(e) => setRepetido(soloDigitos(e.target.value))} maxLength={digitos} />
          <button type="submit" className="sol-button primary" disabled={enviando}>{textoAsignar}</button>
        </form>
      )}

      {paraEntregar && (
        <section role="region" aria-labelledby={`${id}-titulo`} className="sol-card sol-card-pad" style={{ marginTop: "12px", borderColor: "#c9a227" }}>
          <h3 id={`${id}-titulo`}>{nombre} para entregar</h3>
          <p style={{ fontFamily: "monospace", fontSize: "28px", letterSpacing: "6px", margin: "8px 0" }}>{paraEntregar}</p>
          <p><strong>No se volverá a mostrar.</strong> Entrégaselo a la clienta en privado; tú no lo anotes.</p>
          <button type="button" className="sol-button primary" onClick={() => setParaEntregar(null)}>Ya lo entregué</button>
        </section>
      )}
    </div>
  );
}
