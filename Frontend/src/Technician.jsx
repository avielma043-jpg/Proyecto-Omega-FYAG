import React, { useEffect, useRef, useState } from 'react';
import { money, costWork } from './data';
import { Brand, Tag } from './ui';

function SignaturePad({ value, onSave, disabled }) {
  const canvasRef=useRef(null);
  const pointer=useRef(false);
  const hasDrawn=useRef(false);
  useEffect(()=>{
    const c=canvasRef.current;if(!c)return;
    const context=c.getContext('2d');
    context.clearRect(0,0,c.width,c.height);context.fillStyle='#fff';context.fillRect(0,0,c.width,c.height);
    context.lineWidth=3.2;context.strokeStyle='#182f4b';context.lineCap='round';context.lineJoin='round';
    if(value&&value!=='demo'){
      const img=new Image();img.onload=()=>{context.drawImage(img,0,0,c.width,c.height)};img.src=value;
    }
  },[value]);
  function point(e){const c=canvasRef.current,r=c.getBoundingClientRect();return {x:(e.clientX-r.left)*c.width/r.width,y:(e.clientY-r.top)*c.height/r.height}}
  function down(e){if(disabled)return;pointer.current=true;hasDrawn.current=false;e.currentTarget.setPointerCapture(e.pointerId);const p=point(e);const ctx=e.currentTarget.getContext('2d');ctx.beginPath();ctx.moveTo(p.x,p.y);e.preventDefault()}
  function move(e){if(!pointer.current||disabled)return;const p=point(e);const ctx=e.currentTarget.getContext('2d');ctx.lineTo(p.x,p.y);ctx.stroke();hasDrawn.current=true;e.preventDefault()}
  function up(e){if(!pointer.current||disabled)return;pointer.current=false;if(!hasDrawn.current){const p=point(e),ctx=e.currentTarget.getContext('2d');ctx.fillStyle='#172f4a';ctx.fillRect(p.x,p.y,2,2);}onSave(e.currentTarget.toDataURL('image/png'))}
  return <canvas ref={canvasRef} className="signature-pad" width={640} height={180} onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up} aria-label="Dibujar firma del cliente"/>;
}

export default function Technician({ demo, actions, toast, back, isReal }) {
  const [tab,setTab]=useState('works');
  const [workId,setWorkId]=useState('OB-0032');
  const [search,setSearch]=useState('');
  const w=demo.works.find(x=>x.id===workId)||demo.works[0];
  const locked=w?.status==='Finalizada';
  const [hours,setHours]=useState(String(w?.hours||0));
  const [description,setDescription]=useState(w?.description||'');
  useEffect(()=>{setHours(String(w?.hours||0));setDescription(w?.description||'')},[w?.id]);
  const assigned=demo.works.filter(x=>x.technician==='Juan Pérez'||x.id===workId);
  function chooseWork(id){setWorkId(id);setTab('service')}
  async function photoChanged(e){const file=e.target.files?.[0];if(!file)return;
    if(!file.type.startsWith('image/')){toast('Selecciona una imagen válida.',true);return}
    if(file.size>8*1024*1024){toast('La imagen debe pesar menos de 8 MB.',true);return}
    const reader=new FileReader();reader.onload=()=>actions.addPhoto(workId,{name:file.name,url:String(reader.result)});reader.readAsDataURL(file);e.target.value='';
  }
  return <div className="tech-bg"><div className="tech-shell"><div className="tech-shell-top"><div className="actions" style={{justifyContent:'space-between'}}><Brand/><button className="btn tiny ghost" onClick={back}>↩ ERP</button></div><h2>{({works:'Mis obras',service:'Hoja de servicio',materials:'Materiales y horas',evidence:'Fotografías y firma'})[tab]}</h2><small>Portal técnico · Datos de demostración</small></div>
    <div className="tech-shell-nav">{[['works','Mis obras'],['service','Servicio'],['materials','Materiales y horas'],['evidence','Evidencias']].map(([key,label])=><button key={key} className={tab===key?'active':''} onClick={()=>setTab(key)}>{label}</button>)}</div>
    <div className="tech-shell-body">
      {isReal&&<div className="test-banner">Autenticación JWT real; las obras y hojas de servicio continúan siendo simuladas.</div>}
      {tab==='works'&&<><p className="helper">Consulta los servicios asignados. Este listado es ilustrativo.</p><input className="form-control" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Buscar obra"/>
        {assigned.filter(x=>`${x.id} ${x.name}`.toLowerCase().includes(search.toLowerCase())).map(x=><button className="tech-work-item" key={x.id} onClick={()=>chooseWork(x.id)}><div><h3>{x.id} · {x.name}</h3><p>{x.city} · {x.client}</p></div><Tag value={x.status}/></button>)}
      </>}
      {tab==='service'&&w&&<><p className="mobile-meta"><b>{w.id} · {w.name}</b><br/>Cliente: {w.client}<br/>Estado: {w.status}</p><form className="mobile-form" onSubmit={e=>{e.preventDefault();if(actions.saveDescription(workId,description))setTab('materials')}}><div className="form-field"><label>Actividades realizadas</label><textarea className="form-control" value={description} onChange={e=>setDescription(e.target.value)} disabled={locked} placeholder="Describe el trabajo realizado…" required/></div><button className="btn primary" disabled={locked}>Guardar y continuar</button></form></>}
      {tab==='materials'&&w&&<><p className="mobile-meta"><b>{w.id} · {w.name}</b></p><h3>Materiales utilizados</h3><div className="stacked">{w.usage.filter(u=>!u.reversed).map((u,i)=><div className="list-row" key={i}><div className="flex-grow"><strong>{demo.items.find(x=>x.id===u.itemId)?.name}</strong><small>Valor lista: {money(u.price)} / unidad</small></div><b>{u.qty} uds.</b></div>)}{!w.usage.length&&<div className="helper">Aún no hay materiales imputados.</div>}</div>
        <form className="mobile-form" onSubmit={e=>{e.preventDefault();const v=new FormData(e.currentTarget);if(actions.addTechItem(workId,String(v.get('item')),Number(v.get('qty'))))e.currentTarget.reset()}}><div className="form-field"><label>Agregar artículo</label><select name="item" className="form-control" disabled={locked}>{demo.items.map(i=><option key={i.id} value={i.id}>{i.name} · {i.stock} disponibles</option>)}</select></div><div className="form-field"><label>Cantidad</label><input name="qty" type="number" className="form-control" min="1" step="1" required defaultValue="1" disabled={locked}/></div><button className="btn subtle" disabled={locked}>Registrar consumo (demo)</button></form>
        <form className="mobile-form section-gap" onSubmit={e=>{e.preventDefault();actions.saveHours(workId,Number(hours))}}><div className="form-field"><label>Horas trabajadas</label><input type="number" className="form-control" step="0.5" min="0" max="500" value={hours} onChange={e=>setHours(e.target.value)} disabled={locked}/></div><button className="btn primary" disabled={locked}>Guardar horas</button></form><div className="test-banner"><b>Costo imputado de referencia:</b> {money(costWork(w))}</div></>}
      {tab==='evidence'&&w&&<><h3>Fotografías del trabajo</h3><p className="helper">Adjunta evidencia fotográfica del servicio. Las fotos se mantienen solo en memoria.</p><input type="file" accept="image/*" className="form-control" onChange={photoChanged} disabled={locked}/><div className="picture-grid">{w.photos.map((p,i)=><img src={p.url} title={p.name} alt={`Evidencia ${i+1}: ${p.name}`} key={i}/>)}</div>
        <h3>Firma de conformidad</h3><p className="helper">Solicita al cliente que firme en el recuadro.</p><SignaturePad value={w.signature} onSave={data=>actions.saveSignature(workId,data)} disabled={locked}/><div className="actions section-gap"><button className="btn ghost sm" disabled={locked} onClick={()=>actions.saveSignature(workId,null)}>Limpiar firma</button>{w.signature&&<Tag value="Disponible"/>}</div>
        <button className="btn primary full section-gap" disabled={locked} onClick={()=>{if(actions.submitService(workId))setTab('works')}}>Enviar hoja de servicio para revisión</button></>}
      <div className="test-banner">Módulo frontend: al recargar la página se pierden todos los cambios de demostración.</div>
    </div></div></div>;
}
