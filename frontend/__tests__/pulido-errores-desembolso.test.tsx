import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AlertaError } from "../app/desembolso/_componentes/ui";
import { ErrorApi } from "../lib/desembolso/api";

// Los avisos de Desembolso también son pantallas que ve el personal: el código interno y la
// correlación sirven al diagnóstico, no a quien está operando.
describe("Avisos de error de Desembolso", () => {
  it("PU-ER-01 no muestra el código interno ni la correlación", () => {
    render(
      <AlertaError
        error={new ErrorApi("No se pudo completar la operación.", "PERMISO_DENEGADO", 403, "corr-123")}
      />,
    );
    const texto = screen.getByRole("alert").textContent ?? "";
    expect(texto).not.toMatch(/PERMISO_DENEGADO|correlaci[oó]n|corr-123|\b403\b/);
  });
});
