import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

const router = { replace: vi.fn(), push: vi.fn() };
vi.mock("next/navigation", () => ({ useRouter: () => router }));

vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  api: { get: vi.fn(), post: vi.fn() },
}));
import { api, cabecerasDeOperacion, mensajeError } from "@/lib/api";
import { obtenerMiPerfil, obtenerToken, obtenerUsuarioGuardado } from "@/lib/auth";
import Home from "../app/page";
import LoginPage from "../app/login/page";

const get = vi.mocked(api.get);
const post = vi.mocked(api.post);

const USUARIO = { id_usuario: "u-1", username: "diego", nombre: "Diego Vargas", rol: "OPERADOR", modulo: null, activo: true };
const PERFIL = { id_usuario: "u-1", username: "diego", rol: "OPERADOR", modulo: null, acciones: ["VER_CUENTA"] };

function errorHttp(status: number, data: unknown) {
  const err = new AxiosError("fail", "ERR_BAD_REQUEST");
  err.response = { status, data, statusText: "", headers: {}, config: {} as never };
  return err;
}

function conSesion() {
  localStorage.setItem("bna_access_token", "token-de-prueba");
  localStorage.setItem("bna_usuario", JSON.stringify(USUARIO));
}

beforeEach(() => {
  localStorage.clear();
  get.mockReset();
  post.mockReset();
  router.replace.mockReset();
});

describe("Exigencia de sesión en la banca personal", () => {
  it("SE-01 Sin token lleva al login y no consulta al CORE", async () => {
    render(<Home />);
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/login"));
    expect(get).not.toHaveBeenCalled();
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  });

  it("SE-02 Con una sesión vigente muestra la banca personal con el nombre del usuario", async () => {
    conSesion();
    get.mockResolvedValue({ data: PERFIL });
    render(<Home />);
    expect(await screen.findByRole("navigation", { name: "Navegación principal" })).toBeInTheDocument();
    expect(get).toHaveBeenCalledWith("/coredb/auth/me");
    expect(screen.getByText("Diego Vargas")).toBeInTheDocument();
    expect(router.replace).not.toHaveBeenCalled();
  });

  it("SE-03 Si el CORE ya no acepta el token, cierra la sesión y lleva al login", async () => {
    conSesion();
    get.mockRejectedValue(errorHttp(401, { error: { code: "TOKEN_EXPIRADO", message: "El token venció." } }));
    render(<Home />);
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/login"));
    expect(obtenerToken()).toBeNull();
  });

  it("SE-04 El perfil conserva el nombre que dio el login", async () => {
    conSesion();
    get.mockResolvedValue({ data: PERFIL });
    const perfil = await obtenerMiPerfil();
    expect(perfil.nombre).toBe("Diego Vargas");
    expect(perfil.acciones).toEqual(["VER_CUENTA"]);
    expect(obtenerUsuarioGuardado()?.acciones).toEqual(["VER_CUENTA"]);
  });
});

describe("Inicio de sesión", () => {
  const escribirCredenciales = async () => {
    await userEvent.type(screen.getByLabelText("Usuario"), " diego ");
    await userEvent.type(screen.getByLabelText("Contraseña"), "una-clave-larga");
  };

  it("LG-01 Un login correcto guarda la sesión y lleva a la banca personal", async () => {
    post.mockResolvedValue({ data: { access_token: "abc", token_type: "bearer", expires_in: 1800, usuario: USUARIO } });
    render(<LoginPage />);
    await escribirCredenciales();
    await userEvent.click(screen.getByRole("button", { name: /Ingresar a mi cuenta/ }));
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/"));
    expect(post).toHaveBeenCalledWith("/coredb/auth/login", { username: "diego", password: "una-clave-larga" });
    expect(obtenerToken()).toBe("abc");
    expect(obtenerUsuarioGuardado()?.nombre).toBe("Diego Vargas");
  });

  it("LG-02 Un login fallido muestra el mensaje del CORE y no guarda nada", async () => {
    post.mockRejectedValue(errorHttp(401, { error: { code: "CREDENCIALES_INVALIDAS", message: "Usuario o contraseña incorrectos." } }));
    render(<LoginPage />);
    await escribirCredenciales();
    await userEvent.click(screen.getByRole("button", { name: /Ingresar a mi cuenta/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Usuario o contraseña incorrectos.");
    expect(obtenerToken()).toBeNull();
    expect(router.replace).not.toHaveBeenCalled();
  });

  it("LG-03 'Registrar usuario' crea un usuario del sistema con la sesión actual", async () => {
    conSesion();
    post.mockResolvedValue({ data: { ...USUARIO, username: "nuevo" } });
    render(<LoginPage />);
    await userEvent.click(screen.getByRole("button", { name: "Registrar usuario" }));
    await userEvent.type(screen.getByLabelText("Nombre completo"), "Persona Nueva");
    await userEvent.type(screen.getByLabelText("Usuario"), "nuevo");
    await userEvent.selectOptions(screen.getByLabelText("Rol del usuario"), "OPERADOR");
    await userEvent.type(screen.getByLabelText("Contraseña"), "otra-clave-larga");
    await userEvent.click(screen.getByRole("button", { name: /Crear usuario/ }));
    expect(await screen.findByRole("status")).toHaveTextContent("Usuario nuevo creado correctamente");
    expect(post).toHaveBeenCalledWith("/coredb/usuarios", {
      username: "nuevo", nombre: "Persona Nueva", password: "otra-clave-larga", rol: "OPERADOR", id_empleado: null,
    });
  });
});

describe("Mensajes de error y cabeceras", () => {
  it("ER-01 Toma el mensaje de COREDB, el de CUENTAS o uno genérico", () => {
    expect(mensajeError(errorHttp(409, { error: { code: "X", message: "De COREDB." } }))).toBe("De COREDB.");
    expect(mensajeError(errorHttp(400, { success: false, message: "De CUENTAS." }))).toBe("De CUENTAS.");
    expect(mensajeError(errorHttp(503, { detail: "No se pudo contactar al servicio COREDB." }))).toBe("No se pudo contactar al servicio COREDB.");
    expect(mensajeError(errorHttp(422, { detail: [{ loc: ["body", "x"], type: "missing" }] }))).toMatch(/algún campo no es válido/);
    expect(mensajeError(errorHttp(403, {}))).toMatch(/no tiene permisos/);
    expect(mensajeError(new AxiosError("Network Error", "ERR_NETWORK"))).toBe("No se pudo conectar con el servidor.");
    expect(mensajeError("otra cosa")).toBe("Error inesperado");
  });

  it("ER-02 Cada operación lleva una llave nueva, el canal y la hora", () => {
    const una = cabecerasDeOperacion();
    const otra = cabecerasDeOperacion();
    expect(una["X-Idempotency-Key"]).toMatch(/^[0-9a-f-]{36}$/);
    expect(una["X-Idempotency-Key"]).not.toBe(otra["X-Idempotency-Key"]);
    expect(una["X-Channel-ID"]).toBe("VEN");
    expect(new Date(una["X-Request-Timestamp"]).getTime()).not.toBeNaN();
  });
});
