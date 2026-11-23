"use client";

import type { ReactNode } from "react";

type Props = {
  titulo?: string;
  mensaje: string;
  detalle?: ReactNode;
};

export function AvisoPermiso({ titulo = "Esta pantalla no está disponible para tu rol", mensaje, detalle }: Props) {
  return (
    <section className="sol-card" role="alert" aria-live="polite" style={{ maxWidth: 760, margin: "24px auto" }}>
      <div className="sol-card-title">
        <div>
          <h2>{titulo}</h2>
          <p>Acceso no disponible para tu usuario.</p>
        </div>
      </div>
      <p>{mensaje}</p>
      {detalle ? <p className="sol-caption" style={{ marginTop: 10 }}>{detalle}</p> : null}
    </section>
  );
}
