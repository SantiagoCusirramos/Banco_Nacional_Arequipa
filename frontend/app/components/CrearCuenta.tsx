"use client";

import { useEffect, useState } from "react";
import { Controller, useFieldArray, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { buscarClientesPorDocumento, nombreCompleto, type Cliente } from "@/lib/clientes";
import { listarAgencias, listarProductosAhorro, type Agencia, type ProductoAhorro } from "@/lib/catalogos";
import { crearCuenta, mensajeDeError, REGIMENES, ROLES_TITULAR, type Cuenta } from "@/lib/cuentas";
import { CuentaResumen } from "./CuentaResumen";

const requerido = (mensaje: string) => z.string().trim().min(1, mensaje);

const esquema = z
  .object({
    id_cliente: requerido("Selecciona el cliente titular."),
    id_producto_ahorro: requerido("Selecciona un producto de ahorro."),
    id_agencia: requerido("Selecciona una agencia."),
    regimen: z.enum(REGIMENES),
    rol_principal: z.enum(ROLES_TITULAR),
    titulares: z.array(
      z.object({ id_cliente: requerido("Selecciona el cliente titular."), rol_titular: z.enum(ROLES_TITULAR) }),
    ),
  })
  .superRefine((valores, ctx) => {
    const vistos = new Set([valores.id_cliente]);
    valores.titulares.forEach((titular, i) => {
      if (vistos.has(titular.id_cliente)) {
        ctx.addIssue({ code: "custom", path: ["titulares", i, "id_cliente"], message: "Este cliente ya figura como titular." });
      }
      vistos.add(titular.id_cliente);
    });
    const mancomunada = valores.rol_principal === "MANCOMUNADO" || valores.titulares.some((t) => t.rol_titular === "MANCOMUNADO");
    if (mancomunada && valores.titulares.length < 1) {
      ctx.addIssue({ code: "custom", path: ["titulares"], message: "Una cuenta mancomunada requiere al menos dos titulares (RGN-16)." });
    }
  });

type Valores = z.infer<typeof esquema>;

const VALORES_INICIALES: Valores = {
  id_cliente: "",
  id_producto_ahorro: "",
  id_agencia: "",
  regimen: "LIBRE",
  rol_principal: "TITULAR",
  titulares: [],
};

type Props = {
  onNotice: (mensaje: string) => void;
  onModificar: (cuenta: Cuenta) => void;
};

type ClienteSelectorProps = {
  id: string;
  label: string;
  value: string;
  onChange: (idCliente: string) => void;
  error?: string;
};

function ClienteSelector({ id, label, value, onChange, error }: ClienteSelectorProps) {
  const [documento, setDocumento] = useState("");
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [buscando, setBuscando] = useState(false);
  const [errorBusqueda, setErrorBusqueda] = useState("");

  async function buscar() {
    const consulta = documento.trim();
    if (!consulta) {
      setErrorBusqueda("Ingresa un número de documento para buscar.");
      setClientes([]);
      return;
    }

    setBuscando(true);
    setErrorBusqueda("");
    try {
      const encontrados = await buscarClientesPorDocumento(consulta);
      setClientes(encontrados);
      if (encontrados.length === 0) {
        setErrorBusqueda("No encontramos clientes con ese documento.");
        onChange("");
      } else if (!encontrados.some((cliente) => cliente.id_cliente === value)) {
        onChange("");
      }
    } catch (err) {
      setClientes([]);
      setErrorBusqueda(mensajeDeError(err));
      onChange("");
    } finally {
      setBuscando(false);
    }
  }

  return (
    <div className="fx-field">
      <label htmlFor={id + "-documento"}>{label}</label>
      <div className="fx-search">
        <div className="fx-field fx-grow">
          <input
            id={id + "-documento"}
            autoComplete="off"
            inputMode="numeric"
            placeholder="DNI o número de documento"
            value={documento}
            onChange={(event) => {
              setDocumento(event.target.value);
              setClientes([]);
              setErrorBusqueda("");
              onChange("");
            }}
          />
        </div>
        <button className="outline-button" type="button" aria-label={"Buscar " + id} onClick={buscar} disabled={buscando}>
          {buscando ? "Buscando..." : "Buscar"}
        </button>
      </div>
      {clientes.length > 0 && (
        <div className="fx-field">
          <label htmlFor={id}>{label.replace("Buscar ", "") + " seleccionado"}</label>
          <select id={id} value={value} onChange={(event) => onChange(event.target.value)} aria-invalid={!!error}>
            <option value="">Selecciona un cliente...</option>
            {clientes.map((cliente) => (
              <option key={cliente.id_cliente} value={cliente.id_cliente}>
                {nombreCompleto(cliente)} · {cliente.cod_tipo_documento} {cliente.numero_documento}
              </option>
            ))}
          </select>
        </div>
      )}
      {value && <span className="fx-hint">Cliente seleccionado: {value}</span>}
      {errorBusqueda && <span className="fx-error" role="status">{errorBusqueda}</span>}
      {error && <span className="fx-error">{error}</span>}
    </div>
  );
}

export function CrearCuenta({ onNotice, onModificar }: Props) {
  const [creada, setCreada] = useState<Cuenta | null>(null);
  const [errorServidor, setErrorServidor] = useState("");
  const [errorCatalogos, setErrorCatalogos] = useState("");
  const [agencias, setAgencias] = useState<Agencia[]>([]);
  const [productos, setProductos] = useState<ProductoAhorro[]>([]);
  const [cargandoCatalogos, setCargandoCatalogos] = useState(true);
  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<Valores>({ resolver: zodResolver(esquema), defaultValues: VALORES_INICIALES });
  const { fields, append, remove } = useFieldArray({ control, name: "titulares" });

  useEffect(() => {
    let activo = true;

    async function cargarCatalogos() {
      setCargandoCatalogos(true);
      setErrorCatalogos("");
      try {
        const [agenciasDisponibles, productosDisponibles] = await Promise.all([
          listarAgencias(),
          listarProductosAhorro(),
        ]);
        if (!activo) return;
        setAgencias(agenciasDisponibles);
        setProductos(productosDisponibles);
        if (agenciasDisponibles.length === 0 || productosDisponibles.length === 0) {
          setErrorCatalogos("No hay agencias o productos de ahorro activos para seleccionar.");
        }
      } catch (err) {
        if (activo) setErrorCatalogos(mensajeDeError(err));
      } finally {
        if (activo) setCargandoCatalogos(false);
      }
    }

    void cargarCatalogos();
    return () => {
      activo = false;
    };
  }, []);

  async function enviar(valores: Valores) {
    setErrorServidor("");
    const vinculos = [{ id_cliente: valores.id_cliente, rol_titular: valores.rol_principal }, ...valores.titulares];
    const enviarTitulares = valores.titulares.length > 0 || valores.rol_principal !== "TITULAR";
    try {
      const cuenta = await crearCuenta({
        id_cliente: valores.id_cliente,
        id_producto_ahorro: valores.id_producto_ahorro,
        id_agencia: valores.id_agencia,
        regimen: valores.regimen,
        titulares: enviarTitulares ? vinculos : undefined,
      });
      setCreada(cuenta);
      onNotice("Cuenta " + cuenta.num_cuenta + " creada correctamente.");
    } catch (err) {
      setErrorServidor(mensajeDeError(err));
    }
  }

  if (creada) {
    return (
      <div className="fx-stack">
        <CuentaResumen cuenta={creada} titulo="Cuenta creada" />
        <div className="fx-actions">
          <button className="outline-button" onClick={() => onModificar(creada)}>Modificar estado de esta cuenta</button>
          <button className="primary-button" onClick={() => { setCreada(null); reset(VALORES_INICIALES); onNotice(""); }}>Abrir otra cuenta</button>
        </div>
      </div>
    );
  }

  const errorTitulares = errors.titulares?.root?.message ?? errors.titulares?.message;

  return (
    <div className="form-card">
      <div className="form-intro">
        <span className="form-icon">+</span>
        <div>
          <h2>Abrir cuenta de ahorros</h2>
          <p>Busca al cliente y selecciona el producto y la agencia para abrir la cuenta.</p>
        </div>
      </div>

      {cargandoCatalogos && <p className="fx-hint" role="status">Cargando agencias y productos...</p>}
      {errorCatalogos && <div className="fx-alert" role="alert">{errorCatalogos}</div>}

      <form className="fx-form" onSubmit={handleSubmit(enviar)} noValidate>
        <Controller
          name="id_cliente"
          control={control}
          render={({ field }) => (
            <ClienteSelector
              id="id_cliente"
              label="Buscar cliente titular"
              value={field.value}
              onChange={field.onChange}
              error={errors.id_cliente?.message}
            />
          )}
        />

        <div className="fx-grid">
          <div className="fx-field">
            <label htmlFor="id_producto_ahorro">Producto de ahorro</label>
            <select id="id_producto_ahorro" disabled={cargandoCatalogos || productos.length === 0} aria-invalid={!!errors.id_producto_ahorro} {...register("id_producto_ahorro")}>
              <option value="">Selecciona un producto...</option>
              {productos.map((producto) => (
                <option key={producto.id_producto_ahorro} value={producto.id_producto_ahorro}>
                  {producto.nombre} · {producto.moneda} · TEA {producto.tasa_tea}%
                </option>
              ))}
            </select>
            {errors.id_producto_ahorro && <span className="fx-error">{errors.id_producto_ahorro.message}</span>}
            <span className="fx-hint">La moneda de la cuenta la define el producto.</span>
          </div>
          <div className="fx-field">
            <label htmlFor="id_agencia">Agencia</label>
            <select id="id_agencia" disabled={cargandoCatalogos || agencias.length === 0} aria-invalid={!!errors.id_agencia} {...register("id_agencia")}>
              <option value="">Selecciona una agencia...</option>
              {agencias.map((agencia) => (
                <option key={agencia.id_agencia} value={agencia.id_agencia}>
                  {agencia.nombre} · {agencia.direccion}
                </option>
              ))}
            </select>
            {errors.id_agencia && <span className="fx-error">{errors.id_agencia.message}</span>}
          </div>
        </div>

        <div className="fx-field">
          <label htmlFor="regimen">Régimen</label>
          <select id="regimen" {...register("regimen")}>
            {REGIMENES.map((regimen) => <option key={regimen} value={regimen}>{regimen}</option>)}
          </select>
        </div>

        <div className="fx-section">
          <div className="fx-section-head">
            <div>
              <strong>Titulares</strong>
              <p className="fx-hint">Opcional: agrega titulares adicionales o cambia el rol del cliente principal.</p>
            </div>
            <button type="button" className="text-button" onClick={() => append({ id_cliente: "", rol_titular: "TITULAR" })}>+ Agregar titular</button>
          </div>

          <div className="fx-titular-row">
            <div className="fx-field">
              <label htmlFor="rol_principal">Rol del cliente principal</label>
              <select id="rol_principal" {...register("rol_principal")}>
                {ROLES_TITULAR.map((rol) => <option key={rol} value={rol}>{rol}</option>)}
              </select>
            </div>
          </div>

          {fields.map((campo, i) => (
            <div className="fx-titular-row" key={campo.id}>
              <Controller
                name={`titulares.${i}.id_cliente`}
                control={control}
                render={({ field }) => (
                  <ClienteSelector
                    id={"titular_" + (i + 2)}
                    label={"Buscar titular " + (i + 2)}
                    value={field.value}
                    onChange={field.onChange}
                    error={errors.titulares?.[i]?.id_cliente?.message}
                  />
                )}
              />
              <div className="fx-field">
                <label htmlFor={"rol_titular_" + i}>{"Rol del titular " + (i + 2)}</label>
                <select id={"rol_titular_" + i} {...register(`titulares.${i}.rol_titular`)}>
                  {ROLES_TITULAR.map((rol) => <option key={rol} value={rol}>{rol}</option>)}
                </select>
              </div>
              <button type="button" className="fx-remove" aria-label={"Quitar titular " + (i + 2)} onClick={() => remove(i)}>×</button>
            </div>
          ))}
          {errorTitulares && <span className="fx-error" role="alert">{errorTitulares}</span>}
        </div>

        {errorServidor && <div className="fx-alert" role="alert">{errorServidor}</div>}

        <button className="primary-button" type="submit" disabled={isSubmitting || cargandoCatalogos || !!errorCatalogos}>
          {isSubmitting ? "Creando cuenta..." : "Crear cuenta"} <span>→</span>
        </button>
      </form>
    </div>
  );
}

