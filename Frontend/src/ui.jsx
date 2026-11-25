import React from 'react';
import { money } from './data';

export function Brand({ dark = true }) {
  return <div className={`logo ${dark ? 'on-dark' : ''}`}>
    <div className="logo-symbol" aria-hidden="true">❄</div>
    <div><strong>PROYECTO<br/>OMEGA</strong><small>SISTEMA ERP · FYAG</small></div>
  </div>;
}
export function Tag({ value }) {
  const colors = { 'En curso':'green', 'Finalizada':'blue', 'Pendiente':'orange', 'Pendiente revisión':'orange',
    'Pagada':'green', 'Crítico':'red', 'Bajo':'orange', 'Disponible':'green', 'Activo':'green', 'Inactivo':'red' };
  return <span className={`tag ${colors[value] || 'gray'}`}>{value}</span>;
}
export function Stat({ title, value, meta, icon='▣', accent='#377ce9', tint='#edf5ff' }) {
  return <div className="card metric-card" style={{ '--accent':accent, '--tint':tint }}>
    <div className="metric-top"><span>{title}</span><span className="metric-icon" aria-hidden="true">{icon}</span></div>
    <div className="metric-value">{value}</div><div className="metric-meta">{meta}</div>
  </div>;
}
export function PageHeading({ title, description, actions }) {
  return <div className="page-head"><div><div className="eyebrow">PROYECTO OMEGA / DEMOSTRACIÓN</div>
    <h2 className="page-title">{title}</h2><div className="page-description">{description}</div></div>
    <div className="page-actions">{actions}</div></div>;
}
export function DemoNotice() {
  return <div className="demo-alert"><strong>Sección demostrativa:</strong> los datos y cambios de este módulo son locales; el backend actual solo ofrece autenticación, roles y usuarios.</div>;
}
export function Modal({ title, children, onClose, wide = false }) {
  return <div className="overlay" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget)onClose();}}>
    <div className={`modal ${wide?'wide':''}`} role="dialog" aria-modal="true" aria-label={title}>
      <div className="modal-header"><h2>{title}</h2><button className="close" type="button" aria-label="Cerrar" onClick={onClose}>×</button></div>
      {children}
    </div>
  </div>;
}
export function FormField({ label, children, full=false }) { return <div className={`form-field ${full?'full':''}`}><label>{label}</label>{children}</div>; }
export function DataCard({ title, sub, children }) { return <div className="card"><h3>{title}</h3>{sub&&<p className="card-sub">{sub}</p>}{children}</div>; }
export function InlineCard({ label, number, note }) { return <div className="card"><div className="eyebrow">{label}</div><h3 className="numbers">{number}</h3><div className="page-description">{note}</div></div>; }
export { money };
