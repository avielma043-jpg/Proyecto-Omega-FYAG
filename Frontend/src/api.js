
import { apiClient } from "./services/apiClient";
export const errorMessage = (data, status) => {
  if (data?.detail) return String(data.detail);
  if (data && typeof data === 'object') {
    return Object.entries(data)
      .map(([name, value]) => `${name}: ${Array.isArray(value) ? value.join(', ') : String(value)}`)
      .join(' · ').slice(0, 450);
  }
  return `Error HTTP ${status}`;
};
function normalizeAxiosError(error) {
  if (error.message ==="La sesión ha vencido. Inicia sesión nuevamente.") {return error;}
  if (error.response) {
    return new Error(
      errorMessage(error.response.data, error.response.status)
    );}
  return new Error(
    "No fue posible conectar con Django.");}
async function request(path, options = {}, auth = null, onTokenRefresh = () => {}, retry = true) {
  const headers = { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers };
  if (auth?.access) headers.Authorization = `Bearer ${auth.access}`;
  let response;
  try {
    response = await fetch(path, { ...options, headers, credentials: 'omit', cache: 'no-store' });
  } catch {
    throw new Error('No es posible contactar el servidor. Inicia Django (puerto 8000) y Vite (puerto 5500).');
  }
  if (response.status === 401 && retry && auth?.refresh && path !== '/api/auth/refresh/') {
    try {
      const refreshed = await request('/api/auth/refresh/', {
        method: 'POST', body: JSON.stringify({ refresh: auth.refresh })
      }, null, () => {}, false);
      if (refreshed?.access) {
        const nextAuth = { ...auth, access: refreshed.access, refresh: refreshed.refresh || auth.refresh };
        onTokenRefresh(nextAuth);
        return request(path, options, nextAuth, onTokenRefresh, false);
      }
    } catch { /* devolver error original de sesión */ }
    throw new Error('La sesión ha vencido. Inicia sesión nuevamente.');
  }
  const text = await response.text();
  let data;
  try { data = text ? JSON.parse(text) : null; }
  catch { data = { detail: 'Respuesta inesperada del servidor Django.' }; }
  if (!response.ok) throw new Error(errorMessage(data, response.status));
  return data;
}
export const login = async (username, password) => {
  try {
    const response = await apiClient.post("auth/login/", {
      username,
      password,
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(
        errorMessage(error.response.data, error.response.status)
      );
    }
    throw new Error(
      "No se pudo conectar con Django. Comprueba que el backend esté funcionando.");}};

async function requestWithAxios(
  method,
  endpoint,
  payload,
  auth,
  onTokenRefresh
) {
  try {
    const response = await apiClient.request({
      method,
      url: endpoint,
      ...(payload !== undefined ? { data: payload } : {}),
    });

    return response.data;
  } catch (error) {
    throw normalizeAxiosError(error);
  }
}

export const getUsers = (auth, refresh) =>
  requestWithAxios("GET","usuarios/",undefined,auth,refresh);

export const getRoles = async (auth, refresh) => {try {const response = await apiClient.get("roles/");return response.data;} catch (error) {throw normalizeAxiosError(error);}};
export const createUser = (payload, auth, refresh) =>
  requestWithAxios("POST","usuarios/",payload,auth,refresh);
export const editUser = (id, payload, auth, refresh) =>
  requestWithAxios("PATCH",`usuarios/${encodeURIComponent(id)}/`,payload,auth,refresh);
export const listResult = data => Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);
