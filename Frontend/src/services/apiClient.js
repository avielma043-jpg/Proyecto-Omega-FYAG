
import axios from "axios";
import { useAuthStore } from "../stores/useAuthStore";

export const apiClient = axios.create({
  baseURL: "/api/",
  timeout: 15000,
  headers: {
    Accept: "application/json",
  },
});

// Controla que varias peticiones compartan una sola renovación.
let refreshPromise = null;

// 1. Adjuntar JWT a las solicitudes protegidas.
apiClient.interceptors.request.use((config) => {
  const session = useAuthStore.getState().session;

  if (session?.access) {
    config.headers.set(
      "Authorization",
      `Bearer ${session.access}`
    );
  }

  return config;
});

// 2. Detectar cuando el token de acceso ha vencido.
apiClient.interceptors.response.use(
  (response) => response,

  async (error) => {
    const original = error.config;
    const url = String(original?.url ?? "");

    // No reintentar errores diferentes de 401,
    // peticiones ya reintentadas ni el login.
    if (
      error.response?.status !== 401 ||
      !original ||
      original._retry ||
      url.includes("auth/login/") ||
      url.includes("auth/refresh/")
    ) {
      return Promise.reject(error);
    }

    const session = useAuthStore.getState().session;

    if (!session?.refresh) {
      return Promise.reject(error);
    }

    original._retry = true;

    // Solo una renovación aunque fallen varias peticiones.
    if (!refreshPromise) {
      const usedRefresh = session.refresh;

      refreshPromise = axios
        .post(
          "/api/auth/refresh/",
          { refresh: usedRefresh },
          { timeout: 15000 }
        )
        .then(({ data }) => {
          if (!data?.access) {
            throw new Error("Respuesta de renovación inválida.");
          }

          const current = useAuthStore.getState().session;

          // No restaurar una sesión cerrada o reemplazada.
          if (!current || current.refresh !== usedRefresh) {
            throw new Error("La sesión ya no está activa.");
          }

          const updated = {
            ...current,
            access: data.access,
            refresh: data.refresh || current.refresh,
          };

          useAuthStore.getState().saveSession(updated);

          return updated.access;
        })
        .catch(() => {
          const current = useAuthStore.getState().session;

          if (current?.refresh === usedRefresh) {
            useAuthStore.getState().clearSession();
          }

          throw new Error(
            "La sesión ha vencido. Inicia sesión nuevamente."
          );
        })
        .finally(() => {
          refreshPromise = null;
        });
    }

    try {
      const newAccess = await refreshPromise;

      // Reenviar la solicitud original con el token nuevo.
      original.headers = axios.AxiosHeaders.from(
        original.headers
      );

      original.headers.set(
        "Authorization",
        `Bearer ${newAccess}`
      );

      return apiClient(original);
    } catch (refreshError) {
      return Promise.reject(refreshError);
    }
  }
);
