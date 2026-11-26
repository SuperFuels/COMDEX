const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');
const file=path.resolve(__dirname,'../../../pages/api/iq/[...path].ts');
const compiled=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const m={exports:{}};new Function('module','exports','require',compiled)(m,m.exports,require);
const handler=m.exports.default;
function response(){return {statusCode:200,headers:{},setHeader(k,v){this.headers[k]=v;return this;},status(v){this.statusCode=v;return this;},json(v){this.body=v;return this;},send(v){this.body=v;return this;},end(){return this;}};}
test('gateway gates configuration, origin, paths and forwards only the IQ cookie',async()=>{
 const vars=['IQ_SHARED_DEMO_ENABLED','IQ_BACKEND_URL','IQ_PROXY_KEY','IQ_PUBLIC_ORIGIN','VERCEL'];const original=Object.fromEntries(vars.map(k=>[k,process.env[k]]));const oldFetch=global.fetch;
 try{
  const req={method:'GET',query:{path:['wallet']},headers:{},cookies:{'__Host-iq_demo':'demo_token','unrelated':'secret'},socket:{remoteAddress:'127.0.0.1'}};
  process.env.IQ_SHARED_DEMO_ENABLED='false';let res=response();await handler(req,res);assert.equal(res.statusCode,503);
  Object.assign(process.env,{IQ_SHARED_DEMO_ENABLED:'true',IQ_BACKEND_URL:'https://backend.example',IQ_PROXY_KEY:'test-key',IQ_PUBLIC_ORIGIN:'https://tessaris.ai'});
  let calls=0;global.fetch=async(url,options)=>{calls++;assert.equal(url,'https://backend.example/api/iq/wallet');assert.equal(options.headers.Cookie,'__Host-iq_demo=demo_token');assert.equal(options.headers['X-IQ-Proxy-Key'],'test-key');return new Response('{"ok":true}',{headers:{'content-type':'application/json'}});};
  res=response();await handler(req,res);assert.equal(res.statusCode,200);assert.equal(calls,1);
  res=response();await handler({...req,method:'POST',headers:{origin:'https://evil.example'}},res);assert.equal(res.statusCode,403);assert.equal(calls,1);
  res=response();await handler({...req,query:{path:['..','wallet']}},res);assert.equal(res.statusCode,400);
  process.env.IQ_BACKEND_URL='http://backend.example';res=response();await handler(req,res);assert.equal(res.statusCode,503);
  process.env.IQ_BACKEND_URL='not a url';res=response();await handler(req,res);assert.equal(res.statusCode,503);
 }finally{global.fetch=oldFetch;for(const k of vars){if(original[k]===undefined)delete process.env[k];else process.env[k]=original[k];}}
});
test('legacy API rewrite excludes the shared IQ gateway',async()=>{
 const old=process.env.FASTAPI_ORIGIN;process.env.FASTAPI_ORIGIN='https://legacy.example';
 try{const config=require('../../../next.config.js');const routes=await config.rewrites();const legacy=routes.find(r=>r.destination==='https://legacy.example/api/:path*');const {pathToRegexp}=require('next/dist/compiled/path-to-regexp');const pattern=pathToRegexp(legacy.source);assert.equal(pattern.test('/api/iq/wallet'),false);assert.equal(pattern.test('/api/iq/session'),false);assert.equal(pattern.test('/api/iq-connection'),false);assert.equal(pattern.test('/api/other/test'),true);}finally{if(old===undefined)delete process.env.FASTAPI_ORIGIN;else process.env.FASTAPI_ORIGIN=old;}
});
