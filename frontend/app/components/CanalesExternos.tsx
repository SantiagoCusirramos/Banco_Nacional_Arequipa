"use client";

import { useEffect, useState } from "react";

type Config = { urlCajero: string | null; urlApk: string | null };

/**
 * El cajero y la app Chaski viven en otras direcciones (las del despliegue, en /api/config-publica).
 * Sin URL configurada no se muestra nada: mejor sin enlace que con uno roto.
 */
export function CanalesExternos() {
  const [config, setConfig] = useState<Config | null>(null);
  useEffect(() => {
    let vigente = true;
    fetch("/api/config-publica")
      .then((r) => (r.ok ? r.json() : null))
      .then((datos: Config | null) => { if (vigente && datos) setConfig(datos); })
      .catch(() => { /* sin configuración: no hay enlaces */ });
    return () => { vigente = false; };
  }, []);
  if (!config?.urlCajero && !config?.urlApk) return null;
  return (
    <>
      <div className="section-heading"><div><h2>Canales para la clienta</h2><p>Se abren en otra pestaña.</p></div></div>
      <div className="quick-grid">
        {config.urlCajero && (
          <a href={config.urlCajero} target="_blank" rel="noopener noreferrer" className="quick-action">
            <span className="quick-icon blue">🏧</span>
            <span><strong>Cajero (simulador)</strong><small>Lo abre un operador; la clienta inserta la tarjeta con su documento y los 4 últimos dígitos</small></span>
            <b>↗</b>
          </a>
        )}
        {config.urlApk && (
          <a href={config.urlApk} target="_blank" rel="noopener noreferrer" className="quick-action">
            <span className="quick-icon blue">📱</span>
            <span><strong>Descargar Chaski</strong><small>La app de la billetera; en Billetera está el QR para conectarla con el banco</small></span>
            <b>↗</b>
          </a>
        )}
      </div>
    </>
  );
}
