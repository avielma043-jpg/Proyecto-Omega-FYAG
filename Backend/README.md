# Proyecto Omega - Frontend (ERP Web & PWA Móvil)
**Cliente:** Frío y Agroindustria SpA (FYAG)
**Versión:** 1.0.0 (MVP)

## 1. Alcance Global del Proyecto (Scope)
El Proyecto Omega digitaliza la cadena de valor de FYAG integrando la oficina central (bodega, compras, finanzas) con el personal desplegado en terreno (técnicos). El frontend es una **Single Page Application (SPA) construida en React (Vite)** que sirve dos experiencias de usuario totalmente distintas dependiendo del rol autenticado:

1. **ERP Web (Escritorio - `ERPLayout`):** Interfaz para administración. Incluye catálogos, ingresos de compras, control de inventario (Cardex), orquestación de obras y dashboards de rentabilidad.
2. **Portal Móvil (PWA - `MobileLayout`):** Interfaz diseñada bajo principios *Mobile-First* para técnicos en terreno. Posee botones de gran tamaño (Touch Targets), modo *offline* para operar dentro de cámaras frigoríficas, integración con la cámara del dispositivo y captura de firma digital mediante Canvas.

---

## 2. Seguridad y Control de Acceso (RBAC)
El sistema utiliza autenticación **Stateless con JWT (JSON Web Tokens)**. Los tokens expiran rápidamente y deben ser renovados (Rotación de Refresh Tokens) de forma transparente mediante interceptores de Axios. 

Existen 6 roles estrictos. El payload del token JWT devuelve el `id_rol` y `nombre_rol`, determinando el Layout y los menús visibles:

| Rol (nombre_rol) | Acceso Frontend (Layout) | Permisos Principales |
| :--- | :--- | :--- |
| **Administrador General** | ERP Web | Acceso total. CRUD usuarios. Autoriza reversas en Cardex. |
| **Administración** | ERP Web | Compras, facturación, clientes, presupuestos y KPIs. (No puede crear usuarios Admin Generales). |
| **Bodega/Logística** | ERP Web | Catálogo de artículos, ingresos de compras, egresos a obras, Cardex (Solo lectura/inserción). |
| **Supervisor de Obras** | ERP Web | Creación de obras, asignación de técnicos, cambio de estados, validación de horas. |
| **Técnico** | **PWA Móvil** | **Solo ve sus propias obras.** Consume materiales (Egresos), registra horas y firma hojas de servicio. |
| **Consulta** | ERP Web | Perfil auditor. Solo lectura global, sin capacidad de mutación (POST/PATCH/DELETE bloqueados). |

---

## 3. Arquitectura Offline e Idempotencia (PWA)
Las zonas agroindustriales (plantas frutícolas, viñas) tienen pésima conectividad. El frontend debe implementar un motor offline (Service Workers + IndexedDB/Dexie.js).

**El flujo obligatorio para Hojas de Servicio y Cardex (Egresos):**
1. Al detectar falta de red (`!navigator.onLine`), el frontend intercepta el formulario.
2. Genera un **UUID v4 (`client_uuid`)**.
3. Guarda el payload en IndexedDB (Cola de sincronización).
4. Al recuperar conexión, despacha la cola.
5. **Idempotencia:** Si la red se cae a la mitad de un POST exitoso y el frontend reintenta enviar el mismo `client_uuid`, el backend retornará `200 OK` (en lugar de `201 Created`) protegiendo el inventario de rebajas duplicadas.

---

## 4. Reglas de Negocio Críticas (Frontend)
1. **Inmutabilidad del Cardex:** Nunca envíes peticiones `PUT`, `PATCH` o `DELETE` a `/api/logistica/cardex/`. Solo acepta `POST`. Cualquier corrección se hace emitiendo un nuevo POST con `tipo_movimiento: 'REVERSA'`.
2. **Cálculos Financieros Enteros:** Toda moneda (CLP) viaja y se renderiza como `Integer`. Las cantidades fraccionarias de materiales/horas son `Decimal` de 2 posiciones.
3. **Descuentos Multiplicativos (Cascada):** En compras, el frontend debe simular visualmente la cascada de descuentos de los artículos: `Costo_Base * (1 - d1) * (1 - d2) * (1 - d3)`. El backend validará y calculará el valor final exacto.
4. **Máquina de Estados de Obra (HTTP 422):** Al intentar pasar una obra a estado `'Finalizada'`, el backend puede rechazar el `PATCH` con código `422 Unprocessable Entity` si faltan requisitos (Técnico, Firma, Horas o Egresos de materiales). El frontend debe capturar el array `errores` del JSON de respuesta y mostrarlo en un Toast rojo.

---

## 5. Diccionario de Endpoints (API RESTful)

> **Base URL:** El servidor de producción/staging (ej. `https://api.fyag.cl`).
> **Headers Globales:** `Authorization: Bearer <access_token>`, `Content-Type: application/json` (o `multipart/form-data` si aplica).

### Módulo CORE (Seguridad y Usuarios)
| Método | Endpoint | Payload Esperado (Body) | Respuesta Esperada | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/core/auth/login/` | `{ username, password }` | `200`: `{ access, refresh }` (el token ya incluye los claims `rut`, `id_rol`, `nombre_rol`). | Autenticación inicial. |
| `POST` | `/api/core/auth/refresh/` | `{ refresh }` | `200`: `{ access }` | Renovación del access token. |
| `GET` | `/api/core/usuarios/` | *Ninguno* | `200`: `[{ id_usuario, username, rut, first_name, email, rol, nombre_rol, estado_activo }]` | Listado paginado de usuarios. |
| `POST` | `/api/core/usuarios/` | `{ username, password, rut, first_name, last_name, email, rol }` | `201`: Objeto del usuario creado. | Crea usuario. `rol` es numérico. |
| `PATCH` | `/api/core/usuarios/<id>/`| `{ rol, estado_activo, password (opcional) }` | `200`: Usuario actualizado. | Desactiva o reasigna rol. |
| `GET` | `/api/core/roles/` | *Ninguno* | `200`: `[{ id_rol, nombre_rol }]` | Lista de roles (para `<select>`). |
| `GET` | `/api/core/lookups/tecnicos/`| *Ninguno* | `200`: `[{ id_usuario, username... }]` | **Sin Paginación:** Útil para poblar el `<select>` al asignar técnicos a obras. |

### Módulo LOGÍSTICA (Catálogo e Inventario)
| Método | Endpoint | Payload Esperado (Body) | Respuesta Esperada | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/logistica/articulos/` | *Ninguno* | `200`: `[{ id, codigo_interno, nombre, categoria, stock_disponible, precio_lista_vigente... }]` | Catálogo de bodega. |
| `POST` | `/api/logistica/articulos/` | `{ codigo_interno, nombre, categoria, unidad_medida, stock_minimo, precio_lista_vigente }` | `201`: Artículo creado. | Crear nuevo artículo. |
| `POST` | `/api/logistica/cardex/` | `{ id_articulo, tipo_movimiento, id_obra (opc), cantidad, precio_unitario, client_uuid (opc) }` | `201 Created` o `200 OK` (Si UUID ya existía). | **CRÍTICO:** Registra entradas y salidas de bodega. Retorna `400` si no hay stock suficiente para un egreso. |
| `GET` | `/api/logistica/lookups/articulos-activos/` | *Ninguno* | `200`: `[{ id, nombre, codigo_interno }]` | **Sin Paginación:** Para usar en los selectores de Compras y Egresos móviles. |

### Módulo COMPRAS (Proveedores y Facturación)
| Método | Endpoint | Payload Esperado (Body) | Respuesta Esperada | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/compras/proveedores/` | *Ninguno* | `200`: `[{ id, rut, razon_social, contactos: [] }]` | Directorio de proveedores. |
| `POST` | `/api/compras/documentos/` | `{ id_proveedor, tipo_documento, folio, fecha_ingreso, detalles: [ { id_articulo, cantidad, costo_base, descuento_1... } ] }` | `201`: Documento guardado. | Crea Factura/Boleta. El backend re-calcula subtotales e inyecta el stock al Cardex. |

### Módulo OBRAS (Proyectos y Terreno)
| Método | Endpoint | Payload Esperado (Body) | Respuesta Esperada | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/obras/obras/` | *Ninguno* | `200`: `[{ id, id_presupuesto, id_cliente, id_tecnico, tipo_servicio, estado }]` | Lista de Obras. (El backend oculta automáticamente las obras ajenas si eres Técnico). |
| `PATCH` | `/api/obras/obras/<id>/` | `{ estado, id_tecnico (opcional) }` | `200` o `422 Unprocessable Entity` (`{ errores: [] }`) | Cambia estado o asigna técnico. |
| `POST` | `/api/obras/hojas-servicio/`| `{ client_uuid, id_obra, estado_firma, firma_canvas_base64 }` | `201` o `200` (Idempotencia). | Firma del cliente capturada en terreno. |
| `POST` | `/api/obras/horas-trabajadas/`| `{ id_obra, id_tecnico, cantidad_horas, costo_hora }` | `201`: Horas registradas. | Imputación de HH a la obra. |
| `GET` | `/api/obras/lookups/clientes/` | *Ninguno* | `200`: `[{ id, razon_social, rut }]` | **Sin Paginación:** Para dropdowns de creación de Obras/Presupuestos. |

### Módulo REPORTES (Analítica y Exportaciones)
*Nota: Estas rutas devuelven JSON analítico o archivos binarios (`Blob`). Configura Axios con `responseType: 'blob'` para las descargas de archivos.*
| Método | Endpoint | Parámetros Query / Payload | Respuesta Esperada | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/reportes/dashboard-kpis/` | *Ninguno* | `200`: `{ obras_por_estado, alertas_stock_critico, compras_del_mes, presupuestos_aprobados_mes }` | Resumen global en tiempo real. |
| `GET` | `/api/reportes/rentabilidad-obras/`| *Ninguno* | `200`: `[{ id, tipo_servicio, monto_presupuesto, costo_materiales, costo_horas, margen_neto }]` | Estado financiero consolidado de obras. |
| `GET` | `/api/reportes/alertas-stock/` | *Ninguno* | `200`: `[{ id, codigo_interno, nombre, stock_disponible, deficit }]` | Lista de artículos debajo del stock mínimo ordenados por gravedad. |
| `GET` | `/api/reportes/exportar/cardex-excel/`| `?fecha_inicio=X&fecha_fin=Y&id_articulo=Z` | `200`: Binario `.xlsx` (`application/vnd.openxmlformats...`) | Descarga Excel del historial de bodega (Genera log de auditoría). |
| `GET` | `/api/reportes/exportar/hoja-servicio-pdf/<id_hoja>/` | *Ninguno* | `200`: Binario `.pdf` (`application/pdf`) | Renderiza comprobante en PDF con incrustación de la firma táctil base64. |

---
**Desarrollado para:** Operaciones de Alta Exigencia en la Agroindustria Chilena.