import type { Metadata } from "next";
import "../solicitud-credito/sol.css";

export const metadata: Metadata = {
  title: "Módulo de Cuentas · BNA",
  description:
    "Gestión y apertura de cuentas de ahorros del Banco Nacional de Arequipa (Integrado con COREDB).",
};

export default function CuentaLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="sol" lang="es">
      {children}
    </div>
  );
}
