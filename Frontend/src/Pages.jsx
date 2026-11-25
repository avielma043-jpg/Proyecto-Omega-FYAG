import React, { useState } from 'react';
import { money, nfmt, costWork } from './data';
import { PageHeading, DemoNotice, Stat, Tag, DataCard, FormField, Modal } from './ui';

const toItem = (items, id) => items.find(i => i.id === id);
const toWork = (works, id) => works.find(w => w.id === id);

export function Dashboard({ demo, role, go, openTech }) {
  const low = demo.items.filter(i => i.stock <= i.min);
  const active = demo.works.filter(w => w.status === 'En curso');
  const pending = demo.invoices.filter(i => i.status === 'Pendiente');
  return <><DemoNotice/><PageHeading title="Panel de control" description="Vista general de las operaciones de Frío y Agroindustria SpA."/>
    <div className="stat-grid">
      <Stat title="Artículos en bodega" value={demo.items.length} meta="Catálogo ilustrativo" icon="▣"/>
      <Stat title="Obras en ejecución" value={active.length} meta="Trabajos activos" icon="♧" accent="#12a278" tint="#e7f8ee"/>
      <Stat title="Stock crítico" value={low.length} meta="Materiales por reponer" icon="!" accent="#ec9a25" tint="#fff2df"/>
      <Stat title="Cobros pendientes" value={money(pending.reduce((a,b)=>a+b.amount,0))} meta="Total ilustrativo" icon="$" accent="#8467e8" tint="#f0eafa"/>
    </div>
    <div className="grid-2">
      <DataCard title="Obras recientes" sub="Seguimiento de la operación simulada">
        {demo.works.map(w=><div className="list-row" key={w.id}><span className="row-icon">♧</span><div className="flex-grow"><strong>{w.name}</strong><small>{w.id} · {w.client}</small></div><Tag value={w.status}/></div>)}
        <button className="btn subtle section-gap" onClick={()=>go('works')}>Ver gestión de obras</button>
      </DataCard>
      <DataCard title="Accesos rápidos" sub="Consulta los principales procesos de la empresa">
        <div className="stacked">
          <button className="btn ghost" onClick={()=>go('inventory')}>▣ Inventario y Cardex</button>
          <button className="btn ghost" onClick={()=>go('purchases')}>▤ Compras y descuentos</button>
          <button className="btn ghost" onClick={()=>go('works')}>♧ Obras y servicios</button>
          <button className="btn ghost" onClick={openTech}>▣ Abrir PWA para técnicos (demo)</button>
        </div>
        <div className="test-banner"><b>Rol actual:</b> {role}. Los cambios de estas pantallas no se guardan en PostgreSQL.</div>
      </DataCard>
    </div></>;
}

export function Inventory({ demo, role, addArticle, addMovement, reverseMovement, showMessage }) {
  const [tab,setTab]=useState('items');
  const [filter,setFilter]=useState('Todos');
  const [search,setSearch]=useState('');
  const [modal,setModal]=useState(null);
  const isEditor=['Administrador General','Bodega / Logística'].includes(role);
  const filtered = demo.items.filter(i => (filter === 'Todos' || (filter === 'Bajo stock' ? i.stock <= i.min : i.category === filter))
    && `${i.id} ${i.name}`.toLowerCase().includes(search.toLowerCase()));
  const categories = ['Todos','Bajo stock',...new Set(demo.items.map(i=>i.category))];
  function submitArticle(e) {e.preventDefault();const v=Object.fromEntries(new FormData(e.currentTarget));if(addArticle(v))setModal(null);}
  function submitMovement(e) {e.preventDefault();const v=Object.fromEntries(new FormData(e.currentTarget));if(addMovement({itemId:v.item,qty:Number(v.qty),type:v.type,workId:v.work||null})){setModal(null);setTab('cardex');}}
  return <><DemoNotice/><PageHeading title="Inventario y Cardex" description="Control de materiales, existencias y movimientos sin eliminación del historial." actions={isEditor&&<>
    <button className="btn ghost" onClick={()=>setModal('article')}>+ Nuevo artículo</button>
    <button className="btn primary" onClick={()=>setModal('movement')}>↔ Registrar movimiento</button></>}/>
    <div className="stat-grid">
      <Stat title="Total de unidades" value={nfmt(demo.items.reduce((a,b)=>a+b.stock,0))} meta="Stock físico simulado"/>
      <Stat title="Artículos registrados" value={demo.items.length} meta="Catálogo centralizado" icon="▤" accent="#12a278" tint="#e5f7ee"/>
      <Stat title="Bajo stock" value={demo.items.filter(i=>i.stock<=i.min).length} meta="Requieren reposición" icon="!" accent="#ec9a25" tint="#fff2df"/>
      <Stat title="Movimientos" value={demo.movements.length} meta="Historial de simulación" icon="↔" accent="#8f71e9" tint="#f0eafe"/>
    </div>
    <div className="card"><div className="tabbar"><button className={`tab ${tab==='items'?'active':''}`} onClick={()=>setTab('items')}>Existencias</button><button className={`tab ${tab==='cardex'?'active':''}`} onClick={()=>setTab('cardex')}>Cardex / Auditoría</button></div>
      {tab==='items'?<><div className="toolbar"><input className="form-control search" aria-label="Buscar artículo" value={search} onChange={e=>setSearch(e.target.value)} placeholder="⌕ Buscar artículo por nombre o código"/><select className="form-control" style={{width:160}} value={filter} onChange={e=>setFilter(e.target.value)}>{categories.map(c=><option key={c}>{c}</option>)}</select></div>
        <div className="table-wrap"><table className="data-table"><thead><tr><th>Artículo</th><th>Categoría</th><th>Stock actual</th><th>Stock mínimo</th><th>Precio de lista</th><th>Estado</th></tr></thead><tbody>{filtered.map(i=><tr key={i.id}><td><strong>{i.name}</strong><small>{i.id}</small></td><td>{i.category}</td><td><b>{nfmt(i.stock)}</b></td><td>{nfmt(i.min)}</td><td>{money(i.price)}</td><td><Tag value={i.stock<=i.min?'Crítico':'Disponible'}/></td></tr>)}</tbody></table></div>{!filtered.length&&<div className="empty">Sin artículos que coincidan.</div>}</>:
        <div className="table-wrap"><table className="data-table"><thead><tr><th>Movimiento</th><th>Fecha</th><th>Artículo</th><th>Tipo</th><th>Cantidad</th><th>Obra</th><th>Responsable</th><th>Reversa</th></tr></thead><tbody>{[...demo.movements].reverse().map(m=>{const already=demo.movements.some(x=>x.reversalOf===m.id);return <tr key={m.id}><td><b>{m.id}</b><small>{m.reversalOf?`Compensa ${m.reversalOf}`:''}</small></td><td>{m.date}</td><td>{toItem(demo.items,m.itemId)?.name}</td><td><Tag value={m.type}/></td><td className={m.qty>=0?'amount plus':'amount minus'}>{m.qty>0?'+':''}{m.qty}</td><td>{m.workId||'—'}</td><td>{m.user}</td><td>{role==='Administrador General'&&!m.reversalOf&&!already?<button className="btn tiny ghost" onClick={()=>{if(window.confirm(`¿Crear un movimiento de reversa para ${m.id}?`))reverseMovement(m.id);}}>Reversar</button>:'—'}</td></tr>})}</tbody></table></div>}
    </div>
    {modal==='article'&&<Modal title="Crear artículo (demostración)" onClose={()=>setModal(null)}><form onSubmit={submitArticle}><div className="form-grid"><FormField label="Nombre" full><input className="form-control" name="name" required maxLength={80}/></FormField><FormField label="Categoría"><select className="form-control" name="category">{['Refrigeración','Materiales','Electricidad','Equipos','Instrumentación'].map(c=><option key={c}>{c}</option>)}</select></FormField><FormField label="Stock inicial"><input className="form-control" name="stock" type="number" min="0" defaultValue="10" required/></FormField><FormField label="Stock mínimo"><input className="form-control" name="min" type="number" min="0" defaultValue="5" required/></FormField><FormField label="Precio de lista (CLP)"><input className="form-control" name="price" type="number" min="1" defaultValue="15000" required/></FormField></div><div className="modal-footer"><button type="button" className="btn ghost" onClick={()=>setModal(null)}>Cancelar</button><button className="btn primary">Crear artículo</button></div></form></Modal>}
    {modal==='movement'&&<Modal title="Registrar movimiento de inventario (demostración)" onClose={()=>setModal(null)}><form onSubmit={submitMovement}><div className="form-grid"><FormField label="Movimiento"><select name="type" className="form-control"><option>Ingreso</option><option>Egreso</option></select></FormField><FormField label="Artículo"><select name="item" className="form-control">{demo.items.map(i=><option value={i.id} key={i.id}>{i.name} ({i.stock})</option>)}</select></FormField><FormField label="Cantidad"><input className="form-control" name="qty" type="number" min="1" step="1" required defaultValue="2"/></FormField><FormField label="Obra destino (obligatoria para egreso)"><select className="form-control" name="work"><option value="">Sin obra</option>{demo.works.filter(w=>w.status!=='Finalizada').map(w=><option key={w.id} value={w.id}>{w.id} · {w.name}</option>)}</select></FormField></div><div className="test-banner">Los egresos se valorizarán al precio de lista. La operación solo afecta los datos de esta sesión.</div><div className="modal-footer"><button className="btn ghost" type="button" onClick={()=>setModal(null)}>Cancelar</button><button className="btn primary">Confirmar movimiento</button></div></form></Modal>}
  </>;
}

export function Purchases({ demo, role, registerPurchase }) {
  const canWrite=['Administrador General','Bodega / Logística'].includes(role);
  const [open,setOpen]=useState(false);
  const [form,setForm]=useState({item:demo.items[0].id,qty:5,cost:100000,d1:10,d2:5,d3:2});
  const net=Number(form.cost)*[form.d1,form.d2,form.d3].reduce((a,d)=>a*(1-Number(d)/100),1);
  function submit(e){e.preventDefault();if(registerPurchase(form))setOpen(false);}
  return <><DemoNotice/><PageHeading title="Compras y abastecimiento" description="Recepción de materiales con descuentos comerciales sucesivos." actions={canWrite&&<button className="btn primary" onClick={()=>setOpen(true)}>+ Registrar compra</button>}/>
    <div className="stat-grid"><Stat title="Proveedores" value="3" meta="Referenciales" icon="♙"/><Stat title="Artículos en catálogo" value={demo.items.length} meta="Datos de ejemplo" icon="▣" accent="#15a57a"/><Stat title="Descuentos permitidos" value="3" meta="Aplicación en cascada" icon="%" accent="#e69a20"/><Stat title="Costo compra actual" value={money(form.cost)} meta="Para cálculo en el formulario" icon="$" accent="#8f71e9"/></div>
    <div className="grid-2 equal"><DataCard title="Regla de descuentos" sub="Se aplica cada descuento sobre el saldo restante"><p className="helper">Costo neto = costo base × (1 − D1) × (1 − D2) × (1 − D3).</p><div className="test-banner">Ejemplo: $10.000 con 10 %, 5 % y 2 % de descuentos sucesivos da <b>$8.379</b>, no $8.300.</div></DataCard><DataCard title="Impacto sobre inventario" sub="Recepción de compra"><p className="helper">Cuando registras una compra simulada, el catálogo incrementa el stock y crea un movimiento de ingreso en el Cardex temporal.</p></DataCard></div>
    {open&&<Modal title="Registrar compra con descuentos" onClose={()=>setOpen(false)}><form onSubmit={submit}><div className="form-grid"><FormField label="Artículo" full><select className="form-control" value={form.item} onChange={e=>setForm({...form,item:e.target.value})}>{demo.items.map(i=><option key={i.id} value={i.id}>{i.name}</option>)}</select></FormField>{[['qty','Cantidad'],['cost','Costo unitario base'],['d1','Descuento 1 (%)'],['d2','Descuento 2 (%)'],['d3','Descuento 3 (%)']].map(([k,label])=><FormField key={k} label={label}><input className="form-control" type="number" required min={k.startsWith('d')?0:1} max={k.startsWith('d')?99:undefined} step={k.startsWith('d')?0.1:1} value={form[k]} onChange={e=>setForm({...form,[k]:e.target.value})}/></FormField>)}</div><div className="test-banner"><b>Costo neto unitario:</b> {money(net)}<br/><b>Total compra:</b> {money(net*Number(form.qty))}</div><div className="modal-footer"><button type="button" className="btn ghost" onClick={()=>setOpen(false)}>Cancelar</button><button className="btn primary">Ingresar compra</button></div></form></Modal>}
  </>;
}

export function Works({ demo, role, createWork, startWork, finishWork }) {
  const editor=['Administrador General','Supervisor de Obras'].includes(role);
  const [modal,setModal]=useState(null);
  const selected=demo.works.find(w=>w.id===modal?.id);
  function submit(e){e.preventDefault();if(createWork(Object.fromEntries(new FormData(e.currentTarget))))setModal(null);}
  return <><DemoNotice/><PageHeading title="Obras y Técnicos" description="Gestión de obras, asignación de responsables y cierre controlado." actions={editor&&<button className="btn primary" onClick={()=>setModal({type:'create'})}>+ Crear obra</button>}/>
    <div className="stat-grid"><Stat title="Obras registradas" value={demo.works.length} meta="Registros simulados" icon="♧"/><Stat title="En ejecución" value={demo.works.filter(w=>w.status==='En curso').length} meta="Trabajos activos" icon="◷" accent="#13a277"/><Stat title="Pendientes revisión" value={demo.works.filter(w=>w.status==='Pendiente revisión').length} meta="Requieren conformidad" icon="!" accent="#d49c25"/><Stat title="Finalizadas" value={demo.works.filter(w=>w.status==='Finalizada').length} meta="Cierre de ejemplo" icon="✓" accent="#8566d9"/></div>
    <div className="card-grid">{demo.works.map(w=><div className="work-card" key={w.id}><div className="actions" style={{justifyContent:'space-between'}}><b className="eyebrow">{w.id}</b><Tag value={w.status}/></div><h3>{w.name}</h3><p className="helper">{w.client}<br/>{w.city} · {w.technician}</p><div className="actions" style={{marginTop:'auto',justifyContent:'space-between'}}><span className="muted">{nfmt(w.hours)} h registradas</span><button className="btn tiny subtle" onClick={()=>setModal({type:'view',id:w.id})}>Ver detalle</button></div></div>)}</div>
    {modal?.type==='create'&&<Modal title="Crear obra (demostración)" onClose={()=>setModal(null)}><form onSubmit={submit}><div className="form-grid"><FormField full label="Nombre de la obra"><input className="form-control" name="name" required maxLength="80" placeholder="Ej. Reparación cámara de frío"/></FormField><FormField label="Cliente"><input className="form-control" name="client" defaultValue="Frutícola Ñuble" required/></FormField><FormField label="Ubicación"><input className="form-control" name="city" defaultValue="Chillán" required/></FormField><FormField full label="Técnico asignado"><select name="technician" className="form-control"><option>Juan Pérez</option><option>María González</option></select></FormField></div><div className="modal-footer"><button type="button" className="btn ghost" onClick={()=>setModal(null)}>Cancelar</button><button className="btn primary">Crear obra</button></div></form></Modal>}
    {selected&&modal?.type==='view'&&<Modal wide title={`${selected.id} · ${selected.name}`} onClose={()=>setModal(null)}><div className="actions" style={{justifyContent:'space-between'}}><span className="eyebrow">{selected.client} · {selected.city}</span><Tag value={selected.status}/></div>
      <div className="stat-grid section-gap" style={{gridTemplateColumns:'repeat(3,minmax(0,1fr))'}}><Stat title="Horas" value={`${nfmt(selected.hours)} h`} meta="Registradas"/><Stat title="Materiales" value={selected.usage.filter(u=>!u.reversed).length} meta="Egresos" accent="#159d78"/><Stat title="Costo imputado" value={money(costWork(selected))} meta="Referencial" accent="#d89a28"/></div>
      <div className="test-banner">{selected.description||'Sin descripción de actividades guardada.'}</div><h3>Condiciones de cierre de la demo</h3>
      {[['Técnico asignado',!!selected.technician],['Horas registradas',selected.hours>0],['Fotografías',selected.photos.length>0],['Firma del cliente',!!selected.signature]].map(([label,ok])=><div className="list-row" key={label}><span style={{color:ok?'#0c9b6b':'#cc8130'}}>{ok?'✓':'○'}</span><div className="flex-grow"><strong>{label}</strong></div><Tag value={ok?'Disponible':'Pendiente'}/></div>)}
      <div className="modal-footer">{editor&&selected.status==='Pendiente'&&<button className="btn subtle" onClick={()=>startWork(selected.id)}>Iniciar obra</button>}{editor&&selected.status!=='Finalizada'&&<button className="btn primary" onClick={()=>{if(finishWork(selected.id))setModal(null);}}>Finalizar obra</button>}<button className="btn ghost" onClick={()=>setModal(null)}>Cerrar</button></div></Modal>}
  </>;
}

export function Finance({ demo, role, payInvoice }) {
  const canWrite=['Administrador General','Administración / Finanzas'].includes(role);
  const pending=demo.invoices.filter(i=>i.status==='Pendiente');
  return <><DemoNotice/><PageHeading title="Clientes y Finanzas" description="Consulta de cobros y facturación ilustrativa de FYAG."/>
    <div className="stat-grid"><Stat title="Facturas registradas" value={demo.invoices.length} meta="Datos de ejemplo"/><Stat title="Facturas pendientes" value={pending.length} meta="Por cobrar" accent="#e5a12c"/><Stat title="Pendiente de pago" value={money(pending.reduce((a,b)=>a+b.amount,0))} meta="Saldo ilustrativo" accent="#856de5"/><Stat title="Facturas pagadas" value={demo.invoices.filter(x=>x.status==='Pagada').length} meta="Conciliadas" accent="#13a277"/></div>
    <div className="card"><h3>Facturas y cobranza</h3><p className="card-sub">Los registros son exclusivamente demostrativos.</p><div className="table-wrap"><table className="data-table"><thead><tr><th>Número</th><th>Cliente</th><th>Total</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>{demo.invoices.map(i=><tr key={i.id}><td><b>{i.id}</b></td><td>{i.client}</td><td>{money(i.amount)}</td><td><Tag value={i.status}/></td><td>{canWrite&&i.status==='Pendiente'?<button className="btn tiny subtle" onClick={()=>payInvoice(i.id)}>Marcar pagada</button>:'—'}</td></tr>)}</tbody></table></div></div>
  </>;
}

export function Reports({ demo }) {
  const [filter,setFilter]=useState('Todo');
  const movements=demo.movements.filter(m=>filter==='Todo'||m.type===filter);
  return <><DemoNotice/><PageHeading title="Reportes y trazabilidad" description="Indicadores operativos basados en los datos de esta sesión." actions={<button className="btn ghost" onClick={()=>window.print()}>▤ Imprimir / PDF</button>}/>
    <div className="stat-grid"><Stat title="Movimientos de inventario" value={demo.movements.length} meta="Movimientos históricos"/><Stat title="Obras" value={demo.works.length} meta="Registradas" accent="#12a278"/><Stat title="Horas imputadas" value={`${nfmt(demo.works.reduce((a,w)=>a+w.hours,0))} h`} meta="Hoja de servicio" accent="#dca02c"/><Stat title="Costos de obras" value={money(demo.works.reduce((a,w)=>a+costWork(w),0))} meta="Valores de referencia" accent="#8466e1"/></div>
    <div className="grid-2"><DataCard title="Historial del Cardex" sub="Puedes filtrar los movimientos"><div className="toolbar"><select className="form-control" style={{maxWidth:180}} value={filter} onChange={e=>setFilter(e.target.value)}>{['Todo','Ingreso','Egreso','Reversa'].map(v=><option key={v}>{v}</option>)}</select></div>{movements.map(m=><div className="list-row" key={m.id}><span className="row-icon">↔</span><div className="flex-grow"><strong>{toItem(demo.items,m.itemId)?.name}</strong><small>{m.id} · {m.date}</small></div><span className={m.qty>0?'amount plus':'amount minus'}>{m.qty>0?'+':''}{m.qty}</span></div>)}{!movements.length&&<div className="empty">No hay registros.</div>}</DataCard><DataCard title="Trazabilidad por obra" sub="Horas y materiales valorizados">{demo.works.map(w=><div className="list-row" key={w.id}><div className="flex-grow"><strong>{w.name}</strong><small>{w.id} · {w.hours} horas registradas</small></div><span className="amount">{money(costWork(w))}</span></div>)}</DataCard></div>
  </>;
}
