import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Cierre de sesión único (hallazgo C1 de la prueba «solo con el mouse»): «Cerrar sesión» en el
// portal dejaba abiertos Solicitud de crédito (otra cookie) y el Home Banking (otra sesión del
// navegador). Ahora salir en cualquier pantalla cierra las tres sesiones, avisa a las otras
// pestañas y entrar con otro usuario cierra la sesión del anterior.
vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  api: { get: vi.fn(), post: vi.fn() },
}));
import { api } from "@/lib/api";
import { CLAVE_CIERRE, cerrarSesion, iniciarSesion, obtenerToken, obtenerUsuarioGuardado } from "@/lib/auth";
import VigilanteSesion from "../app/components/VigilanteSesion";
import SolicitudPage from "../app/solicitud-credito/page";

const post = vi.mocked(api.post);
const USUARIO = { id_usuario: "u-1", username: "operador.uno", nombre: "Operador Uno", rol: "OPERADOR" };
let fetchMock: ReturnType<typeof vi.fn>;
let reemplazar: ReturnType<typeof vi.fn>;
let recargar: ReturnType<typeof vi.fn>;
let ruta: string;

function conSesionCompleta() {
  localStorage.setItem("bna_access_token", "token-del-portal");
  localStorage.setItem("bna_usuario", JSON.stringify(USUARIO));
  sessionStorage.setItem("hb_sesion_bna", JSON.stringify({ codCliente: "CLI000000001", nombres: "Operador" }));
  sessionStorage.setItem("hb_ultima_tarjeta", "4111111111113886");
}

function llamadasA(url: string) {
  return fetchMock.mock.calls.filter(([u]) => u === url);
}

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  post.mockReset();
  fetchMock = vi.fn(async () => Response.json({ ok: true }));
  vi.stubGlobal("fetch", fetchMock);
  ruta = "/";
  reemplazar = vi.fn();
  recargar = vi.fn();
  vi.stubGlobal("location", {
    get pathname() { return ruta; },
    replace: reemplazar,
    reload: recargar,
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

describe("cerrarSesion cierra todas las sesiones del navegador", () => {
  it("CS-01 borra el token y el usuario del portal y la sesión del Home Banking", () => {
    conSesionCompleta();
    cerrarSesion();
    expect(obtenerToken()).toBeNull();
    expect(obtenerUsuarioGuardado()).toBeNull();
    expect(sessionStorage.getItem("hb_sesion_bna")).toBeNull();
    expect(sessionStorage.getItem("hb_ultima_tarjeta")).toBeNull();
  });

  it("CS-02 cierra la sesión de Solicitud de crédito (su cookie solo la borra el servidor)", () => {
    conSesionCompleta();
    cerrarSesion();
    const [llamada] = llamadasA("/api/solicitud-credito/auth/logout");
    expect(llamada).toBeDefined();
    const init = llamada[1] as RequestInit;
    expect(init.method).toBe("POST");
    // keepalive: la petición sigue aunque la pantalla navegue al login en el mismo clic.
    expect(init.keepalive).toBe(true);
  });

  it("CS-03 avisa a las otras pestañas", () => {
    conSesionCompleta();
    cerrarSesion();
    expect(localStorage.getItem(CLAVE_CIERRE)).toMatch(/^\d+$/);
  });

  it("CS-04 entrar con otro usuario cierra antes la sesión anterior (Solicitud y Home Banking)", async () => {
    conSesionCompleta();
    post.mockResolvedValue({ data: { access_token: "token-nuevo", token_type: "bearer", expires_in: 1800,
      usuario: { ...USUARIO, username: "asesora.dos", nombre: "Asesora Dos", rol: "ASESOR" } } });
    await iniciarSesion("asesora.dos", "clave-sintetica");
    expect(sessionStorage.getItem("hb_sesion_bna")).toBeNull();
    expect(llamadasA("/api/solicitud-credito/auth/logout")).toHaveLength(1);
    expect(obtenerToken()).toBe("token-nuevo");
    expect(obtenerUsuarioGuardado()?.username).toBe("asesora.dos");
  });
});

describe("Las otras pestañas se enteran del cierre", () => {
  function avisar(key: string, newValue: string | null) {
    act(() => { window.dispatchEvent(new StorageEvent("storage", { key, newValue })); });
  }

  it("CS-05 un cierre en otra pestaña lleva al login", () => {
    ruta = "/tarjetas";
    render(<VigilanteSesion />);
    avisar(CLAVE_CIERRE, String(Date.now()));
    expect(reemplazar).toHaveBeenCalledWith("/login");
  });

  it("CS-06 también si otra pestaña borró el token del portal", () => {
    ruta = "/solicitud-credito";
    render(<VigilanteSesion />);
    avisar("bna_access_token", null);
    expect(reemplazar).toHaveBeenCalledWith("/login");
  });

  it("CS-07 en el login no hace nada y no reacciona a otras claves", () => {
    ruta = "/tarjetas";
    render(<VigilanteSesion />);
    avisar("otra_clave", null);
    avisar("bna_access_token", "token-renovado");
    expect(reemplazar).not.toHaveBeenCalled();
    ruta = "/login";
    avisar(CLAVE_CIERRE, String(Date.now()));
    expect(reemplazar).not.toHaveBeenCalled();
  });

  it("CS-08 al volver con «Atrás» a una página guardada en memoria, la recarga para comprobar la sesión", () => {
    ruta = "/";
    render(<VigilanteSesion />);
    act(() => { window.dispatchEvent(new PageTransitionEvent("pageshow", { persisted: true })); });
    expect(recargar).toHaveBeenCalled();
  });
});

describe("Solicitud de crédito usa la sesión del portal", () => {
  const usuarioSol = { username: "asesora.dos", nombre: "Asesora Dos", rol: "ASESOR" };
  const politica = { version: "T", estado_aprobacion: "PROPUESTO", producto_nombre: "Crédito", monedas: ["PEN"],
    monto_minimo: "1000.00", monto_maximo: "50000.00", plazo_minimo_meses: 6, plazo_maximo_meses: 60, tea: "0.22",
    dias_por_periodo: 30, nota: "", integracion: "REAL" };
  let conCookie: boolean;

  function servidorSol() {
    fetchMock.mockImplementation(async (input: string, init?: RequestInit) => {
      const path = input.replace("/api/solicitud-credito/", "");
      if (path === "auth/me")
        return conCookie ? Response.json(usuarioSol) : Response.json({ detail: "Inicia sesión para continuar." }, { status: 401 });
      if (path === "auth/portal") {
        const cabeceras = new Headers(init?.headers);
        if (cabeceras.get("Authorization") !== "Bearer token-del-portal")
          return Response.json({ detail: "Inicia sesión para continuar." }, { status: 401 });
        conCookie = true;
        return Response.json({ usuario: usuarioSol });
      }
      if (path === "auth/login") { conCookie = true; return Response.json({ usuario: usuarioSol }); }
      if (path === "auth/logout") { conCookie = false; return Response.json({ ok: true }); }
      if (path === "policy") return Response.json(politica);
      if (path === "clients") return Response.json([]);
      if (path.startsWith("applications?")) return Response.json({ items: [], total: 0, limit: 50, offset: 0, estados: {} });
      return Response.json({ detail: "no simulado " + path }, { status: 404 });
    });
  }

  beforeEach(() => { conCookie = false; servidorSol(); });

  it("CS-09 con sesión en el portal entra sin pedir otra vez usuario y clave", async () => {
    localStorage.setItem("bna_access_token", "token-del-portal");
    localStorage.setItem("bna_usuario", JSON.stringify({ ...USUARIO, username: "asesora.dos" }));
    render(<SolicitudPage />);
    expect(await screen.findByText("Asesora Dos")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Bienvenido a BNA" })).not.toBeInTheDocument();
    expect(llamadasA("/api/solicitud-credito/auth/portal")).toHaveLength(1);
  });

  it("CS-10 sin sesión en el portal muestra su acceso y no intenta adoptar nada", async () => {
    render(<SolicitudPage />);
    expect(await screen.findByRole("heading", { name: "Bienvenido a BNA" })).toBeInTheDocument();
    expect(llamadasA("/api/solicitud-credito/auth/portal")).toHaveLength(0);
  });

  it("CS-11 «Cerrar sesión» en Solicitud cierra también el portal y el Home Banking", async () => {
    conSesionCompleta();
    localStorage.setItem("bna_usuario", JSON.stringify({ ...USUARIO, username: "asesora.dos" }));
    render(<SolicitudPage />);
    await screen.findByText("Asesora Dos");
    await userEvent.click(screen.getByRole("button", { name: "Cerrar sesión" }));
    await waitFor(() => expect(obtenerToken()).toBeNull());
    expect(sessionStorage.getItem("hb_sesion_bna")).toBeNull();
    expect(localStorage.getItem(CLAVE_CIERRE)).not.toBeNull();
  });

  it("CS-12 entrar en Solicitud con otro usuario cierra la sesión del portal del anterior", async () => {
    // Token que Solicitud no acepta (por ejemplo, vencido): se queda en su acceso.
    localStorage.setItem("bna_access_token", "token-de-otro");
    localStorage.setItem("bna_usuario", JSON.stringify(USUARIO));
    sessionStorage.setItem("hb_sesion_bna", JSON.stringify({ codCliente: "CLI000000001" }));
    render(<SolicitudPage />);
    await screen.findByRole("heading", { name: "Bienvenido a BNA" });
    await userEvent.type(screen.getByLabelText("Usuario"), "asesora.dos");
    await userEvent.type(screen.getByLabelText("Contraseña"), "clave-sintetica");
    await userEvent.click(screen.getByRole("button", { name: "Ingresar al portal" }));
    await screen.findByText("Asesora Dos");
    expect(obtenerToken()).toBeNull();
    expect(sessionStorage.getItem("hb_sesion_bna")).toBeNull();
  });
});
