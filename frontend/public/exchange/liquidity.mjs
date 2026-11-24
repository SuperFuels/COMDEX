import {bitcoinQuotes} from './bitcoin-pricing.mjs';
const bases={mks:51,aapl:64,tsco:58,nvda:72,energy:37};
export function marketSession(s,id){return id==='btc'?s.bitcoin:s.marketDepth?.[id];}
export function quoteFor(s,id,now=Date.now()){if(s.settled[id]?.lastQuote)return s.settled[id].lastQuote;if(id==='btc')return bitcoinQuotes(s.bitcoin,now);if(!(id in bases))throw Error('Unknown market.');const t=Math.floor((now-(s.quoteStart||now))/4000),phase=Object.keys(bases).indexOf(id)*2;const yes=Math.max(10,Math.min(90,bases[id]+Math.round(7*Math.sin(t/8+phase)-7*Math.sin(phase)+3*Math.sin(t/3))));return {yes,no:102-yes,bidYes:yes-3,bidNo:99-yes};}
const sizes=[200,800,2000],names=['Atlas Demo','Bluewater Demo','Cobalt Demo'];
export function book(s,side,kind='buy',now=Date.now(),id='btc'){
 const q=quoteFor(s,id,now),base=kind==='buy'?(side==='YES'?q.yes:q.no):(side==='YES'?q.bidYes:q.bidNo);
 return (kind==='buy'?sizes:[100,400,1000]).map((n,i)=>({maker:names[i],key:kind+side+i,price:Math.max(1,Math.min(99,base+(kind==='buy'?1:-1)*[0,5,12][i])),shares:Math.max(0,n-(marketSession(s,id)?.depthUsed?.[kind+side+i]||0))}));
}
export function preview(s,side,kind,requested,now=Date.now(),id='btc'){
 if(!['YES','NO'].includes(side)||!['buy','sell'].includes(kind)||!Number.isSafeInteger(requested)||requested<=0)throw Error('Enter a positive whole IQ budget or share quantity.');
 const levels=book(s,side,kind,now,id);let left=requested,shares=0,value=0;const fills=[];
 for(const l of levels){const n=Math.min(l.shares,kind==='buy'?Math.floor(left/l.price):left);if(n){fills.push({...l,shares:n});shares+=n;value+=n*l.price;left-=kind==='buy'?n*l.price:n;}}
 const p=s.positions.find(p=>p.market===id&&p.side===side),costSold=kind==='sell'&&p?Math.round(p.cost*shares/p.shares):0;
 return {id,side,kind,requested,shares,value,left,fills,levels,costSold,net:shares*98,signature:JSON.stringify({id,side,kind,requested,levels})};
}
export function executeDepth(s,review,now=Date.now()){
 const id=review.id||'btc';
 if(s.settled[id]||(id==='btc'&&(!s.bitcoin||s.bitcoin.finished||now>=s.bitcoin.end)))throw Error('This round has ended. Start a new round.');
 const r=preview(s,review.side,review.kind,review.requested,now,id);
 if(r.signature!==review.signature)throw Error('Prices or available shares changed. Refresh the quote before confirming.');
 if(!r.shares)throw Error('No shares are available for this order.');
 let p=s.positions.find(p=>p.market===id&&p.side===r.side);
 if(r.kind==='buy'&&s.cash<r.value)throw Error('Not enough demo IQ.');
 if(r.kind==='sell'&&(!p||p.shares<r.requested))throw Error('You do not hold these shares.');
 const session=id==='btc'?s.bitcoin:((s.marketDepth??={})[id]??={});
 if(r.kind==='buy'){
  if(s.cash<r.value)throw Error('Not enough demo IQ for the actual purchase. Add test IQ or reduce the budget.');
  if(!p){p={market:id,side:r.side,shares:0,cost:0};s.positions.push(p)}
  p.shares+=r.shares;p.cost+=r.value;s.cash-=r.value;
 }else{
  if(!p||p.shares<r.requested)throw Error('You do not hold these shares.');
  p.shares-=r.shares;p.cost-=r.costSold;s.cash+=r.value;
  session.realized=(session.realized||0)+r.value-r.costSold;
  s.positions=s.positions.filter(p=>p.shares>0);
 }
 session.depthUsed??={};for(const f of r.fills)session.depthUsed[f.key]=(session.depthUsed[f.key]||0)+f.shares;
 s.history.unshift({id:'depth-'+now,time:now,label:`${r.kind==='buy'?'Bought':'Sold'} ${r.shares} ${r.side} ${id.toUpperCase()} · ${r.fills.length} simulated maker levels`,amount:r.kind==='buy'?-r.value:r.value});
 session.lastDepth={...r,time:now};return r;
}
