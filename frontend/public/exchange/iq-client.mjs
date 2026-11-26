/** Transport for the IQ ledger API. No browser balance mutations or simulated fallback.
 * The host owns session authentication. Bearer injection is for the local test app;
 * deployed same-origin sessions should use HttpOnly cookies. Never persist a token.
 */
export class IQLedgerClient {
  constructor({base='/api/iq',fetcher=globalThis.fetch,token=null}={}) {
    this.base=base.replace(/\/$/,''); this.fetcher=fetcher.bind(globalThis); this.token=token;
  }
  async request(path,{body,signal}={}) {
    const response=await this.fetcher(this.base+path,{
      method:body===undefined?'GET':'POST',credentials:'same-origin',cache:'no-store',signal,
      headers:{Accept:'application/json',...(body===undefined?{}:{'Content-Type':'application/json'}),...(this.token?{Authorization:`Bearer ${this.token}`}:{})},
      ...(body===undefined?{}:{body:JSON.stringify(body)})
    });
    let result;
    try { result=await response.json(); }
    catch { throw new Error('The connected IQ service is unavailable. No local balance was changed.'); }
    if(!response.ok) {
      const error=new Error(typeof result.detail==='string'?result.detail.replaceAll('_',' '):'The IQ service could not accept this request.');
      error.status=response.status; error.definitive=response.status>=400&&response.status<500;
      throw error;
    }
    return result;
  }
  async rules() {
    const rules=await this.request('/rules');
    if(rules.asset!=='IQ'||rules.simulated!==true||rules.production_issuance_enabled!==false||rules.cash_redemption_enabled!==false)
      throw new Error('This exchange requires a simulated IQ service with cash operations disabled.');
    return rules;
  }
  async wallet() {
    const wallet=await this.request('/wallet');
    if(wallet.asset!=='IQ'||wallet.simulated!==true||wallet.units_per_iq!==100)
      throw new Error('The wallet is not a compatible simulated IQ account.');
    return wallet;
  }
  markets(){return this.request('/markets');}
  market(id){return this.request('/markets/'+encodeURIComponent(id));}
  preview(id,order){return this.request('/markets/'+encodeURIComponent(id)+'/preview',{body:order});}
  order(id,order){return this.request('/markets/'+encodeURIComponent(id)+'/orders',{body:order});}
  cancel(id,key){return this.request('/orders/'+encodeURIComponent(id)+'/cancel',{body:{key}});}
  transfer(recipient,amount_units,idempotency_key){return this.request('/transfers',{body:{recipient,amount_units,idempotency_key}});}
  briefs(){return this.request('/research');}
  fundBrief(brief_id,budget_units,key){return this.request('/research',{body:{brief_id,budget_units,key}});}
  payResponse(brief,body){return this.request('/research/'+encodeURIComponent(brief)+'/awards',{body});}
  closeBrief(brief,key){return this.request('/research/'+encodeURIComponent(brief)+'/close',{body:{key}});}
  operations(){return this.request('/operations');}
}

/** Retains the exact request until its result is established. It never retries
 * with a fresh ID after a timeout, and does not optimistically edit balances.
 */
export class IQPendingAction {
  constructor(send,payload){this.send=send;this.payload=structuredClone(payload);this.pending=false;this.result=null;this.complete=false;}
  async confirm(){
    if(this.complete)return this.result;
    if(this.pending)throw new Error('This request is already being confirmed.');
    this.pending=true;
    try {this.result=await this.send(structuredClone(this.payload));this.complete=true;return this.result;}
    finally {this.pending=false;}
  }
}
