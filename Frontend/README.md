# Proyecto Omega — Frontend React + Vite

**Frontend nuevo y separado para la API Django de `Omega-main`.**

- Interfaz web implementada con **React 19**, componentes JSX y estado mediante `useState`/`useEffect`.
- Desarrollo y compilación con **Vite**.
- Backend original **Django REST Framework**, sin cambios.
- Conexión REAL a la API para inicio de sesión JWT, consulta de roles y creación/edición de usuarios.
- Inventario, Cardex, compras, obras, finanzas, reportes y vista de técnicos son **simulaciones locales en memoria**, porque `Omega-main` aún no expone esos endpoints.
- **No guarda los JWT en localStorage**. Al recargar la página, es necesario volver a iniciar sesión.
- Vista móvil diseñada con React. **No es todavía una PWA instalable con funcionamiento offline**; esa capacidad es futura.

## 1. Dónde ponerlo en Visual Studio Code

```text
ProyectoOmega/
├── Omega-main/            # Carpeta descomprimida del compañero, sin cambios
│   ├── manage.py
│   ├── Omega/
│   └── core/
└── Frontend_Omega_React/  # Esta carpeta (separada)
    ├── package.json
    ├── vite.config.js
    ├── index.html
    ├── src/
    │   ├── App.jsx
    │   ├── Pages.jsx
    │   ├── Users.jsx
    │   ├── Technician.jsx
    │   ├── api.js
    │   ├── data.js
    │   └── ...
    └── README.md
```

Abre la carpeta `ProyectoOmega` en **Visual Studio Code**. Requiere **Node.js 22 LTS** (con npm), Python y el ambiente Django del backend.

## 2. Terminal 1: Django

Dentro de `Omega-main` (asegúrate de que Django, DRF, SimpleJWT, el driver de PostgreSQL y las dependencias del backend estén instaladas y la base de datos esté configurada):

```powershell
cd Omega-main
py manage.py runserver 127.0.0.1:8000
```

Django debe permanecer ejecutándose para las funciones reales. No hay que cambiar `settings.py`, `urls.py` ni los archivos de `core`.

## 3. Terminal 2: React

Dentro de `Frontend_Omega_React`:

```powershell
cd Frontend_Omega_React
npm install
npm run dev
```

En el navegador abre **http://127.0.0.1:5500**.

También puedes iniciar React con doble clic en `iniciar_frontend.bat` (instala dependencias si aún no hay `node_modules`).

**No abras `index.html` haciendo doble clic**: React y sus importaciones se sirven a través de Vite.

### ¿Por qué no hay que configurar CORS?

`vite.config.js` tiene un proxy de desarrollo:

```js
'/api' -> 'http://127.0.0.1:8000'
```

Así, el navegador consulta `127.0.0.1:5500/api/...` y Vite reenvía esa solicitud al backend. No se necesita editar `Omega-main` para desarrollar localmente. Esta configuración **no equivale a un despliegue de producción**.

## 4. Iniciar sesión

Hay dos formas de acceder:

**Login real de Django**: usuario y contraseña de una cuenta activa en PostgreSQL. Django devuelve tokens `access`, `refresh`, `nombre_rol` e `id_usuario`. Los roles del backend se traducen a los nombres visuales del frontend. Para gestionar usuarios necesitas una cuenta con rol `Administrador General` o `Administración`.

**Modo demostración**: elige un perfil y entra sin conectarte a Django. Los datos son ficticios y se restablecen al actualizar.

### Rutas Django que sí se utilizan

- `POST /api/auth/login/`
- `POST /api/auth/refresh/`
- `GET /api/roles/`
- `GET /api/usuarios/`
- `POST /api/usuarios/`
- `PATCH /api/usuarios/{id}/`

**Nunca utilices usuarios reales para pruebas de creación/edición sin autorización**: estos endpoints sí escriben datos.

## 5. Simulaciones incluidas

- **Inicio / Dashboard:** métricas ilustrativas y acceso a módulos.
- **Inventario y Cardex:** artículos, filtros, ingresos/egresos, control de stock, reversas compensatorias simuladas.
- **Compras:** descuentos sucesivos, coste neto y entrada de inventario.
- **Obras:** crear/iniciar/finalizar con condiciones mínimas de horas, fotografía, técnico y firma.
- **Finanzas / Reportes:** facturas, cobranzas y trazabilidad de movimientos.
- **Vista técnico:** mis obras, hoja de servicio, horas y materiales, fotografías y firma en `canvas`.
- **Usuarios:** listado y formulario reales contra Django (solo con sesión y perfil autorizado).

**No afirmar en la presentación que el Cardex inmutable, los bloqueos ACID, el cierre financiero o las evidencias persistentes ya están implementados.** Actualmente se simulan en React; su validación real depende de endpoints, transacciones y restricciones futuras del backend.

## 6. Compilación y pruebas

```powershell
npm run build
npm run preview
npm run test:smoke
```

El comando `build` genera `dist/`. `preview` permite visualizar el resultado de compilación, pero el proxy de `/api` está configurado para `npm run dev`, **no para una versión de producción**.

Para cambiar el puerto de Django de desarrollo, modifica `target` en `vite.config.js` en esta carpeta (no en el backend).

## 7. Próxima integración

Cuando estén creados los endpoints de inventario, Cardex, obras y hojas de servicio en `Omega-main`, reemplazar las operaciones en memoria de `App.jsx` por solicitudes a las nuevas rutas dentro de `src/api.js`. Mantener las validaciones finales en Django, no en React.

## Validación de la entrega

En el entorno de creación, todos los archivos `.jsx` y `.js` pasaron el análisis sintáctico con el parser de TypeScript y los contratos básicos HTTP pasaron pruebas simuladas. No fue posible descargar dependencias npm para ejecutar el build en ese entorno, por lo que **el primer `npm install` y `npm run build` deben verificarse en el computador del usuario**.
