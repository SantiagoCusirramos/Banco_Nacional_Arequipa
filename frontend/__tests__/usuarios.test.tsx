import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError, AxiosHeaders } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Usuarios y contraseñas (hallazgos B1 y B2 de la prueba «solo con el mouse»): el alta estaba en
// una pestaña del login que fallaba sin sesión («Falta el encabezado Authorization…») y la
// contraseña la inventaba el administrador. Ahora hay una pantalla «Usuarios» para quien puede
// crear usuarios, COREDB genera la contraseña inicial y se muestra una sola vez, y el primer
// ingreso obliga a cambiarla.
const router = { replace: vi.fn(), push: vi.fn() };
vi.mock("next/navigation", () => ({ useRouter: () => router, usePathname: () => "/usuarios" }));
vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  api: { get: vi.fn(), post: vi.fn() },
}));
import { api, alExigirCambioDeClave } from "@/lib/api";
import LoginPage from "../app/login/page";
import CambiarClavePage from "../app/cambiar-clave/page";
import UsuariosPage from "../app/usuarios/page";
import { BancaPersonal } from "../app/components/BancaPersonal";

const get = vi.mocked(api.get);
const post = vi.mocked(api.post);
const ADMIN = { id_usuario: "a-1", username: "admin", nombre: "Administrador", rol: "ADMINISTRADOR", acciones: ["CREAR_USUARIO", "ASIGNAR_ROLES"] };
const FILA = { id_usuario: "u-2", username: "asesora.dos", nombre: "Asesora Dos", rol: "ASESOR", modulo: null, id_empleado: null,
  activo: true, creado_en: "2026-11-22T10:00:00Z", debe_cambiar_clave: true };
let copiar: ReturnType<typeof vi.fn>;

function sesion(usuario = ADMIN) {
  localStorage.setItem("bna_access_token", "token");
  localStorage.setItem("bna_usuario", JSON.stringify(usuario));
}

beforeEach(() => {
  localStorage.clear();
  get.mockReset();
  post.mockReset();
  router.replace.mockReset();
  router.push.mockReset();
  copiar = vi.fn(async () => undefined);
  Object.defineProperty(navigator, "clipboard", { value: { writeText: copiar }, configurable: true });
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ ok: true })));
});
afterEach(() => vi.unstubAllGlobals());

describe("Login", () => {
  it("US-01 ya no tiene la pestaña «Registrar usuario»", () => {
    render(<LoginPage />);
    expect(screen.queryByText("Registrar usuario")).not.toBeInTheDocument();
    expect(screen.queryByText(/POST \/coredb/)).not.toBeInTheDocument();
  });

  it("US-02 con la contraseña inicial lleva a cambiarla", async () => {
    post.mockResolvedValue({ data: { access_token: "t", token_type: "bearer", expires_in: 1800,
      usuario: { ...FILA, debe_cambiar_clave: true } } });
    render(<LoginPage />);
    await userEvent.type(screen.getByLabelText("Usuario"), "asesora.dos");
    await userEvent.type(screen.getByLabelText("Contraseña"), "Kq7mPx2vRt9w");
    await userEvent.click(screen.getByRole("button", { name: /Ingresar/ }));
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/cambiar-clave"));
  });
});

describe("Cambio de contraseña", () => {
  async function llenar(actual: string, nueva: string, repetir: string) {
    render(<CambiarClavePage />);
    await screen.findByRole("heading", { name: /Cambia tu contraseña/ });
    await userEvent.type(screen.getByLabelText("Contraseña actual"), actual);
    await userEvent.type(screen.getByLabelText("Contraseña nueva"), nueva);
    await userEvent.type(screen.getByLabelText("Repite la contraseña nueva"), repetir);
    await userEvent.click(screen.getByRole("button", { name: /Guardar contraseña/ }));
  }

  it("US-03 si la repetición no coincide, avisa y no la envía", async () => {
    sesion({ ...ADMIN, acciones: [] });
    get.mockResolvedValue({ data: { ...ADMIN, acciones: [], debe_cambiar_clave: true } });
    await llenar("Kq7mPx2vRt9w", "mi-clave-propia-1", "otra-cosa-1");
    expect(await screen.findByRole("alert")).toHaveTextContent("no coinciden");
    expect(post).not.toHaveBeenCalled();
  });

  it("US-04 la guarda y lleva al portal", async () => {
    sesion({ ...ADMIN, acciones: [] });
    get.mockResolvedValue({ data: { ...ADMIN, acciones: [], debe_cambiar_clave: true } });
    post.mockResolvedValue({ data: { debe_cambiar_clave: false } });
    await llenar("Kq7mPx2vRt9w", "mi-clave-propia-1", "mi-clave-propia-1");
    await waitFor(() => expect(post).toHaveBeenCalledWith("/coredb/auth/clave", { actual: "Kq7mPx2vRt9w", nueva: "mi-clave-propia-1" }));
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/"));
  });

  it("US-05 un 403 CAMBIO_CLAVE_OBLIGATORIO de cualquier pantalla lleva a cambiarla", () => {
    const asignar = vi.fn();
    vi.stubGlobal("location", { pathname: "/tarjetas", assign: asignar });
    const err = new AxiosError("x", "ERR_BAD_REQUEST", undefined, undefined, {
      status: 403, statusText: "", headers: {}, config: { headers: new AxiosHeaders() },
      data: { error: { code: "CAMBIO_CLAVE_OBLIGATORIO", message: "Antes de continuar, cambia tu contraseña." } },
    });
    expect(() => alExigirCambioDeClave(err)).toThrow();
    expect(asignar).toHaveBeenCalledWith("/cambiar-clave");
  });
});

describe("Pantalla Usuarios", () => {
  function servidor(lista = [FILA]) {
    get.mockImplementation(async (url: string) => {
      if (url === "/coredb/auth/me") return { data: { ...ADMIN, debe_cambiar_clave: false } };
      if (url.startsWith("/coredb/usuarios")) return { data: lista };
      throw new Error("no simulado " + url);
    });
  }

  it("US-06 quien no puede crear usuarios ve un aviso y no la lista", async () => {
    sesion({ ...ADMIN, rol: "OPERADOR", acciones: ["VER_CUENTA"] });
    get.mockResolvedValue({ data: { ...ADMIN, rol: "OPERADOR", acciones: ["VER_CUENTA"], debe_cambiar_clave: false } });
    render(<UsuariosPage />);
    expect(await screen.findByText(/Esta pantalla es para administradores/)).toBeInTheDocument();
    expect(get).not.toHaveBeenCalledWith(expect.stringMatching(/^\/coredb\/usuarios/));
  });

  it("US-07 lista los usuarios con su rol y si deben cambiar la contraseña", async () => {
    sesion();
    servidor();
    render(<UsuariosPage />);
    const fila = (await screen.findByText("asesora.dos")).closest("tr")!;
    expect(within(fila).getByText("Asesora Dos")).toBeInTheDocument();
    expect(within(fila).getByText(/Debe cambiar su contraseña/)).toBeInTheDocument();
  });

  it("US-08 el alta no pide contraseña: muestra la inicial una sola vez, con Copiar", async () => {
    sesion();
    servidor([]);
    post.mockResolvedValue({ data: { ...FILA, username: "operador.tres", nombre: "Operador Tres", rol: "OPERADOR", clave_inicial: "Kq7mPx2vRt9w" } });
    render(<UsuariosPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Nuevo usuario" }));
    expect(screen.queryByLabelText(/Contraseña/)).not.toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Nombre completo"), "Operador Tres");
    await userEvent.type(screen.getByLabelText("Usuario"), "operador.tres");
    await userEvent.selectOptions(screen.getByLabelText("Rol"), "OPERADOR");
    await userEvent.click(screen.getByRole("button", { name: "Crear usuario" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/coredb/usuarios", { username: "operador.tres", nombre: "Operador Tres", rol: "OPERADOR" }));
    const panel = await screen.findByRole("region", { name: /Contraseña inicial/ });
    expect(within(panel).getByText("Kq7mPx2vRt9w")).toBeInTheDocument();
    expect(within(panel).getByText(/no se volverá a mostrar/i)).toBeInTheDocument();
    await userEvent.click(within(panel).getByRole("button", { name: "Copiar" }));
    expect(copiar).toHaveBeenCalledWith("Kq7mPx2vRt9w");
    await userEvent.click(within(panel).getByRole("button", { name: /Ya la entregué/ }));
    expect(screen.queryByText("Kq7mPx2vRt9w")).not.toBeInTheDocument();
  });

  it("US-09 «Renovar contraseña» pide confirmación y muestra la temporal una vez", async () => {
    sesion();
    servidor();
    post.mockResolvedValue({ data: { usuario: FILA, clave_inicial: "Zt8nQw3eLp5x" } });
    render(<UsuariosPage />);
    const fila = (await screen.findByText("asesora.dos")).closest("tr")!;
    await userEvent.click(within(fila).getByRole("button", { name: "Renovar contraseña" }));
    const dialogo = await screen.findByRole("dialog");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Sí, renovar" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/coredb/usuarios/u-2/clave"));
    expect(await screen.findByText("Zt8nQw3eLp5x")).toBeInTheDocument();
  });

  it("US-10 cambia el rol, desactiva y desbloquea el ingreso", async () => {
    sesion();
    servidor();
    post.mockResolvedValue({ data: FILA });
    render(<UsuariosPage />);
    const fila = (await screen.findByText("asesora.dos")).closest("tr")!;
    await userEvent.selectOptions(within(fila).getByLabelText("Rol de asesora.dos"), "ANALISTA");
    await waitFor(() => expect(post).toHaveBeenCalledWith("/coredb/usuarios/u-2/rol", { rol: "ANALISTA" }));
    await userEvent.click(within(fila).getByRole("button", { name: "Desactivar" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/coredb/usuarios/u-2/estado", { activo: false }));
    await userEvent.click(within(fila).getByRole("button", { name: "Desbloquear ingreso" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/coredb/usuarios/u-2/desbloqueo"));
  });
});

describe("Cuentas de servicio", () => {
  it("US-12 una cuenta de servicio (un módulo) no se desactiva, renueva ni desbloquea desde aquí", async () => {
    sesion();
    get.mockImplementation(async (url: string) => {
      if (url === "/coredb/auth/me") return { data: { ...ADMIN, debe_cambiar_clave: false } };
      return { data: [{ ...FILA, id_usuario: "s-1", username: "svc-captacion", nombre: "Captación", rol: "SERVICIO", modulo: "CLIENTES", debe_cambiar_clave: false }] };
    });
    render(<UsuariosPage />);
    const fila = (await screen.findByText("svc-captacion")).closest("tr")!;
    expect(within(fila).queryByRole("button")).not.toBeInTheDocument();
    expect(within(fila).queryByRole("combobox")).not.toBeInTheDocument();
  });
});

describe("Portal", () => {
  it("US-11 el menú muestra «Usuarios» solo a quien puede crear usuarios", () => {
    const { unmount } = render(<BancaPersonal usuario={ADMIN} onSalir={() => {}} />);
    expect(screen.getAllByRole("link", { name: /Usuarios/ }).length).toBeGreaterThan(0);
    unmount();
    render(<BancaPersonal usuario={{ ...ADMIN, rol: "OPERADOR", acciones: ["VER_CUENTA"] }} onSalir={() => {}} />);
    expect(screen.queryByRole("link", { name: /Usuarios/ })).not.toBeInTheDocument();
  });
});
