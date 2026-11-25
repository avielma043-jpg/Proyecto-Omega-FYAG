import { apiClient } from "./apiClient";

// Consultar las obras registradas en Django.
export async function getObras() {
  const response = await apiClient.get("obras/obras/");
  return response.data;
}
