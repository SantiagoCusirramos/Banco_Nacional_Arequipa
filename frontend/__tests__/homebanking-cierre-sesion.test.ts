import { readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Cierre de sesión único en el Home Banking (hallazgo C1): su «Cerrar sesión» solo borraba su
// propia sesión del navegador; la del portal y la de Solicitud seguían abiertas, y al revés. Tras
// salir, «Atrás» volvía a mostrar al cliente atendido.
const HB = resolve(process.cwd(), "public/homebanking"); // vitest corre en frontend/
const leer = (f: string) => readFileSync(join(HB, f), "utf8");

let fetchMock: ReturnType<typeof vi.fn>;
let destino: string | null;

// Los scripts declaran `const Sesion`, `const Bus`: solo existen dentro de la misma evaluación,
// así que el código de la prueba va en ella y se devuelve su valor.
function ejecutar(scripts: string[], codigo = "undefined") {
  return (0, eval)([...scripts.map((s) => leer(`js/${s}`)), codigo].join("\n;\n"));
}

function conSesionCompleta() {
  localStorage.setItem("bna_access_token", "token-del-portal");
  localStorage.setItem("bna_usuario", JSON.stringify({ username: "operador.uno" }));
  sessionStorage.setItem("hb_sesion_bna", JSON.stringify({ codCliente: "CLI000000001", nombres: "Carmen", dni: "x" }));
  sessionStorage.setItem("hb_ultima_tarjeta", "4111111111113886");
}

beforeEach(() => {
  destino = null;
  fetchMock = vi.fn(async () => Response.json({ ok: true }));
  vi.stubGlobal("fetch", fetchMock);
  vi.stubGlobal("location", {
    get href() { return destino ?? "http://localhost/homebanking/cuentas.html"; },
    set href(v: string) { destino = v; },
    replace: (v: string) => { destino = v; },
    reload: vi.fn(),
    pathname: "/homebanking/cuentas.html",
  });
  document.body.innerHTML = '<span id="sesionNombre"></span><span id="sesionCliente"></span><button id="btnSalir">Cerrar sesión</button>';
});

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
  document.body.innerHTML = "";
});

describe("Home Banking: una sola sesión para cerrar", () => {
  it("HB-40 «Cerrar sesión» cierra el Home Banking, el portal y Solicitud, y avisa a las otras pestañas", () => {
    conSesionCompleta();
    ejecutar(["comun.js"], "pintarCabecera()");
    (document.getElementById("btnSalir") as HTMLButtonElement).click();
    expect(sessionStorage.getItem("hb_sesion_bna")).toBeNull();
    expect(sessionStorage.getItem("hb_ultima_tarjeta")).toBeNull();
    expect(localStorage.getItem("bna_access_token")).toBeNull();
    expect(localStorage.getItem("bna_usuario")).toBeNull();
    expect(localStorage.getItem("bna_cierre_sesion")).toMatch(/^\d+$/);
    const llamada = fetchMock.mock.calls.find(([u]) => u === "/api/solicitud-credito/auth/logout");
    expect(llamada?.[1]).toMatchObject({ method: "POST", keepalive: true });
    expect(destino).toBe("index.html");
  });

  it("HB-41 sin la sesión del banco (token del portal) no muestra al cliente atendido", () => {
    sessionStorage.setItem("hb_sesion_bna", JSON.stringify({ codCliente: "CLI000000001" }));
    expect(ejecutar(["comun.js"], "Sesion.exigir()")).toBeNull();
    expect(sessionStorage.getItem("hb_sesion_bna")).toBeNull();
    expect(destino).toBe("index.html");
  });

  it("HB-42 con las dos sesiones, sigue en la página", () => {
    conSesionCompleta();
    expect(ejecutar(["comun.js"], "Sesion.exigir()")).toMatchObject({ codCliente: "CLI000000001" });
    expect(destino).toBeNull();
  });

  it("HB-43 un cierre en otra pestaña lleva al acceso del Home Banking", () => {
    conSesionCompleta();
    ejecutar(["comun.js"], "Sesion.exigir()");
    localStorage.removeItem("bna_access_token");
    window.dispatchEvent(new StorageEvent("storage", { key: "bna_cierre_sesion", newValue: String(Date.now()) }));
    expect(sessionStorage.getItem("hb_sesion_bna")).toBeNull();
    expect(destino).toBe("index.html");
  });

  it("HB-44 al volver con «Atrás» tras salir, no muestra la página guardada", () => {
    conSesionCompleta();
    ejecutar(["comun.js"], "Sesion.exigir()");
    localStorage.removeItem("bna_access_token");
    sessionStorage.removeItem("hb_sesion_bna");
    window.dispatchEvent(new PageTransitionEvent("pageshow", { persisted: true }));
    expect(destino).toBe("index.html");
  });

  it("HB-45 entrar con un usuario cierra antes cualquier sesión anterior y guarda el usuario del portal", async () => {
    conSesionCompleta();
    fetchMock.mockImplementation(async (url: string) => {
      if (url === "/api/core/coredb/auth/login") return Response.json({ access_token: "token-nuevo" });
      if (url === "/api/core/coredb/auth/me")
        return Response.json({ id_usuario: "u-2", username: "asesora.dos", rol: "ASESOR", acciones: [] });
      return Response.json({ ok: true });
    });
    await ejecutar(["bus.js", "comun.js"], 'Bus.autenticar("asesora.dos", "clave-sintetica", "CLI000000002")');
    expect(sessionStorage.getItem("hb_sesion_bna")).toBeNull();
    expect(fetchMock.mock.calls.some(([u]) => u === "/api/solicitud-credito/auth/logout")).toBe(true);
    expect(localStorage.getItem("bna_access_token")).toBe("token-nuevo");
    expect(JSON.parse(localStorage.getItem("bna_usuario") || "{}")).toMatchObject({ username: "asesora.dos", rol: "ASESOR" });
  });
});
