import test from 'node:test';
import assert from 'node:assert/strict';
import {IQLedgerClient,IQPendingAction} from '../iq-client.mjs';
const response=(data,status=200)=>({ok:status<400,status,json:async()=>data});
test('requires simulated IQ and disabled cash operations',async()=>{
 const client=new IQLedgerClient({fetcher:async()=>response({asset:'IQ',simulated:false})});
 await assert.rejects(client.rules(),/requires a simulated/);
});
test('never substitutes a local balance for an unavailable service',async()=>{
 const client=new IQLedgerClient({fetcher:async()=>({ok:false,json:async()=>{throw Error('HTML');}})});
 await assert.rejects(client.wallet(),/unavailable/);
});
test('server selects account identity; transfer contains no sender',async()=>{
 let captured;
 const client=new IQLedgerClient({fetcher:async(url,options)=>{captured={url,options};return response({ok:true});}});
 await client.transfer('bob',1200,'stable-request');
 assert.equal(captured.url,'/api/iq/transfers');
 assert.deepEqual(JSON.parse(captured.options.body),{recipient:'bob',amount_units:1200,idempotency_key:'stable-request'});
 assert.equal(captured.options.credentials,'same-origin');
});
test('uncertain action keeps its original retry key and payload',async()=>{
 const calls=[];let first=true;
 const action=new IQPendingAction(async body=>{calls.push(body);if(first){first=false;throw Error('lost response');}return {done:true};},{key:'same-key',amount_units:100});
 await assert.rejects(action.confirm());
 assert.deepEqual(await action.confirm(),{done:true});
 assert.deepEqual(await action.confirm(),{done:true});
 assert.deepEqual(calls,[{key:'same-key',amount_units:100},{key:'same-key',amount_units:100}]);
});
test('blocks duplicate clicks while a request is in flight',async()=>{
 let release;const action=new IQPendingAction(()=>new Promise(resolve=>{release=resolve;}),{key:'a'});
 const first=action.confirm();await assert.rejects(action.confirm(),/already/);release({done:true});await first;
});
