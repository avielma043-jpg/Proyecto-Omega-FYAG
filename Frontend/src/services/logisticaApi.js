
import { apiClient } from "./apiClient";

// Obtener los artículos desde PostgreSQL
export async function getArticulos() {
  const response = await apiClient.get(
    "logistica/articulos/"
  );

  return response.data;
}

export async function createArticulo(payload) {
  const response = await apiClient.post(
    "logistica/articulos/",
    payload
  );

  return response.data;
}

export async function createMovimiento(payload) {
  const response = await apiClient.post(
    "logistica/cardex/",
    payload
  );

  return response.data;
}

export async function getMovimientosCardex() {
  const response = await apiClient.get("logistica/cardex/");
  return response.data;
}
