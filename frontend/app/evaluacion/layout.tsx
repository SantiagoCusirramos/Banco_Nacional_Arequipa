import type { Metadata } from "next";
import "../solicitud-credito/sol.css";
import "./evaluacion.css";

export const metadata: Metadata = {
  title: "Evaluación Crediticia · BNA",
  description:
    "Bandeja del analista: expedientes de Solicitud, situación financiera, decisión y aprobación para Desembolso.",
};

export default function EvaluacionLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="sol" lang="es">
      {children}
    </div>
  );
}
