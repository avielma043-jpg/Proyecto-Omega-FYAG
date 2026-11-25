import React, { useState } from 'react';
import { PageHeading, Tag, DataCard, FormField, Modal } from './ui';
import { createUser, editUser } from './api';

export default function Users({ auth, users, roles, loading, error, refreshUsers, changeAuth, toast, expireSession }) {
  const [search,setSearch]=useState('');
  const [selected,setSelected]=useState(null);
  const [saving,setSaving]=useState(false);
  const [submitError,setSubmitError]=useState('');
  const allowedRoles=roles.filter(r=>auth?.nombre_rol==='Administrador General'||r.nombre_rol!=='Administrador General');
  const filtered=users.filter(u=>`${u.username} ${u.first_name} ${u.last_name} ${u.rut} ${u.nombre_rol}`.toLowerCase().includes(search.toLowerCase()));
  const create=selected?.type==='create';
  const editing=selected?.type==='edit';
  const item=editing?users.find(u=>String(u.id_usuario)===String(selected.id)):null;

  async function submit(e) {
    e.preventDefault();
    const form=new FormData(e.currentTarget);
    const payload={
      first_name:String(form.get('first_name')||'').trim(),
      last_name:String(form.get('last_name')||'').trim(),
      email:String(form.get('email')||'').trim(),
      rol:Number(form.get('rol')),
      estado_activo:form.get('estado_activo')==='true'
    };
    if (create) {
      payload.username=String(form.get('username')||'').trim();
      payload.rut=String(form.get('rut')||'').trim();
    }
    const password=String(form.get('password')||'');
    if(password)payload.password=password;
    if(create&&!password){setSubmitError('Debes establecer una contraseña para crear el usuario.');return;}
    setSaving(true);setSubmitError('');
    try {
      if(create)await createUser(payload,auth,changeAuth);
      else await editUser(item.id_usuario,payload,auth,changeAuth);
      setSelected(null);
      toast(create?'Usuario creado en Django.':'Usuario actualizado en Django.');
      await refreshUsers();
    } catch (err) {
      setSubmitError(err.message);
      if(/sesión ha vencido/i.test(err.message))expireSession();
    } finally {setSaving(false);}
  }
  return <>
    <div className="real-only-note"><b>Módulo conectado a Django:</b> los datos que consultes o guardes aquí sí afectan a la base de datos configurada en el backend. Utiliza cuentas de prueba.</div>
    <PageHeading title="Usuarios, roles y seguridad" description="Administración de usuarios mediante la API REST de Django y controles RBAC." actions={<>
      <button className="btn ghost" onClick={refreshUsers} disabled={loading}>↻ Actualizar</button>
      <button className="btn primary" onClick={()=>{setSelected({type:'create'});setSubmitError('')}} disabled={loading||!roles.length}>+ Crear usuario</button>
    </>}/>
    <div className="card"><div className="toolbar"><input className="form-control search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Buscar por usuario, RUT o rol" aria-label="Buscar usuarios"/><span className="helper">{users.length} usuarios registrados</span></div>
      {loading&&<div className="test-banner">Consultando usuarios y roles a Django…</div>}
      {error&&<div className="error-banner">{error}</div>}
      <div className="table-wrap"><table className="data-table"><thead><tr><th>Usuario</th><th>RUT</th><th>Email</th><th>Perfil</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>{filtered.map(u=><tr key={u.id_usuario}><td><b>{u.username}</b><small>{`${u.first_name||''} ${u.last_name||''}`.trim()||'Sin nombre'}</small></td><td>{u.rut}</td><td>{u.email||'—'}</td><td>{u.nombre_rol||'—'}</td><td><Tag value={u.estado_activo?'Activo':'Inactivo'}/></td><td><button className="btn tiny subtle" onClick={()=>{setSelected({type:'edit',id:u.id_usuario});setSubmitError('')}}>Editar</button></td></tr>)}</tbody></table></div>
      {!loading&&!filtered.length&&<div className="empty">No hay usuarios para mostrar.</div>}
    </div>
    <div className="grid-2 equal section-gap"><DataCard title="Control de acceso basado en roles" sub="Permisos del servidor"><p className="helper">La API solo permite gestionar usuarios a Administración o Administrador General. El perfil Administración no puede asignar Administrador General.</p></DataCard><DataCard title="Registro de auditoría" sub="Disponible en el modelo Django"><p className="helper">Al crear o editar usuarios, el backend registra operaciones en su tabla LogAuditoria. El ZIP actual no expone todavía un endpoint para visualizar esos registros.</p></DataCard></div>
    {(create||editing)&&<Modal title={create?'Crear usuario real en Django':`Editar usuario · ${item?.username||''}`} onClose={()=>{if(!saving)setSelected(null)}}>
      <form onSubmit={submit} key={create?'new':item?.id_usuario}>
        <div className="form-grid">
          <FormField label="Usuario"><input className="form-control" name="username" defaultValue={item?.username||''} disabled={editing} required maxLength={150}/></FormField>
          <FormField label="RUT"><input className="form-control" name="rut" defaultValue={item?.rut||''} disabled={editing} required maxLength={12}/></FormField>
          <FormField label="Nombre"><input className="form-control" name="first_name" defaultValue={item?.first_name||''} maxLength={150}/></FormField>
          <FormField label="Apellido"><input className="form-control" name="last_name" defaultValue={item?.last_name||''} maxLength={150}/></FormField>
          <FormField label="Correo electrónico" full><input className="form-control" name="email" type="email" defaultValue={item?.email||''}/></FormField>
          <FormField label="Rol"><select className="form-control" name="rol" required defaultValue={item?.rol||allowedRoles[0]?.id_rol||''}>{allowedRoles.map(r=><option key={r.id_rol} value={r.id_rol}>{r.nombre_rol}</option>)}</select></FormField>
          <FormField label="Estado"><select className="form-control" name="estado_activo" defaultValue={String(item?.estado_activo??true)}><option value="true">Activo</option><option value="false">Inactivo</option></select></FormField>
          <FormField label={create?'Contraseña inicial':'Nueva contraseña (opcional)'} full><input type="password" className="form-control" name="password" autoComplete="new-password" required={create} minLength={8}/></FormField>
        </div>
        {submitError&&<div className="error-banner" role="alert">{submitError}</div>}
        <div className="modal-footer"><button type="button" className="btn ghost" disabled={saving} onClick={()=>setSelected(null)}>Cancelar</button><button className="btn primary" disabled={saving}>{saving?'Guardando…':create?'Crear usuario':'Guardar cambios'}</button></div>
      </form>
    </Modal>}
  </>;
}
