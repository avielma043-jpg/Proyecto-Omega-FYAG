
import React, {
  useCallback,
  useEffect,
  useState
} from "react";

import {
  getArticulos,
  createArticulo,
  createMovimiento,
  getMovimientosCardex
} from "./services/logisticaApi";

import { money } from "./data";

function getError(error) {
  const data = error.response?.data;

  if (typeof data === "string") return data;
  if (data?.detail) return String(data.detail);

  if (data && typeof data === "object") {
    return Object.entries(data)
      .map(([campo, mensaje]) =>
        `${campo}: ${Array.isArray(mensaje)
          ? mensaje.join(", ")
          : String(mensaje)}`
      )
      .join(" | ");
  }

  return error.message || "Error de conexión.";
}

export default function InventoryReal({ role }) {
  const [articulos, setArticulos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");
  const [savingMovement, setSavingMovement] = useState(false);
  const [success, setSuccess] = useState("");
  const [movimientos, setMovimientos] = useState([]);
  const [loadingCardex, setLoadingCardex] = useState(true);
  const [errorCardex, setErrorCardex] = useState("");


  const canCreate = [
    "Administrador General",
    "Administración / Finanzas",
    "Bodega / Logística"
  ].includes(role);
 
  const canRegisterMovement = [
  "Administrador General",
  "Bodega / Logística",
  "Bodega/Logística"
  ].includes(role);

  const cargarArticulos = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await getArticulos();

      const lista = Array.isArray(data)
        ? data
        : data.results || [];

      setArticulos(lista);
    } catch (err) {
      setError(getError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    cargarArticulos();
  }, [cargarArticulos]);


const cargarMovimientos = useCallback(async () => {
  setLoadingCardex(true);
  setErrorCardex("");

  try {
    const data = await getMovimientosCardex();

    const lista = Array.isArray(data)
      ? data
      : data.results || [];

    setMovimientos(lista);
  } catch (error) {
    setErrorCardex(getError(error));
  } finally {
    setLoadingCardex(false);
  }
}, []);

useEffect(() => {
  cargarMovimientos();
}, [cargarMovimientos]);

async function handleCreate(event) {
    event.preventDefault();
    if (saving || !canCreate) return;

    const form = new FormData(event.currentTarget);

    const payload = {
      codigo_interno: String(
        form.get("codigo_interno") || ""
      ).trim(),

      nombre: String(
        form.get("nombre") || ""
      ).trim(),

      categoria: String(
        form.get("categoria") || ""
      ).trim(),

      unidad_medida: String(
        form.get("unidad_medida") || ""
      ).trim(),

      stock_minimo: String(
        form.get("stock_minimo") || "0"
      ),

      precio_lista_vigente: Number(
        form.get("precio_lista_vigente") || 0
      )
    };

    setSaving(true);
    setError("");
    setSuccess("");

    try {
      await createArticulo(payload);

      setShowForm(false);

      await cargarArticulos();

      setSuccess(
        `Artículo "${payload.nombre}" registrado correctamente.`
      );
    } catch (err) {
      setError(getError(err));
    } finally {
      setSaving(false);
    }

async function handleIngreso(event) {
  event.preventDefault();

  if (savingMovement || !canRegisterMovement) return;

  const form = event.currentTarget;
  const values = new FormData(form);

  const articuloId = Number(values.get("id_articulo"));
  const cantidad = Number(values.get("cantidad"));
  const precio = Number(values.get("precio_unitario"));

  if (
    !Number.isInteger(articuloId) ||
    articuloId <= 0 ||
    !Number.isFinite(cantidad) ||
    cantidad <= 0 ||
    !Number.isInteger(precio) ||
    precio < 0
  ) {
    setError("Revisa el artículo, la cantidad y el precio.");
    return;
  }

  const payload = {
    id_articulo: articuloId,
    tipo_movimiento: "Ingreso",
    cantidad: cantidad.toFixed(2),
    precio_unitario: precio,
    client_uuid: crypto.randomUUID()
  };

  setSavingMovement(true);
  setError("");
  setSuccess("");

  try {
    await createMovimiento(payload);

    setSuccess("Ingreso registrado correctamente en Cardex.");

    form.reset();

    await cargarArticulos();
  } catch (err) {
    setError(getError(err));
  } finally {
    setSavingMovement(false);
  }}

  }

async function handleIngreso(event) {
  event.preventDefault();

  if (savingMovement || !canRegisterMovement) return;

  const form = event.currentTarget;
  const values = new FormData(form);

  const articuloId = Number(values.get("id_articulo"));
  const cantidad = Number(values.get("cantidad"));
  const precio = Number(values.get("precio_unitario"));

  if (
    !Number.isInteger(articuloId) ||
    articuloId <= 0 ||
    !Number.isFinite(cantidad) ||
    cantidad <= 0 ||
    !Number.isInteger(precio) ||
    precio < 0
  ) {
    setError("Revisa el artículo, la cantidad y el precio.");
    return;
  }

  const payload = {
    id_articulo: articuloId,
    tipo_movimiento: "Ingreso",
    cantidad: cantidad.toFixed(2),
    precio_unitario: precio,
    client_uuid: crypto.randomUUID()
  };

  setSavingMovement(true);
  setError("");
  setSuccess("");

  try {
    await createMovimiento(payload);
    await cargarArticulos();
    await cargarMovimientos();

    form.reset();
    setSuccess("Ingreso registrado correctamente en Cardex.");
  } catch (err) {
    setError(getError(err));
  } finally {
    setSavingMovement(false);
  }
}

  return (
    <div>
      <div className="page-heading">
        <div>
          <h2>Inventario y Cardex</h2>
          <p>
            Catálogo real almacenado en PostgreSQL.
          </p>
        </div>

        <div className="top-actions">
          <button
            className="btn ghost"
            onClick={cargarArticulos}
          >
            Actualizar
          </button>

          {canCreate && (
            <button
              className="btn primary"
              onClick={() => setShowForm(!showForm)}
            >
              {showForm ? "Cancelar" : "+ Nuevo artículo"}
            </button>
          )}
        </div>
      </div>

      {showForm && canCreate && (
        <div className="card">
          <h3>Registrar nuevo artículo</h3>

          <form onSubmit={handleCreate}>
            <div className="form-grid">

              <div className="form-field">
                <label>Código interno</label>
                <input
                  className="form-control"
                  name="codigo_interno"
                  placeholder="ART-TEST-001"
                  maxLength={50}
                  required
                />
              </div>

              <div className="form-field">
                <label>Nombre</label>
                <input
                  className="form-control"
                  name="nombre"
                  placeholder="Filtro secador"
                  maxLength={200}
                  required
                />
              </div>

              <div className="form-field">
                <label>Categoría</label>
                <input
                  className="form-control"
                  name="categoria"
                  placeholder="Refrigeración"
                  maxLength={100}
                  required
                />
              </div>

              <div className="form-field">
                <label>Unidad de medida</label>
                <input
                  className="form-control"
                  name="unidad_medida"
                  placeholder="Unidad"
                  maxLength={20}
                  required
                />
              </div>

              <div className="form-field">
                <label>Stock mínimo</label>
                <input
                  className="form-control"
                  name="stock_minimo"
                  type="number"
                  min="0"
                  step="0.01"
                  defaultValue="5"
                  required
                />
              </div>

              <div className="form-field">
                <label>Precio de lista (CLP)</label>
                <input
                  className="form-control"
                  name="precio_lista_vigente"
                  type="number"
                  min="0"
                  step="1"
                  defaultValue="15000"
                  required
                />
              </div>
            </div>

            <p className="helper">
              El artículo se creará con stock 0.
              Las existencias se registran en Cardex.
            </p>

            <button
              className="btn primary"
              type="submit"
              disabled={saving}
            >
              {saving
                ? "Guardando..."
                : "Guardar en PostgreSQL"}
            </button>
          </form>
        </div>
      )}

{canRegisterMovement && (
  <div className="card">
    <h3>Registrar ingreso de inventario</h3>

    <form onSubmit={handleIngreso}>
      <div className="form-grid">
        <div className="form-field">
          <label>Artículo</label>
          <select
            className="form-control"
            name="id_articulo"
            defaultValue=""
            required
          >
            <option value="" disabled>
              Selecciona un artículo
            </option>

            {articulos.map((articulo) => (
              <option
                key={articulo.id}
                value={articulo.id}
              >
                {articulo.codigo_interno} - {articulo.nombre}
              </option>
            ))}
          </select>
        </div>

        <div className="form-field">
          <label>Cantidad de ingreso</label>
          <input
            className="form-control"
            name="cantidad"
            type="number"
            min="0.01"
            step="0.01"
            defaultValue="10"
            required
          />
        </div>

        <div className="form-field">
          <label>Precio unitario (CLP)</label>
          <input
            className="form-control"
            name="precio_unitario"
            type="number"
            min="0"
            step="1"
            defaultValue="15000"
            required
          />
        </div>
      </div>

      <p className="helper">
        Este movimiento aumentará las existencias
        reales del artículo seleccionado.
      </p>

      <button
        className="btn primary"
        type="submit"
        disabled={savingMovement || articulos.length === 0}
      >
        {savingMovement
          ? "Registrando..."
          : "Registrar ingreso"}
      </button>
    </form>
  </div>
)}

<div className="card">
  <h3>Historial de movimientos de Cardex</h3>

  <button
    type="button"
    className="btn ghost"
    onClick={cargarMovimientos}
  >
    Actualizar historial
  </button>

  {loadingCardex && (
    <p>Cargando movimientos...</p>
  )}

  {errorCardex && (
    <p role="alert">Error: {errorCardex}</p>
  )}

  {!loadingCardex && !errorCardex && (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th>Fecha</th>
            <th>Artículo</th>
            <th>Movimiento</th>
            <th>Cantidad</th>
            <th>Usuario</th>
            <th>Precio unitario</th>
          </tr>
        </thead>

        <tbody>
          {movimientos.map((mov) => (
            <tr key={mov.id}>
              <td>
                {mov.fecha_movimiento
                  ? new Date(
                      mov.fecha_movimiento
                    ).toLocaleString("es-CL")
                  : "—"}
              </td>

              <td>
                {mov.articulo_nombre ||
                  `Artículo ${mov.id_articulo}`}
              </td>

              <td>{mov.tipo_movimiento}</td>

              <td>{mov.cantidad}</td>

              <td>
                {mov.usuario_username || "—"}
              </td>

              <td>
                {money(mov.precio_unitario)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {movimientos.length === 0 && (
        <p>No existen movimientos registrados.</p>
      )}
    </div>
  )}
</div>

      {error && (
        <div className="test-banner" role="alert">
          Error: {error}
        </div>
      )}

      {success && (
        <div className="card" role="status">
          {success}
        </div>
      )}

      <div className="card">
        <h3>
          Artículos registrados: {articulos.length}
        </h3>

        {loading ? (
          <p>Cargando artículos...</p>
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Código</th>
                  <th>Artículo</th>
                  <th>Categoría</th>
                  <th>Stock</th>
                  <th>Stock mínimo</th>
                  <th>Precio</th>
                </tr>
              </thead>

              <tbody>
                {articulos.map((articulo) => (
                  <tr key={articulo.id}>
                    <td>{articulo.codigo_interno}</td>
                    <td>{articulo.nombre}</td>
                    <td>{articulo.categoria}</td>
                    <td>{articulo.stock_disponible}</td>
                    <td>{articulo.stock_minimo}</td>
                    <td>
                      {money(
                        articulo.precio_lista_vigente
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {articulos.length === 0 && !error && (
              <p>No hay artículos registrados.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
