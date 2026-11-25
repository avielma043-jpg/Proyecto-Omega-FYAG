export const ROLES=['Administrador General','Administración / Finanzas','Bodega / Logística','Supervisor de Obras','Técnico en Terreno','Consulta'];
export const LINKS=[{id:'dashboard',label:'Inicio',icon:'⌂'},{id:'inventory',label:'Inventario y Cardex',icon:'▣'},{id:'purchases',label:'Compras',icon:'▤'},{id:'works',label:'Obras y Técnicos',icon:'♧'},{id:'finance',label:'Clientes y Finanzas',icon:'▥'},{id:'reports',label:'Reportes',icon:'▥'},{id:'security',label:'Usuarios y Seguridad',icon:'♙'}];
export const ACCESS={
 'Administrador General':['dashboard','inventory','purchases','works','finance','reports','security'],
 'Administración / Finanzas':['dashboard','purchases','works','finance','reports','security'],
 'Bodega / Logística':['dashboard','inventory','purchases','works','reports'],
 'Supervisor de Obras':['dashboard','inventory','works','reports'],
 'Técnico en Terreno':[],
 'Consulta':['dashboard','reports']
};
export const ITEMS_SEED=[
 {id:'ART-001',name:'Filtro secador',category:'Refrigeración',stock:28,min:10,price:45000,cost:26000},
 {id:'ART-002',name:'Refrigerante R134a',category:'Refrigeración',stock:32,min:12,price:120000,cost:81500},
 {id:'ART-003',name:'Válvula solenoide',category:'Refrigeración',stock:18,min:8,price:68000,cost:41800},
 {id:'ART-004',name:'Compresor industrial',category:'Equipos',stock:8,min:10,price:445000,cost:310000},
 {id:'ART-005',name:'Cable eléctrico 2,5 mm',category:'Electricidad',stock:95,min:30,price:2600,cost:1500},
 {id:'ART-006',name:'Sensor de temperatura',category:'Instrumentación',stock:14,min:8,price:38500,cost:23200},
 {id:'ART-007',name:'Tubería de cobre (m)',category:'Materiales',stock:350,min:60,price:6900,cost:4250},
 {id:'ART-008',name:'Aceite para compresor',category:'Refrigeración',stock:50,min:18,price:18000,cost:9800}
];
export const WORKS_SEED=[
 {id:'OB-0032',name:'Mantención cámara de frío',client:'Frutícola Ñuble',city:'Chillán',status:'En curso',technician:'Juan Pérez',hours:0,description:'',usage:[],photos:[],signature:null},
 {id:'OB-0031',name:'Instalación eléctrica',client:'Agroindustrial del Sur',city:'Bulnes',status:'Pendiente',technician:'Juan Pérez',hours:0,description:'',usage:[],photos:[],signature:null},
 {id:'OB-0028',name:'Reparación de compresor',client:'Transportes Central',city:'San Carlos',status:'Finalizada',technician:'María González',hours:4,description:'Mantenimiento preventivo realizado.',usage:[],photos:[],signature:'demo',signatureLabel:'Firmada'}
];
export function seed(){return {loggedIn:false,role:'Administrador General',nav:'dashboard',mode:'erp',tab:'items',modal:null,selectedWork:'OB-0032',techTab:'works',search:'',filter:'Todos',items:structuredClone(ITEMS_SEED),works:structuredClone(WORKS_SEED),movements:[{id:'MOV-0081',itemId:'ART-001',qty:12,type:'Ingreso',workId:null,user:'Bodega / Logística',date:'09/11/2026 09:12',price:45000,reversalOf:null},{id:'MOV-0082',itemId:'ART-002',qty:-3,type:'Egreso',workId:'OB-0028',user:'Bodega / Logística',date:'09/11/2026 11:47',price:120000,reversalOf:null},{id:'MOV-0083',itemId:'ART-007',qty:20,type:'Ingreso',workId:null,user:'Bodega / Logística',date:'10/11/2026 10:25',price:6900,reversalOf:null}], invoices:[{id:'FAC-0102',client:'Frutícola Ñuble',amount:1250000,status:'Pendiente'},{id:'FAC-0101',client:'Agroindustrial del Sur',amount:875000,status:'Pagada'},{id:'FAC-0100',client:'Transportes Central',amount:490000,status:'Pendiente'}],activities:[],purchasePreview:0,reportFilter:'Todo'};}

export const NORMALIZE_ROLE={
 'Administrador General':'Administrador General',
 'Administración':'Administración / Finanzas',
 'Bodega/Logística':'Bodega / Logística',
 'Supervisor de Obras':'Supervisor de Obras',
 'Técnico':'Técnico en Terreno',
 'Consulta':'Consulta'
};
export const money=n=>'$ '+Math.round(Number(n)||0).toLocaleString('es-CL');
export const nfmt=n=>Number(n||0).toLocaleString('es-CL');
export const dateNow=()=>new Date().toLocaleString('es-CL',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'});
export const nextId=(prefix,arr)=>prefix+String(Math.max(0,...arr.map(x=>Number((x.id||'').split('-').pop())||0))+1).padStart(4,'0');
export const costWork=w=>w.usage.filter(u=>!u.reversed).reduce((sum,u)=>sum+u.qty*u.price,0)+w.hours*18000;
