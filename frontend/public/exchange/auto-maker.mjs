import {cancelLaunch} from './launch-market.mjs';
export function makerConfig(m){return m.maker??={enabled:true,limit:m.allocated,clip:100,margin:5,revisions:[],reason:'Waiting for funding or trading activity.'};}
export function makerCost(m){return m.book.holdings.filter(h=>h.owner==='Maker').reduce((n,h)=>n+h.cost,0);}
export function repriceMaker(s,m,reason='Trade received'){
 const cfg=makerConfig(m);for(const o of m.book.orders)if(o.owner==='Maker'&&o.left)cancelLaunch(m.book,o.id);
 if(!cfg.enabled||m.status!=='Open'){cfg.reason=m.status==='Open'?'Automation paused; existing holdings remain at risk.':`Market ${m.status.toLowerCase()}; no maker quotes.`;return;}
 const cost=makerCost(m),capacity=Math.max(0,Math.min(m.book.accounts.Maker,cfg.limit-cost,m.allocated-cost));
 if(capacity<2){cfg.reason='Exposure limit or available budget reached. No new quotes.';return;}
 const holdings=m.book.holdings.filter(h=>h.owner==='Maker'),yes=holdings.find(h=>h.side==='YES')?.shares||0,no=holdings.find(h=>h.side==='NO')?.shares||0;
 const skew=Math.max(-10,Math.min(10,Math.round((yes-no)/Math.max(1,yes+no)*10))),center=Math.max(6,Math.min(94,m.mark-skew));
 const prices={YES:Math.max(1,center-cfg.margin),NO:Math.max(1,100-center-cfg.margin)};
 // Post-only quotes: do not cross any existing complementary customer bid.
 for(const side of ['YES','NO']){const opposite=m.book.orders.filter(o=>o.owner!=='Maker'&&o.side!==side&&o.left);const best=Math.max(0,...opposite.map(o=>o.price));prices[side]=Math.min(prices[side],99-best);}
 const shares=Math.min(cfg.clip,Math.floor(capacity/(prices.YES+prices.NO)));
 if(shares<1){cfg.reason='Not enough capacity to fund a pair of quotes.';return;}
 for(const side of ['YES','NO']){const price=prices[side];m.book.accounts.Maker-=price*shares;m.book.orders.push({id:m.book.next++,owner:'Maker',side,price,original:shares,left:shares,status:'Waiting',automatic:true});}
 const entry={time:Date.now(),yes:prices.YES,no:prices.NO,shares,reason,skew,capacity};cfg.revisions.unshift(entry);cfg.revisions=cfg.revisions.slice(0,30);cfg.reason=`${reason}. Inventory adjustment ${skew} cents; ${shares} shares quoted on each side.`;
 s.audit.unshift({time:entry.time,text:`${m.id}: automatic quotes Yes ${(prices.YES/100).toFixed(2)}, No ${(prices.NO/100).toFixed(2)} IQ, ${shares} shares each. ${reason}.`});
}
export function configureMaker(s,m,limit,clip){if(m.status!=='Open')throw Error('Open the market before changing automation.');if(!Number.isInteger(limit)||limit<makerCost(m)||limit>m.allocated)throw Error('Exposure limit must cover existing holdings cost and cannot exceed allocated funds.');if(!Number.isInteger(clip)||clip<1||clip>1000)throw Error('Choose 1–1,000 shares per quote.');const cfg=makerConfig(m);cfg.limit=limit;cfg.clip=clip;repriceMaker(s,m,'Risk limits updated');}
