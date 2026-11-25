import assert from 'node:assert/strict';
import { ACCESS, ROLES, NORMALIZE_ROLE, money, seed, nextId, costWork } from '../src/data.js';
import { login, getRoles, getUsers, createUser, editUser, listResult } from '../src/api.js';

const demo = seed();
assert.equal(demo.items.length, 8);
assert.equal(demo.works.length, 3);
assert.equal(demo.movements.length, 3);
assert.equal(demo.items.reduce((s,i)=>s+i.stock,0), 595);
assert.equal(money(8379),'$ 8.379');
assert.equal(nextId('OB-',demo.works),'OB-0033');
assert.equal(costWork(demo.works[0]),0);
assert.equal(ROLES.length,6);
assert.equal(NORMALIZE_ROLE.Técnico,'Técnico en Terreno');
assert.equal(ACCESS.Consulta.includes('inventory'),false);
assert.equal(10000 * 0.9 * 0.95 * 0.98,8379); // JS exact in this instance

const savedFetch=globalThis.fetch;
const captures=[];
globalThis.fetch=async (path,opt)=>{
  captures.push({path,opt});
  const success={
    '/api/auth/login/':{access:'access-test',refresh:'refresh-test',nombre_rol:'Administrador General',id_usuario:5},
    '/api/usuarios/':[{id_usuario:5,username:'admin',nombre_rol:'Administrador General'}],
    '/api/roles/':[{id_rol:1,nombre_rol:'Administrador General'}],
    '/api/usuarios/5/':{id_usuario:5,username:'admin',estado_activo:true}
  };
  const status=opt.method==='POST'&&path==='/api/usuarios/'?201:200;
  return {ok:true,status,text:async()=>JSON.stringify(success[path]||{})};
};
try {
  const authResponse=await login('admin','secreta');
  assert.equal(authResponse.nombre_rol,'Administrador General');
  const auth={access:authResponse.access,refresh:authResponse.refresh};
  const users=await getUsers(auth,()=>{});assert.equal(listResult(users).length,1);
  const roles=await getRoles(auth,()=>{});assert.equal(listResult(roles).length,1);
  await createUser({username:'demo',rol:1,password:'Abc123!!'},auth,()=>{});
  await editUser(5,{estado_activo:true},auth,()=>{});
  assert.equal(captures.length,5);
  assert.equal(captures[1].opt.headers.Authorization,'Bearer access-test');
  assert.equal(captures[3].opt.method,'POST');
  assert.equal(captures[4].opt.method,'PATCH');
  console.log('OK: seeds/roles/cálculos y contratos HTTP de Django (mock)');
} finally {globalThis.fetch=savedFetch;}
