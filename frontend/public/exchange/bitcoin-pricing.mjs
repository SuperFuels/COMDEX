export const ROUND_MS=300000;
export function createRound(number=1,now=Date.now()){return {number,start:now,end:now+ROUND_MS,opening:60046.66,finished:false,realized:0};}
export function elapsedSeconds(round,now=Date.now()){return round.finished?300:Math.max(0,Math.min(300,(now-round.start)/1000));}
export function bitcoinPrice(round,seconds){const t=Math.max(0,Math.min(300,seconds));const drift=round.number%2?12:-8;return Math.round((round.opening+Math.sin(t/21)*7+Math.sin(t/8)*2+drift*t/300)*100)/100;}
export function roundOutcome(round){return bitcoinPrice(round,300)>=round.opening?'YES':'NO';}
export function bitcoinQuotes(round,now=Date.now()){if(!round)return {yes:51,no:51,bidYes:48,bidNo:48};const t=Math.floor(elapsedSeconds(round,now)),price=bitcoinPrice(round,t),remaining=Math.max(0,300-t),scale=2+12*Math.sqrt(remaining/300),mid=Math.max(4,Math.min(96,Math.round(100/(1+Math.exp(-(price-round.opening)/scale)))));return {yes:mid+1,no:101-mid,bidYes:mid-2,bidNo:98-mid};}
