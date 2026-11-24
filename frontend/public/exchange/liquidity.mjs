import {bitcoinQuotes} from './bitcoin-pricing.mjs';
const sizes=[200,800,2000],names=['Atlas Demo','Bluewater Demo','Cobalt Demo'];
export function book(s,side,kind='buy',now=Date.now()){
 const q=bitcoinQuotes(s.bitcoin,now),base=kind==='buy'?(side==='YES'?q.yes:q.no):(side==='YES'?q.bidYes:q.bidNo);
 return (kind==='buy'?sizes:[100,400,1000]).map((n,i)=>({maker:names[i],key:kind+side+i,price:Math.max(1,Math.min(99,base+(kind==='buy'?1:-1)*[0,5,12][i])),shares:Math.max(0,n-(s.bitcoin?.depthUsed?.[kind+side+i]||0))}));
}
export function preview(s,side,kind,requested,now=Date.now()){
 if(!['YES','NO'].includes(side)||!['buy','sell'].includes(kind)||!Number.isSafeInteger(requested)||requested<=0)throw Error('Enter a positive whole IQ budget or share quantity.');
 const levels=book(s,side,kind,now);let left=requested,shares=0,value=0;const fills=[];
 for(const l of levels){const n=Math.min(l.shares,kind==='buy'?Math.floor(left/l.price):left);if(n){fills.push({...l,shares:n});shares+=n;value+=n*l.price;left-=kind==='buy'?n*l.price:n;}}
 const p=s.positions.find(p=>p.market==='btc'&&p.side===side),costSold=kind==='sell'&&p?Math.round(p.cost*shares/p.shares):0;
 return {side,kind,requested,shares,value,left,fills,levels,costSold,net:shares*98,signature:JSON.stringify({side,kind,requested,levels})};
}
export function executeDepth(s,review,now=Date.now()){
 if(!s.bitcoin||s.bitcoin.finished||now>=s.bitcoin.end||s.settled.btc)throw Error('This round has ended. Start a new round.');
 const r=preview(s,review.side,review.kind,review.requested,now);
 if(r.signature!==review.signature)throw Error('Prices or available shares changed. Refresh the quote before confirming.');
 if(!r.shares)throw Error('No shares are available for this order.');
 let p=s.positions.find(p=>p.market==='btc'&&p.side===r.side);
 if(r.kind==='buy'){
  if(s.cash<r.value)throw Error('Not enough demo IQ for the actual purchase. Add test IQ or reduce the budget.');
  if(!p){p={market:'btc',side:r.side,shares:0,cost:0};s.positions.push(p)}
  p.shares+=r.shares;p.cost+=r.value;s.cash-=r.value;
 }else{
  if(!p||p.shares<r.requested)throw Error('You do not hold these shares.');
  p.shares-=r.shares;p.cost-=r.costSold;s.cash+=r.value;
  s.bitcoin.realized=(s.bitcoin.realized||0)+r.value-r.costSold;
  s.positions=s.positions.filter(p=>p.shares>0);
 }
 s.bitcoin.depthUsed??={};for(const f of r.fills)s.bitcoin.depthUsed[f.key]=(s.bitcoin.depthUsed[f.key]||0)+f.shares;
 s.history.unshift({id:'depth-'+now,time:now,label:`${r.kind==='buy'?'Bought':'Sold'} ${r.shares} ${r.side} BTC · ${r.fills.length} simulated maker levels`,amount:r.kind==='buy'?-r.value:r.value});
 s.bitcoin.lastDepth={...r,time:now};return r;
}
