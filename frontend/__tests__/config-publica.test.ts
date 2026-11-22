// @vitest-environment node
import { afterEach, describe, expect, it, vi } from "vitest";
import { GET } from "../app/api/config-publica/route";

const VARIABLES = {
  BNA_URL_BILLETERA: "http://localhost:8020",
  BNA_URL_CAJERO: "https://cajero.bna.example/terminal",
  BNA_URL_APK: "https://github.com/SantiagoCusirramos/Banco_Nacional_Arequipa/releases",
} as const;

function fijar(valores: Partial<Record<keyof typeof VARIABLES, string>>) {
  for (const nombre of Object.keys(VARIABLES) as (keyof typeof VARIABLES)[]) {
    vi.stubEnv(nombre, valores[nombre] ?? "");
  }
}

const sinSesion = () => new Request("http://localhost:3000/api/config-publica");

afterEach(() => vi.unstubAllEnvs());

describe("GET /api/config-publica", () => {
  it("devuelve las tres URLs sin exigir sesión y sin permitir caché", async () => {
    fijar(VARIABLES);
    const respuesta = await GET(sinSesion());
    expect(respuesta.status).toBe(200);
    expect(respuesta.headers.get("Cache-Control")).toBe("no-store");
    await expect(respuesta.json()).resolves.toEqual({
      urlBilletera: VARIABLES.BNA_URL_BILLETERA,
      urlCajero: VARIABLES.BNA_URL_CAJERO,
      urlApk: VARIABLES.BNA_URL_APK,
    });
  });

  it("devuelve null para las variables vacías o no definidas", async () => {
    fijar({ BNA_URL_BILLETERA: VARIABLES.BNA_URL_BILLETERA });
    delete process.env.BNA_URL_APK;
    const cuerpo = await (await GET(sinSesion())).json();
    expect(cuerpo).toEqual({ urlBilletera: VARIABLES.BNA_URL_BILLETERA, urlCajero: null, urlApk: null });
  });

  it.each([
    "javascript:alert(1)",
    "ftp://bna.example/app",
    "file:///etc/passwd",
    "http://usuario:clave@bna.example",
    "https://usuario@bna.example",
    "bna.example/app",
    "",
  ])("descarta el valor no público %s", async (valor) => {
    fijar({ ...VARIABLES, BNA_URL_BILLETERA: valor });
    const cuerpo = await (await GET(sinSesion())).json();
    expect(cuerpo.urlBilletera).toBeNull();
    expect(cuerpo.urlCajero).toBe(VARIABLES.BNA_URL_CAJERO);
  });

  it("descarta también los valores no públicos del cajero y del APK", async () => {
    fijar({ ...VARIABLES, BNA_URL_CAJERO: "ftp://bna.example", BNA_URL_APK: "http://user:pass@bna.example/apk" });
    const cuerpo = await (await GET(sinSesion())).json();
    expect(cuerpo.urlCajero).toBeNull();
    expect(cuerpo.urlApk).toBeNull();
  });

  it("lee los valores en cada petición y no publica otras variables", async () => {
    fijar(VARIABLES);
    vi.stubEnv("BUS_TOKEN", "secreto-del-bus");
    vi.stubEnv("COREDB_URL", "http://bus:8018/bus/coredb");
    const primera = await (await GET(sinSesion())).json();
    vi.stubEnv("BNA_URL_BILLETERA", "https://otro.bna.example");
    const segunda = await (await GET(sinSesion())).json();

    expect(primera.urlBilletera).toBe(VARIABLES.BNA_URL_BILLETERA);
    expect(segunda.urlBilletera).toBe("https://otro.bna.example");
    expect(Object.keys(segunda).sort()).toEqual(["urlApk", "urlBilletera", "urlCajero"]);
    expect(JSON.stringify(segunda)).not.toContain("secreto-del-bus");
  });
});
