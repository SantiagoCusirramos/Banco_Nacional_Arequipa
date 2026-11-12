import type { Metadata } from "next";
import "../solicitud-credito/sol.css";
import "./tarjetas.css";

export const metadata: Metadata = {
  title: "Módulo de Tarjetas · BNA",
  description: "Consulta, emisión y cambio de estado de tarjetas del Banco Nacional de Arequipa, sobre COREDB.",
};

export default function TarjetasLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="sol" lang="es">
      {children}
    </div>
  );
}
