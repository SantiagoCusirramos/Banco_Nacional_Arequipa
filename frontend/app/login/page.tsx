"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { mensajeError } from "@/lib/api";
import { iniciarSesion } from "@/lib/auth";

// Solo el ingreso. Los usuarios los crea un administrador en la pantalla «Usuarios» del portal.

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);

  async function enviarLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(""); setCargando(true);
    try {
      const sesion = await iniciarSesion(username.trim(), password);
      // Con la contraseña inicial o renovada, primero se cambia.
      router.replace(sesion.usuario.debe_cambiar_clave ? "/cambiar-clave" : "/");
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setCargando(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="auth-brand">
          <div className="auth-brand-mark">B</div>
          <div><strong>BAN</strong><span>Banco Nacional de Arequipa</span></div>
        </div>

        <div className="auth-heading">
          <span className="auth-eyebrow">BANCA DIGITAL</span>
          <h1>Bienvenido de nuevo</h1>
          <p>Ingresa con tu usuario del banco. Si aún no tienes uno, pídelo a un administrador.</p>
        </div>

        {error && <div className="auth-alert auth-error" role="alert">{error}</div>}

        <form className="auth-form" onSubmit={enviarLogin}>
          <label htmlFor="username">Usuario</label>
          <input id="username" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Tu nombre de usuario" required maxLength={40} autoComplete="username" />

          <label htmlFor="password">Contraseña</label>
          <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Ingresa tu contraseña" required maxLength={128} autoComplete="current-password" />

          <button className="auth-submit" type="submit" disabled={cargando}>
            {cargando ? "Procesando..." : "Ingresar a mi cuenta"}
            <span>→</span>
          </button>
        </form>

        <div className="auth-bottom">
          <span>Conexión protegida · BNA</span>
        </div>
      </section>
      <aside className="auth-aside">
        <div className="auth-aside-content">
          <span className="auth-aside-kicker">BANCO NACIONAL DE AREQUIPA</span>
          <h2>Tu banca, más simple y segura.</h2>
          <p>Accede a tus productos y gestiona tus operaciones desde un solo lugar.</p>
        </div>
      </aside>
    </main>
  );
}
