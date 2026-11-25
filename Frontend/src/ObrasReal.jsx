
import React, {
  useCallback,
  useEffect,
  useState
} from "react";

import { getObras } from "./services/obrasApi";

export default function ObrasReal() {
  const [obras, setObras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const cargarObras = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await getObras();

      const lista = Array.isArray(data)
        ? data
        : Array.isArray(data?.results)
          ? data.results
          : [];

      setObras(lista);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        err.message ||
        "No fue posible consultar las obras."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    cargarObras();
  }, [cargarObras]);

  return (
    <div>
      <div className="page-heading">
        <div>
          <h2>Obras y Técnicos</h2>
          <p>
            Obras registradas en PostgreSQL.
          </p>
        </div>

        <button
          type="button"
          className="btn ghost"
          onClick={cargarObras}
          disabled={loading}
        >
          Actualizar
        </button>
      </div>

      <div className="card">
        <h3>Obras registradas: {obras.length}</h3>

        {loading && <p>Cargando obras...</p>}

        {error && (
          <p role="alert">Error: {error}</p>
        )}

        {!loading && !error && (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Tipo de servicio</th>
                  <th>Cliente</th>
                  <th>Técnico</th>
                  <th>Estado</th>
                  <th>Fecha</th>
                </tr>
              </thead>

              <tbody>
                {obras.map((obra) => (
                  <tr key={obra.id}>
                    <td>{obra.id}</td>
                    <td>{obra.tipo_servicio}</td>
                    <td>{obra.id_cliente}</td>
                    <td>
                      {obra.id_tecnico ?? "Sin asignar"}
                    </td>
                    <td>{obra.estado}</td>
                    <td>{obra.fecha_creacion}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {obras.length === 0 && (
              <p>
                No existen obras registradas todavía.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
