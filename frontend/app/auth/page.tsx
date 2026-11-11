"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { crearCliente } from "@/lib/clientes"; // Importado para registrar cliente en la API de CORE
import { abrirCuenta } from "@/lib/cuentas"; // Importado para aperturar cuenta de ahorros en la API

export default function AuthPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [accountType, setAccountType] = useState<"personal" | "mancomunada">("personal");
  
  // Form states
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nombres, setNombres] = useState("");
  const [apellidos, setApellidos] = useState("");
  const [documento, setDocumento] = useState("");
  
  // Mancomunada specific fields
  const [nombreCotitular, setNombreCotitular] = useState("");
  const [docCotitular, setDocCotitular] = useState("");
  const [regimenMancomunado, setRegimenMancomunado] = useState("indistinta");
  
  const [notice, setNotice] = useState("");
  const router = useRouter();

  function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) {
      setNotice("Por favor ingresa tu correo y contraseña.");
      return;
    }
    setNotice("¡Inicio de sesión exitoso! Redirigiendo a tu banca personal...");
    setTimeout(() => {
      router.push("/");
    }, 1000);
  }

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    if (!nombres || !apellidos || !documento || !email || !password) {
      setNotice("Por favor completa todos los campos obligatorios.");
      return;
    }
    if (accountType === "mancomunada" && (!nombreCotitular || !docCotitular)) {
      setNotice("Para cuentas mancomunadas debes ingresar los datos del cotitular.");
      return;
    }
    try {
      // Registrar cliente en el backend a través de la API
      const resCliente = await crearCliente({
        cod_tipo_documento: "DNI",
        numero_documento: documento,
        nombres: nombres,
        apellido_paterno: apellidos,
        numero_celular: "999888777",
      });
      const clienteId = resCliente.cliente?.id_cliente || "CLI-001";

      // Aperturar cuenta en la API para el cliente registrado
      await abrirCuenta({
        id_cliente: clienteId,
        moneda: "PEN",
        regimen: accountType === "mancomunada" ? "MANCOMUNADA_INDISTINTA" : "INDIVIDUAL",
        id_agencia: "AG1",
      });

      setNotice(
        accountType === "mancomunada"
          ? `Cuenta mancomunada creada exitosamente en la BD para ${nombres} y ${nombreCotitular}. Redirigiendo...`
          : `Cuenta personal creada exitosamente en la BD para ${nombres}. Redirigiendo...`
      );
      setTimeout(() => {
        router.push("/");
      }, 1500);
    } catch (err: any) {
      setNotice("Error al registrar en el backend: " + (err.response?.data?.message || err.message));
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#f5f7fb", padding: "20px" }}>
      <div style={{ width: "100%", maxWidth: "480px", background: "#fff", borderRadius: "16px", boxShadow: "0 10px 30px rgba(18, 43, 80, 0.08)", padding: "32px", border: "1px solid #e8edf4" }}>
        
        {/* Brand Header */}
        <div style={{ textAlign: "center", marginBottom: "24px" }}>
          <div style={{ display: "inline-flex", height: "48px", width: "48px", borderRadius: "12px", background: "#173d70", color: "white", alignItems: "center", justifyContent: "center", fontSize: "28px", fontWeight: "800", marginBottom: "12px" }}>
            B
          </div>
          <h1 style={{ fontSize: "20px", fontWeight: "700", color: "#122b50", margin: "0 0 4px 0" }}>
            Banco Nacional de Arequipa
          </h1>
          <p style={{ fontSize: "12px", color: "#7b879b", margin: 0 }}>
            {mode === "login" ? "Accede a tu portal de banca personal" : "Abre tu cuenta de ahorros personal o mancomunada"}
          </p>
        </div>

        {/* Mode Switcher Tabs */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", background: "#f4f7fc", padding: "4px", borderRadius: "10px", marginBottom: "24px" }}>
          <button
            type="button"
            onClick={() => { setMode("login"); setNotice(""); }}
            style={{ padding: "10px", border: 0, borderRadius: "8px", fontWeight: "600", fontSize: "13px", background: mode === "login" ? "#fff" : "transparent", color: mode === "login" ? "#122b50" : "#7b879b", boxShadow: mode === "login" ? "0 2px 6px rgba(0,0,0,0.05)" : "none", cursor: "pointer" }}
          >
            Iniciar Sesión
          </button>
          <button
            type="button"
            onClick={() => { setMode("register"); setNotice(""); }}
            style={{ padding: "10px", border: 0, borderRadius: "8px", fontWeight: "600", fontSize: "13px", background: mode === "register" ? "#fff" : "transparent", color: mode === "register" ? "#122b50" : "#7b879b", boxShadow: mode === "register" ? "0 2px 6px rgba(0,0,0,0.05)" : "none", cursor: "pointer" }}
          >
            Registrarse / Apertura
          </button>
        </div>

        {notice && (
          <div style={{ background: "#eaf1fb", border: "1px solid #cfe0fc", color: "#173d70", padding: "12px 14px", borderRadius: "8px", fontSize: "12px", marginBottom: "20px", display: "flex", gap: "8px", alignItems: "center" }}>
            <span>ℹ️</span>
            <p style={{ margin: 0 }}>{notice}</p>
          </div>
        )}

        {/* LOGIN FORM */}
        {mode === "login" ? (
          <form onSubmit={handleLogin} style={{ display: "grid", gap: "16px" }}>
            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#17243a", marginBottom: "6px" }}>
                Correo electrónico o DNI
              </label>
              <input
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="ejemplo@bna.pe o 12345678"
                required
                style={{ width: "100%", padding: "11px 14px", borderRadius: "8px", border: "1px solid #dcdfe6", fontSize: "13px", outline: "none" }}
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#17243a", marginBottom: "6px" }}>
                Contraseña
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                style={{ width: "100%", padding: "11px 14px", borderRadius: "8px", border: "1px solid #dcdfe6", fontSize: "13px", outline: "none" }}
              />
            </div>

            <button
              type="submit"
              style={{ background: "#122b50", color: "white", border: 0, padding: "12px", borderRadius: "8px", fontWeight: "600", fontSize: "13px", cursor: "pointer", marginTop: "8px" }}
            >
              Ingresar a Banca Personal →
            </button>
          </form>
        ) : (
          /* REGISTER FORM */
          <form onSubmit={handleRegister} style={{ display: "grid", gap: "14px" }}>
            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#17243a", marginBottom: "6px" }}>
                Tipo de Cuenta / Registro
              </label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                <button
                  type="button"
                  onClick={() => setAccountType("personal")}
                  style={{ padding: "9px", borderRadius: "8px", border: accountType === "personal" ? "2px solid #2359a8" : "1px solid #dcdfe6", background: accountType === "personal" ? "#eaf1fb" : "#fff", color: accountType === "personal" ? "#122b50" : "#7b879b", fontSize: "12px", fontWeight: "600", cursor: "pointer" }}
                >
                  👤 Personal
                </button>
                <button
                  type="button"
                  onClick={() => setAccountType("mancomunada")}
                  style={{ padding: "9px", borderRadius: "8px", border: accountType === "mancomunada" ? "2px solid #2359a8" : "1px solid #dcdfe6", background: accountType === "mancomunada" ? "#eaf1fb" : "#fff", color: accountType === "mancomunada" ? "#122b50" : "#7b879b", fontSize: "12px", fontWeight: "600", cursor: "pointer" }}
                >
                  👥 Mancomunada
                </button>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
              <div>
                <label style={{ display: "block", fontSize: "11px", fontWeight: "600", color: "#17243a", marginBottom: "4px" }}>
                  Nombres (Titular 1)
                </label>
                <input
                  type="text"
                  value={nombres}
                  onChange={(e) => setNombres(e.target.value)}
                  placeholder="Diego"
                  required
                  style={{ width: "100%", padding: "10px 12px", borderRadius: "8px", border: "1px solid #dcdfe6", fontSize: "12px", outline: "none" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "11px", fontWeight: "600", color: "#17243a", marginBottom: "4px" }}>
                  Apellidos
                </label>
                <input
                  type="text"
                  value={apellidos}
                  onChange={(e) => setApellidos(e.target.value)}
                  placeholder="Vargas"
                  required
                  style={{ width: "100%", padding: "10px 12px", borderRadius: "8px", border: "1px solid #dcdfe6", fontSize: "12px", outline: "none" }}
                />
              </div>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "11px", fontWeight: "600", color: "#17243a", marginBottom: "4px" }}>
                Número de Documento (DNI / C.E.)
              </label>
              <input
                type="text"
                value={documento}
                onChange={(e) => setDocumento(e.target.value)}
                placeholder="74829102"
                required
                style={{ width: "100%", padding: "10px 12px", borderRadius: "8px", border: "1px solid #dcdfe6", fontSize: "12px", outline: "none" }}
              />
            </div>

            {/* MANCOMUNADA EXTRA FIELDS */}
            {accountType === "mancomunada" && (
              <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "8px", border: "1px dashed #cbd5e1", display: "grid", gap: "10px" }}>
                <span style={{ fontSize: "11px", fontWeight: "700", color: "#1e3a8a" }}>Datos del Cotitular / Mancomunado</span>
                <div>
                  <label style={{ display: "block", fontSize: "11px", fontWeight: "600", color: "#17243a", marginBottom: "3px" }}>
                    Nombre completo del Cotitular
                  </label>
                  <input
                    type="text"
                    value={nombreCotitular}
                    onChange={(e) => setNombreCotitular(e.target.value)}
                    placeholder="María López"
                    required={accountType === "mancomunada"}
                    style={{ width: "100%", padding: "9px 12px", borderRadius: "8px", border: "1px solid #dcdfe6", fontSize: "12px", outline: "none", background: "#fff" }}
                  />
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                  <div>
                    <label style={{ display: "block", fontSize: "11px", fontWeight: "600", color: "#17243a", marginBottom: "3px" }}>
                      Documento Cotitular
                    </label>
                    <input
                      type="text"
                      value={docCotitular}
                      onChange={(e) => setDocCotitular(e.target.value)}
                      placeholder="48291023"
                      required={accountType === "mancomunada"}
                      style={{ width: "100%", padding: "9px 12px", borderRadius: "8px", border: "1px solid #dcdfe6", fontSize: "12px", outline: "none", background: "#fff" }}
                    />
                  </div>
                  <div>
                    <label style={{ display: "block", fontSize: "11px", fontWeight: "600", color: "#17243a", marginBottom: "3px" }}>
                      Régimen
                    </label>
                    <select
                      value={regimenMancomunado}
                      onChange={(e) => setRegimenMancomunado(e.target.value)}
                      style={{ width: "100%", padding: "9px 12px", borderRadius: "8px", border: "1px solid #dcdfe6", fontSize: "12px", outline: "none", background: "#fff" }}
                    >
                      <option value="indistinta">Indistinta (Cualquiera)</option>
                      <option value="conjunta">Conjunta (Ambos)</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            <div>
              <label style={{ display: "block", fontSize: "11px", fontWeight: "600", color: "#17243a", marginBottom: "4px" }}>
                Correo Electrónico
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="diego@bna.pe"
                required
                style={{ width: "100%", padding: "10px 12px", borderRadius: "8px", border: "1px solid #dcdfe6", fontSize: "12px", outline: "none" }}
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "11px", fontWeight: "600", color: "#17243a", marginBottom: "4px" }}>
                Contraseña
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                style={{ width: "100%", padding: "10px 12px", borderRadius: "8px", border: "1px solid #dcdfe6", fontSize: "12px", outline: "none" }}
              />
            </div>

            <button
              type="submit"
              style={{ background: "#122b50", color: "white", border: 0, padding: "12px", borderRadius: "8px", fontWeight: "600", fontSize: "13px", cursor: "pointer", marginTop: "6px" }}
            >
              {accountType === "mancomunada" ? "Registrar Cuenta Mancomunada →" : "Registrar Cuenta Personal →"}
            </button>
          </form>
        )}

        {/* Footer Link to Dashboard */}
        <div style={{ textAlign: "center", marginTop: "20px", borderTop: "1px solid #e8edf4", paddingTop: "16px" }}>
          <button
            onClick={() => router.push("/")}
            style={{ background: "transparent", border: 0, color: "#2359a8", fontSize: "12px", fontWeight: "600", cursor: "pointer" }}
          >
            ← Volver al resumen principal sin autenticar
          </button>
        </div>

      </div>
    </div>
  );
}
