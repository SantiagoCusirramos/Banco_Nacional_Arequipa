import type { Metadata } from "next";
import "../solicitud-credito/sol.css";

export const metadata: Metadata = {
  title: "Pagar cuota · BNA",
  description: "Pago de cuotas de crédito del Banco Nacional de Arequipa (módulo Cobranza).",
};

export default function PagarCuotaLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="sol" lang="es">
      {children}
    </div>
  );
}
