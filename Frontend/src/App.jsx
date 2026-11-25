import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ACCESS, LINKS, ROLES, NORMALIZE_ROLE, seed, money, dateNow, nextId } from './data';
import { Brand, PageHeading, DemoNotice, Stat } from './ui';
import { Dashboard, Inventory, Purchases, Works, Finance, Reports } from './Pages';
import Users from './Users';
import Technician from './Technician';
import { login, getRoles, getUsers, listResult } from './api';
import { useAuthStore } from "./stores/useAuthStore";
import InventoryReal from "./InventoryReal";
import {Navigate,useLocation,useNavigate} from "react-router-dom";
import ObrasReal from "./ObrasReal";

const defaultUsersState={ users:[], roles:[], loading:false, loaded:false, error:'' };

export default function App() {
  const [demo,setDemo]=useState(seed);
  const auth = useAuthStore((state) => state.session);
  const saveSession = useAuthStore((state) => state.saveSession);
  const clearSession = useAuthStore((state) => state.clearSession);

function changeAuth(nextSession) {
  if (nextSession) {
    saveSession(nextSession);
  } else {
    clearSession();}}

const navigate = useNavigate();
const location = useLocation();

const currentPage = location.pathname.replace(
  /^\/+|\/+$/g,"");
const nav = currentPage;
const mode = currentPage === "tech" ? "tech" : "erp";

async function realLogin(event) {
  event.preventDefault();
  if (loginBusy) return;
  const form = new FormData(event.currentTarget);
  const username = String(
    form.get("username") || ""
  ).trim();
  const password = String(
    form.get("password") || ""
  );
  if (!username || !password) {
    setLoginError("Completa usuario y contraseña.");
    return;
  }
  setLoginError("");
  setLoginBusy(true);
  try {
    const data = await login(username, password);
    if (!data?.access || !data?.refresh || !data?.nombre_rol) {
      throw new Error(
        "El backend no devolvió los datos necesarios."
      );
    }
    const session = {
      access: data.access,
      refresh: data.refresh,
      id_usuario: data.id_usuario,
      id_rol: data.id_rol,
      rut: data.rut,
      nombre_rol: data.nombre_rol,
      username,
      real: true,
    };
    changeAuth(session);

    setLogged(true);

    const mapped =
      NORMALIZE_ROLE[data.nombre_rol] || "Consulta";

    setRole(mapped);
navigate(
  mapped === "Técnico en Terreno"
    ? "/tech"
    : "/dashboard",
  { replace: true }
);

    setApiState(defaultUsersState);

    notify("Sesión iniciada correctamente.");

  } catch (error) {
    setLoginError(error.message);
  } finally {
    setLoginBusy(false);}}
  const [logged,setLogged]=useState(false);
  const [role,setRole]=useState('Administrador General');
  const [toastData,setToast]=useState(null);
  const toastTimer=useRef(null);
  const [apiState,setApiState]=useState(defaultUsersState);
  const [loginBusy,setLoginBusy]=useState(false);
  const [loginError,setLoginError]=useState('');
  const [demoRole,setDemoRole]=useState('Administrador General');
  const can = id => (ACCESS[role]||[]).includes(id);
  const canInventory = ['Administrador General','Bodega / Logística'].includes(role);
  const canWorks = ['Administrador General','Supervisor de Obras'].includes(role);

  const notify=useCallback((message,isError=false)=>{
    setToast({message,isError});
    clearTimeout(toastTimer.current);
    toastTimer.current=setTimeout(()=>setToast(null),4200);
  },[]);
  useEffect(()=>()=>clearTimeout(toastTimer.current),[]);

  
function logout(message) {
  clearSession();

  setLogged(false);
  setDemo(seed());
  setRole("Administrador General");

  setApiState(defaultUsersState);
  navigate("/login", { replace: true });
  if (message) notify(message, true);
}


function demoLogin() {
  setLogged(true);
  changeAuth(null);
  setRole(demoRole);
  setApiState(defaultUsersState);

  navigate(
    demoRole === "Técnico en Terreno"
      ? "/tech"
      : "/dashboard",
    { replace: true });notify("Ingresaste a la demostración. Los datos se mantienen solo en esta página.");}


function go(id) {if (can(id)) {navigate(`/${id}`);
  } else {
    notify("Tu perfil no tiene acceso a esa sección.",true);}}
  function resetDemo(){if(window.confirm('¿Restaurar los datos de ejemplo? Se perderán los cambios temporales.')){setDemo(seed());notify('Datos de demostración restaurados.')}}

  const refreshUsers=useCallback(async()=>{
    if(!useAuthStore.getState().session || !['Administrador General','Administración / Finanzas'].includes(role))return;
    setApiState(x=>({...x,loading:true,error:''}));
    try {
      const current=useAuthStore.getState().session;
      const [users,roles]=await Promise.all([
        getUsers(current,changeAuth),getRoles(current,changeAuth)
      ]);
      setApiState({users:listResult(users),roles:listResult(roles),loaded:true,loading:false,error:''});
    } catch(err){
      setApiState(x=>({...x,loading:false,error:err.message}));
      if(/sesión ha vencido/i.test(err.message))logout('La sesión caducó.');
    }
  },[role]);
  useEffect(()=>{if(logged&&auth&&nav==='security'&&['Administrador General','Administración / Finanzas'].includes(role)&&!apiState.loaded&&!apiState.loading)refreshUsers();},[logged,!!auth,nav,role,apiState.loaded,apiState.loading,refreshUsers]);

  function appendLog(d,msg){d.activities.unshift({msg,date:dateNow()});d.activities=d.activities.slice(0,20)}
  function createMovement(d,{itemId,qty,type,workId=null,price=null,reversalOf=null}){
    const i=d.items.find(a=>a.id===itemId);
    if(!i)return null;
    const id=nextId('MOV-',d.movements);
    const movement={id,itemId,qty,type,workId,user:mode==='tech'?'Técnico en Terreno':role,date:dateNow(),price:price??i.price,reversalOf};
    i.stock+=qty;d.movements.push(movement);
    if(workId&&qty<0){const w=d.works.find(x=>x.id===workId);w?.usage.push({itemId,qty:-qty,price:i.price,movementId:id,reversed:false});}
    appendLog(d,`${type}: ${i.name} (${qty>=0?'+':''}${qty})`);
    return movement;
  }
  function addArticle(v){
    if(!canInventory)return notify('Este perfil no puede crear artículos.',true),false;
    const name=String(v.name||'').trim(),stock=Number(v.stock),min=Number(v.min),price=Number(v.price);
    if(!name||!Number.isInteger(stock)||stock<0||!Number.isInteger(min)||min<0||!Number.isFinite(price)||price<=0){notify('Revisa los datos del artículo.',true);return false;}
    setDemo(d=>{const n=structuredClone(d);const id=nextId('ART-',n.items);n.items.push({id,name,category:v.category,stock:0,min,price,cost:price*.7});if(stock>0)createMovement(n,{itemId:id,qty:stock,type:'Ingreso'});return n;});
    notify(`Artículo «${name}» agregado (solo demo).`);return true;
  }
  function addMovement({itemId,qty,type,workId=null}){
    if(!canInventory){notify('No tienes permiso para modificar inventario.',true);return false;}
    const i=demo.items.find(x=>x.id===itemId);
    if(!i||!Number.isInteger(qty)||qty<=0){notify('Selecciona un artículo y una cantidad válida.',true);return false;}
    if(type!=='Ingreso'&&type!=='Egreso'){notify('Movimiento no permitido.',true);return false;}
    if(type==='Egreso'&&!workId){notify('El egreso debe asociarse a una obra.',true);return false;}
    if(type==='Egreso'&&i.stock<qty){notify(`Stock insuficiente. Disponibles: ${i.stock}.`,true);return false;}
    setDemo(d=>{const n=structuredClone(d);createMovement(n,{itemId,qty:type==='Ingreso'?qty:-qty,type,workId});return n;});
    notify('Movimiento agregado al Cardex demostrativo.');return true;
  }
  function reverseMovement(id){
    if(role!=='Administrador General'){notify('Solo Administrador General puede autorizar reversas.',true);return false;}
    const orig=demo.movements.find(x=>x.id===id);
    if(!orig||orig.reversalOf||demo.movements.some(m=>m.reversalOf===id)){notify('El movimiento ya fue reversado o no admite reversa.',true);return false;}
    const article=demo.items.find(i=>i.id===orig.itemId);
    if(!article||article.stock-orig.qty<0){notify('La reversa dejaría el stock negativo.',true);return false;}
    setDemo(d=>{const n=structuredClone(d);createMovement(n,{itemId:orig.itemId,qty:-orig.qty,type:'Reversa',price:orig.price,reversalOf:id});for(const w of n.works){for(const u of w.usage){if(u.movementId===id)u.reversed=true}}return n;});
    notify('Reversa compensatoria creada: se conserva el movimiento original.');return true;
  }
  function registerPurchase(v){
    if(!canInventory){notify('Permisos insuficientes.',true);return false;}
    const i=demo.items.find(x=>x.id===v.item),qty=Number(v.qty),cost=Number(v.cost),discounts=[v.d1,v.d2,v.d3].map(Number);
    if(!i||!Number.isInteger(qty)||qty<1||cost<=0||!discounts.every(d=>Number.isFinite(d)&&d>=0&&d<100)){notify('Cantidad o descuentos inválidos.',true);return false;}
    const net=discounts.reduce((x,d)=>x*(1-d/100),cost);
    setDemo(d=>{const n=structuredClone(d);const item=n.items.find(x=>x.id===v.item);item.cost=net;createMovement(n,{itemId:v.item,qty,type:'Ingreso',price:net});return n;});
    notify(`Compra simulada: +${qty} unidades, total ${money(net*qty)}.`);return true;
  }
  function createWork(v){
    if(!canWorks){notify('Solo el supervisor o administrador puede crear obras.',true);return false;}
    const name=String(v.name||'').trim(),client=String(v.client||'').trim(),city=String(v.city||'').trim();
    if(!name||!client||!city){notify('Completa los campos de la obra.',true);return false;}
    setDemo(d=>{const n=structuredClone(d);const id=nextId('OB-',n.works);n.works.unshift({id,name,client,city,status:'Pendiente',technician:v.technician||'Juan Pérez',hours:0,description:'',usage:[],photos:[],signature:null});appendLog(n,`Obra ${id} creada`);return n;});
    notify('Obra creada en la demostración.');return true;
  }
  function startWork(id){if(!canWorks){notify('Permisos insuficientes.',true);return false;}
    const w=demo.works.find(x=>x.id===id);if(!w||w.status!=='Pendiente')return false;
    setDemo(d=>{const n=structuredClone(d),target=n.works.find(x=>x.id===id);target.status='En curso';appendLog(n,`Obra ${id} iniciada`);return n;});notify('Obra iniciada.');return true;
  }
  function finishWork(id){if(!canWorks){notify('Solo el supervisor/administrador puede finalizar obras.',true);return false;}
    const w=demo.works.find(x=>x.id===id);
    if(!w||!w.technician||w.hours<=0||!w.photos.length||!w.signature){notify('Faltan técnico, horas, fotografías o firma del cliente.',true);return false;}
    setDemo(d=>{const n=structuredClone(d);n.works.find(x=>x.id===id).status='Finalizada';appendLog(n,`Obra ${id} finalizada`);return n;});notify('Obra finalizada en la demostración.');return true;
  }
  function payInvoice(id){if(!['Administrador General','Administración / Finanzas'].includes(role))return false;
    setDemo(d=>{const n=structuredClone(d);const i=n.invoices.find(x=>x.id===id);if(i)i.status='Pagada';appendLog(n,`Factura ${id} conciliada`);return n;});notify('Factura marcada pagada (demo).');return true;
  }
  function saveDescription(id,value){const text=value.trim();if(!text){notify('Describe las actividades realizadas.',true);return false;}
    const w=demo.works.find(x=>x.id===id);if(!w||w.status==='Finalizada')return false;
    setDemo(d=>{const n=structuredClone(d),target=n.works.find(x=>x.id===id);target.description=text;if(target.status==='Pendiente')target.status='En curso';return n;});notify('Hoja de servicio guardada en la demo.');return true;
  }
  function saveHours(id,hours){if(!Number.isFinite(hours)||hours<0||hours>500){notify('Cantidad de horas inválida.',true);return false;}
    setDemo(d=>{const n=structuredClone(d),w=n.works.find(x=>x.id===id);if(w&&w.status!=='Finalizada'){w.hours=hours;appendLog(n,`Horas ${id}: ${hours}`);}return n;});notify('Horas guardadas (demo).');return true;
  }
  function addTechItem(id,itemId,qty){const i=demo.items.find(x=>x.id===itemId),w=demo.works.find(x=>x.id===id);
    if(!w||w.status==='Finalizada'||!i||!Number.isInteger(qty)||qty<=0){notify('Material o cantidad inválida.',true);return false;}
    if(i.stock<qty){notify(`Stock insuficiente. Disponibles: ${i.stock}.`,true);return false;}
    setDemo(d=>{const n=structuredClone(d);createMovement(n,{itemId,qty:-qty,type:'Egreso',workId:id});const target=n.works.find(x=>x.id===id);if(target.status==='Pendiente')target.status='En curso';return n;});notify('Consumo registrado en el Cardex demostrativo.');return true;
  }
  function addPhoto(id,photo){setDemo(d=>{const n=structuredClone(d),w=n.works.find(x=>x.id===id);if(w&&w.status!=='Finalizada'){w.photos.push(photo);appendLog(n,`Foto añadida a ${id}`);}return n;});notify('Fotografía añadida en memoria (demo).');return true;}
  function saveSignature(id,signature){setDemo(d=>{const n=structuredClone(d),w=n.works.find(x=>x.id===id);if(w&&w.status!=='Finalizada')w.signature=signature;return n;});if(!signature)notify('Firma borrada.');return true;}
  function submitService(id){const w=demo.works.find(x=>x.id===id);
    if(!w||!w.description.trim()){notify('Primero completa la descripción del servicio.',true);return false;}
    if(w.hours<=0){notify('Registra horas trabajadas.',true);return false;}
    if(!w.photos.length){notify('Adjunta al menos una fotografía.',true);return false;}
    if(!w.signature){notify('Necesitas la firma del cliente.',true);return false;}
    setDemo(d=>{const n=structuredClone(d);n.works.find(x=>x.id===id).status='Pendiente revisión';appendLog(n,`Hoja ${id} enviada a revisión`);return n;});notify('Hoja de servicio enviada a revisión (simulación).');return true;
  }
  const techActions={saveDescription,saveHours,addTechItem,addPhoto,saveSignature,submitService};

// Si no inició sesión, solo puede ver el login.
if (!logged && currentPage !== "login") {
  return <Navigate to="/login" replace />;
}

// Si inició sesión y vuelve al login,
// enviamos al usuario a su pantalla principal.
if (
  logged &&
  (currentPage === "login" || currentPage === "")
) {
  return (
    <Navigate
      to={
        role === "Técnico en Terreno"
          ? "/tech"
          : "/dashboard"
      }
      replace
    />
  );
}

// Comprobamos que el rol tenga acceso
// al módulo solicitado.
if (
  logged &&
  currentPage !== "tech" &&
  !(ACCESS[role] || []).includes(currentPage)
) {
  return (
    <Navigate
      to={
        role === "Técnico en Terreno"
          ? "/tech"
          : "/dashboard"
      }
      replace
    />
  );
}

  if(!logged)return <><div className="login-screen"><section className="login-visual"><Brand/>
      <div><span className="eyebrow" style={{color:'#a1d5ff'}}>PROYECTO OMEGA · FYAG</span><h1>Gestión eficiente<br/>para un mejor servicio.</h1><p>Plataforma de gestión integrada para inventario, obras, finanzas y servicios técnicos en terreno.</p></div>
      <div className="login-features"><span>▣ Inventario trazable</span><span>♧ Control de obras</span><span>▤ Servicio móvil PWA (prototipo)</span><span>♙ Roles RBAC</span></div>
    </section><section className="login-form-area"><div className="login-panel"><Brand dark={false}/><div style={{marginTop:45}}><span className="eyebrow">ACCESO EMPRESARIAL</span><h2>Bienvenido a Omega.</h2><p>Ingresa con tus credenciales de Django, o utiliza el modo demostración sin base de datos.</p></div>
      <form onSubmit={realLogin}><div className="form-field"><label>Usuario Django</label><input className="form-control" name="username" autoComplete="username" placeholder="admin" required/></div><div className="form-field"><label>Contraseña</label><input className="form-control" name="password" type="password" autoComplete="current-password" required/></div>{loginError&&<div className="error-banner" role="alert">{loginError}</div>}<button className="btn primary full" disabled={loginBusy}>{loginBusy?'Conectando a Django…':'Iniciar sesión con Django'}</button></form>
      <div className="login-note"><b>Conexión real:</b> utiliza la API Django en <code>/api/auth/login/</code>. Si Django no está iniciado, el acceso real no estará disponible.</div>
      <div className="divide" style={{marginTop:24}}></div><p><b>Modo demostración</b> — no escribe datos en PostgreSQL.</p><div className="form-field"><label>Perfil de prueba</label><select value={demoRole} onChange={e=>setDemoRole(e.target.value)} className="form-control">{ROLES.map(r=><option key={r}>{r}</option>)}</select></div><button className="btn ghost full" onClick={demoLogin}>Entrar a demostración</button>
    </div></section></div>{toastData&&<div className={`fixed-toast ${toastData.isError?'error':''}`}>{toastData.message}</div>}</>;


  if (mode === "tech") {
    return (
      <>
        <Technician
          demo={demo}
          actions={techActions}
          toast={notify}
          back={() =>
            role === "Técnico en Terreno"
              ? logout()
              : navigate("/dashboard")
          }
          isReal={!!auth}
        />

        {toastData && (
          <div
            className={`fixed-toast ${toastData.isError ? "error" : ""}`}
            role="status"
          >
            {toastData.message}
          </div>
        )}
      </>
    );
  }

  const titles = {
    dashboard: "Panel de control",
    inventory: "Inventario y Cardex",
    purchases: "Compras",
    works: "Obras y Técnicos",
    finance: "Clientes y Finanzas",
    reports: "Reportes",
    security: "Usuarios y Seguridad",
  };

  const erpPages = {
    dashboard: (
      <Dashboard
        demo={demo}
        role={role}
        go={go}
        openTech={() => navigate("/tech")}
      />
    ),

    // INVENTARIO REAL CUANDO HAY SESIÓN JWT
    inventory: auth ? (
      <InventoryReal role={role} />
    ) : (
      <Inventory
        demo={demo}
        role={role}
        addArticle={addArticle}
        addMovement={addMovement}
        reverseMovement={reverseMovement}
        showMessage={notify}
      />
    ),

    purchases: (
      <Purchases
        demo={demo}
        role={role}
        registerPurchase={registerPurchase}
      />
    ),


    works: auth ? (
      <ObrasReal />
    ) : (
      <Works
        demo={demo}
        role={role}
        createWork={createWork}
        startWork={startWork}
        finishWork={finishWork}
      />
    ),


    finance: (
      <Finance
        demo={demo}
        role={role}
        payInvoice={payInvoice}
      />
    ),

    reports: <Reports demo={demo} />,
  };

  return (
    <>
      <div className="layout">
        <aside className="sidebar">
          <Brand />

          <div className="nav-section">
            MENÚ PRINCIPAL
          </div>

          <nav
            className="nav-list"
            aria-label="Módulos del ERP"
          >
            {LINKS.filter((l) => can(l.id)).map((l) => (
              <button
                key={l.id}
                className={`nav-item ${
                  nav === l.id ? "active" : ""
                }`}
                onClick={() => go(l.id)}
                title={l.label}
              >
                <span className="glyph">{l.icon}</span>
                <span className="nav-label">{l.label}</span>
              </button>
            ))}
          </nav>

          <div className="sidebar-foot">
            <div className="side-user">
              <span className="avatar">
                {role.slice(0, 2).toUpperCase()}
              </span>

              <div>
                {role}
                <small>
                  {auth?.username || "Perfil de prueba"}
                </small>
              </div>
            </div>

            <button
              className="side-link"
              onClick={() => logout()}
            >
              ↩ Cerrar sesión
            </button>
          </div>
        </aside>

        <div className="main-area">
          <header className="topbar">
            <div>
              <h1>
                {titles[nav] || "Proyecto Omega"}
              </h1>

              <small>
                Proyecto Omega · Frío y Agroindustria SpA
              </small>
            </div>

            <div className="top-actions">
              <span
                className={`pill ${auth ? "" : "demo"}`}
              >
                <span className="dot" />
                {auth
                  ? "Sesión JWT · Django"
                  : "Modo demostración"}
              </span>

              <button
                className="btn ghost sm"
                onClick={resetDemo}
              >
                ↻ Reiniciar demo
              </button>

              <button
                className="btn primary sm"
                onClick={() => navigate("/tech")}
              >
                ▣ Vista técnico (demo)
              </button>
            </div>
          </header>

          <main className="content" key={nav}>
            {nav === "security" ? (
              auth ? (
                <Users
                  auth={auth}
                  users={apiState.users}
                  roles={apiState.roles}
                  loading={apiState.loading}
                  error={apiState.error}
                  refreshUsers={refreshUsers}
                  changeAuth={changeAuth}
                  toast={notify}
                  expireSession={() =>
                    logout("La sesión caducó.")
                  }
                />
              ) : (
                <>
                  <DemoNotice />

                  <PageHeading
                    title="Usuarios, roles y seguridad"
                    description="Perfiles RBAC contemplados para Proyecto Omega."
                  />

                  <div className="card-grid">
                    {ROLES.map((r) => (
                      <div className="card" key={r}>
                        <h3>{r}</h3>

                        <p className="helper">
                          Permisos asociados:{" "}
                          {(ACCESS[r] || [])
                            .map((l) => titles[l])
                            .join(", ") || "Portal técnico"}
                        </p>
                      </div>
                    ))}
                  </div>

                  <div className="test-banner">
                    Para crear o editar usuarios reales,
                    inicia sesión contra Django con una
                    cuenta autorizada.
                  </div>
                </>
              )
            ) : (
              erpPages[nav] || (
                <Dashboard
                  demo={demo}
                  role={role}
                  go={go}
                  openTech={() => navigate("/tech")}
                />
              )
            )}
          </main>
        </div>
      </div>

      {toastData && (
        <div
          className={`fixed-toast ${
            toastData.isError ? "error" : ""
          }`}
          role="status"
        >
          {toastData.message}
        </div>
      )}
    </>
  );
}

