"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, mensajeError } from "@/lib/api";
import { cerrarSesion, iniciarSesion, obtenerToken, registrarUsuario } from "@/lib/auth";

type Modo = "login" | "registro";

export default function LoginPage() {
  const router = useRouter();
  const [modo, setModo] = useState<Modo>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [nombre, setNombre] = useState("");
  const [rol, setRol] = useState("ASESOR");
  const [idEmpleado, setIdEmpleado] = useState("");
  const [mensaje, setMensaje] = useState("");
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);
  const [yaReviso, setYaReviso] = useState(false);

  useEffect(() => {
    const token = obtenerToken();
    if (token) {
      api.get("/core/auth/me")
        .then(() => router.replace("/"))
        .catch(() => cerrarSesion())
        .finally(() => setYaReviso(true));
    } else {
      setYaReviso(true);
    }
  }, [router]);

  async function enviarLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(""); setMensaje(""); setCargando(true);
    try {
      await iniciarSesion(username.trim(), password);
      router.replace("/");
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setCargando(false);
    }
  }

  async function enviarRegistro(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(""); setMensaje(""); setCargando(true);
    try {
      const creado = await registrarUsuario({
        username: username.trim(),
        nombre: nombre.trim(),
        password,
        rol,
        id_empleado: idEmpleado.trim() || null,
      });
      setMensaje(`Usuario ${creado.username} creado correctamente. Ya puede iniciar sesión.`);
      setModo("login");
      setPassword("");
      setNombre("");
      setIdEmpleado("");
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setCargando(false);
    }
  }

  if (!yaReviso) return <main className="auth-page"><div className="auth-loading">Verificando sesión...</div></main>;

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="auth-brand">
          <div className="auth-brand-mark">B</div>
          <div><strong>BAN</strong><span>Banco Nacional de Arequipa</span></div>
        </div>

        <div className="auth-heading">
          <span className="auth-eyebrow">BANCA DIGITAL</span>
          <h1>{modo === "login" ? "Bienvenido de nuevo" : "Registrar usuario"}</h1>
          <p>{modo === "login"
            ? "Ingresa tus credenciales para acceder a tu banca personal."
            : "El registro de usuarios del sistema requiere una sesión con permiso CREAR_USUARIO."}</p>
        </div>

        <div className="auth-tabs">
          <button type="button" className={modo === "login" ? "selected" : ""} onClick={() => { setModo("login"); setError(""); setMensaje(""); }}>Iniciar sesión</button>
          <button type="button" className={modo === "registro" ? "selected" : ""} onClick={() => { setModo("registro"); setError(""); setMensaje(""); }}>Registrar usuario</button>
        </div>

        {error && <div className="auth-alert auth-error" role="alert">{error}</div>}
        {mensaje && <div className="auth-alert auth-success" role="status">{mensaje}</div>}

        <form className="auth-form" onSubmit={modo === "login" ? enviarLogin : enviarRegistro}>
          {modo === "registro" && (
            <>
              <label htmlFor="nombre">Nombre completo</label>
              <input id="nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Nombre y apellidos" required maxLength={100} />
            </>
          )}

          <label htmlFor="username">Usuario</label>
          <input id="username" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Tu nombre de usuario" required minLength={modo === "registro" ? 3 : 1} maxLength={40} autoComplete="username" />

          {modo === "registro" && (
            <>
              <label htmlFor="rol">Rol del usuario</label>
              <select id="rol" value={rol} onChange={(e) => setRol(e.target.value)}>
                <option value="ASESOR">Asesor</option>
                <option value="ANALISTA">Analista</option>
                <option value="OPERADOR">Operador</option>
                <option value="AUDITOR">Auditor</option>
                <option value="ADMINISTRADOR">Administrador</option>
              </select>
              <label htmlFor="idEmpleado">ID de empleado (opcional)</label>
              <input id="idEmpleado" value={idEmpleado} onChange={(e) => setIdEmpleado(e.target.value)} placeholder="UUID del empleado, si corresponde" />
            </>
          )}

          <label htmlFor="password">Contraseña</label>
          <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder={modo === "registro" ? "Mínimo 8 caracteres" : "Ingresa tu contraseña"} required minLength={modo === "registro" ? 8 : 1} maxLength={128} autoComplete={modo === "login" ? "current-password" : "new-password"} />

          <button className="auth-submit" type="submit" disabled={cargando}>
            {cargando ? "Procesando..." : modo === "login" ? "Ingresar a mi cuenta" : "Crear usuario"}
            <span>→</span>
          </button>
        </form>

        {modo === "registro" && (
          <p className="auth-note">Este formulario crea usuarios internos del sistema mediante <code>POST /core/usuarios</code>. No es un registro público de clientes. Si recibes un error 403, inicia sesión con un usuario administrador autorizado.</p>
        )}

        <div className="auth-bottom">
          <Link href="/">Volver a la banca personal</Link>
          <span>Conexión protegida · BNA</span>
        </div>
      </section>
      <aside className="auth-aside">
        <div className="auth-aside-content">
          <span className="auth-aside-kicker">BANCO NACIONAL DE AREQUIPA</span>
          <h2>Tu banca, más simple y segura.</h2>
          <p>Accede a tus productos y gestiona tus operaciones desde un solo lugar.</p>
          <div className="auth-feature"><span>✓</span> Acceso mediante credenciales verificadas</div>
          <div className="auth-feature"><span>✓</span> Sesión protegida con token JWT</div>
          <div className="auth-feature"><span>✓</span> Permisos según el rol del usuario</div>
        </div>
      </aside>
    </main>
  );
}
